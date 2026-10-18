#include "engine.h"
#include "defaults.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {
constexpr double pi=3.14159265358979323846;
const guitar::Settings settings{true,guitar::defaults::gate_db,guitar::defaults::confidence,
    guitar::defaults::stability_ms,guitar::defaults::release_ms};
void require(bool value,const char* message) { if (!value) throw std::runtime_error(message); }
double hz(int note) { return 440*std::exp2((note-69)/12.0); }
double tone(int note,double time,int shape=0) {
    const double phase=2*pi*hz(note)*time;
    if (!shape) return 0.2*std::sin(phase);
    double value=0;
    for (int h=1;h<=8;++h) value+=std::sin(phase*h+0.13*h)/(h*h);
    return 0.2*std::exp(-time*1.8)*value*(1-std::exp(-time*1000));
}
struct Result { std::vector<int> starts; double firstMs=-1, endMs=-1; unsigned retriggers=0; double maxCents=0; };
Result run(guitar::Detector& detector,int note,double rate,int shape) {
    Result r; int previous=-1;
    const auto samples=unsigned(rate*0.45);
    for (unsigned i=0;i<samples;++i) {
        const double t=i/rate; const auto u=detector.push(t<0.25 ? tone(note,t,shape) : 0,settings);
        if (!u.ready) continue;
        if (u.note!=previous) {
            if (u.note>=0) { r.starts.push_back(u.note); if (r.firstMs<0) r.firstMs=t*1000; }
            else r.endMs=(t-0.25)*1000;
            previous=u.note;
        }
        if (u.retrigger) ++r.retriggers;
        if (t>0.10 && t<0.23 && u.observation.note==note)
            r.maxCents=std::max(r.maxCents,std::abs(1200*std::log2(u.observation.frequency/hz(note))));
    }
    return r;
}
void pitchMatrix() {
    unsigned cases=0; double latency=0, release=0, cents=0;
    for (double rate:{32000.,44100.,48000.,96000.,192000.}) for (int shape:{0,1})
        for (int note=38;note<=88;++note) {
            guitar::Detector detector; require(detector.prepare(rate),"prepare");
            const auto r=run(detector,note,rate,shape);
            if (r.starts!=std::vector<int>{note}) {
                std::cerr<<"note="<<note<<" rate="<<rate<<" shape="<<shape<<" actual=";
                for (int n:r.starts) std::cerr<<n<<",";
                std::cerr<<"\n"; throw std::runtime_error("exact synthetic note");
            }
            require(r.firstMs>=0 && r.firstMs<110,"attack bound");
            require(r.endMs>=0 && r.endMs<180,"release bound");
            require(r.retriggers==0,"no synthetic sustained-note retrigger");
            require(r.maxCents<30,"pitch estimation cents");
            latency=std::max(latency,r.firstMs); release=std::max(release,r.endMs); cents=std::max(cents,r.maxCents); ++cases;
        }
    std::cout<<"pitch_matrix="<<cases<<" max_attack_ms="<<latency<<" max_release_ms="<<release<<" max_cents="<<cents<<"\n";
}
void rejection() {
    for (int mode=0;mode<6;++mode) {
        guitar::Detector d; require(d.prepare(48000),"prepare rejection"); uint32_t rng=12345;
        for (unsigned i=0;i<48000;++i) {
            rng=1664525*rng+1013904223;
            const double noise=(double(rng)/4294967296.0-0.5)*0.1;
            const double value=mode==0 ? 0 : mode==1 ? 0.2 : mode==2 ? noise : mode==3 ? (i==5000 ? 1 : 0) :
                mode==4 ? std::numeric_limits<double>::quiet_NaN() : tone(60,i/48000.0)*0.0001;
            const auto u=d.push(value,settings); require(!u.ready || u.note<0,"no note on silence/DC/noise/impulse/NaN/below-gate");
        }
    }
    guitar::Detector d;
    require(!d.prepare(0) && !d.prepare(8000) && !d.prepare(std::numeric_limits<double>::infinity()),"sample-rate boundary");
    std::cout<<"rejection=6 rate_validation=3\n";
}
void sequences() {
    guitar::Detector d; require(d.prepare(48000),"prepare sequence");
    const std::vector<int> melody{40,42,44,45,47,49,51,52,60,64,67,72,67,64,60};
    std::vector<int> starts; int previous=-1;
    for (int n:melody) {
        d.reset(); // Each fragment's boundary is verified separately by run().
        const auto r=run(d,n,48000,1); starts.insert(starts.end(),r.starts.begin(),r.starts.end());
    }
    require(starts==melody,"scale and separated arpeggio");
    // Continuous state across adjacent notes, with and without a short damping gap.
    for (double gap : {0.0, 0.06}) {
        d.reset(); starts.clear(); previous=-1;
        for (int note:melody) for (unsigned i=0;i<unsigned(48000*(0.30+gap));++i) {
            const double t=i/48000.0;
            const auto u=d.push(t<0.30 ? tone(note,t,1) : 0,settings);
            if (!u.ready) continue;
            if (u.note>=0 && u.note!=previous) starts.push_back(u.note);
            previous=u.note;
        }
        if (starts!=melody) {for (int n:starts) std::cerr<<n<<","; std::cerr<<" gap="<<gap<<"\n";}
        require(starts==melody,"continuous melody/arpeggio (not overlapping strings)");
    }
    d.reset(); starts.clear(); previous=-1; unsigned repicks=0;
    for (unsigned i=0;i<48000;++i) {
        double t=i/48000.0;
        double value=t<0.4 ? tone(60,t,1)*std::exp(-t*6) : tone(60,t-0.4,1);
        const auto u=d.push(value,settings);
        if (!u.ready) continue;
        if (u.note>=0 && previous<0) starts.push_back(u.note);
        if (u.retrigger) ++repicks;
        previous=u.note;
    }
    require(starts==std::vector<int>{60} && repicks==1,"same-pitch repeated pluck");
    d.reset(); require(d.currentNote()==-1,"reset no stale note");
    std::cout<<"separated_sequence_notes="<<melody.size()<<" continuous_sequences=2 same_note_repicks="<<repicks<<"\n";
}
void virtualLowPitch() {
    unsigned cases=0;
    for (double rate : {32000.,44100.,48000.,96000.,192000.})
        for (int mainNote : {64,67,72}) for (double residual : {0.25,0.45,0.65}) {
            guitar::Detector detector; require(detector.prepare(rate),"prepare virtual-low regression");
            unsigned correct=0, evaluated=0;
            for (unsigned i=0;i<unsigned(rate*0.4);++i) {
                const double time=i/rate;
                const auto u=detector.push(tone(mainNote,time,1)+residual*tone(mainNote-5,time,1),settings);
                if (!u.ready || time<0.12) continue;
                ++evaluated;
                if (u.note==mainNote) ++correct;
                if (u.note>=0 && u.note!=mainNote) {
                    std::cerr<<"virtual low rate="<<rate<<" main="<<mainNote<<" residual="<<residual<<" got="<<u.note<<"\n";
                    throw std::runtime_error("no virtual subharmonic from ringing fourth");
                }
            }
            require(correct>evaluated*0.7,"retain supported dominant pitch, not just silence"); ++cases;
        }
    std::cout<<"virtual_low_regressions="<<cases<<" (dominant mono pitch, not polyphonic recognition)\n";
}

void nearbyLowLeakage() {
    unsigned cases=0;
    // Spark D4 regression: real E2 leakage must not support a fictitious G2.
    for (double rate : {32000.,44100.,48000.,96000.,192000.})
        for (double residual : {0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50})
            for (double phase : {0.,0.7,1.4,2.1}) {
                guitar::Detector detector; require(detector.prepare(rate),"prepare nearby-low regression");
                unsigned correct=0, evaluated=0;
                for (unsigned i=0;i<unsigned(rate*0.4);++i) {
                    const double t=i/rate;
                    const double sample=0.02*(std::sin(2*pi*293*t)+residual*std::sin(2*pi*82*t+phase));
                    const auto u=detector.push(sample,settings);
                    if (!u.ready || t<0.12) continue;
                    ++evaluated;
                    if (u.note==62) ++correct;
                    require(u.note==-1 || u.note==62,"no fictitious G2 from nearby E2 leakage");
                }
                require(correct>evaluated*0.8,"retain D4 instead of silencing leakage cases"); ++cases;
            }
    std::cout<<"nearby_low_leakage_regressions="<<cases<<"\n";
}
}
int main() {
    try {pitchMatrix();rejection();sequences();virtualLowPitch();nearbyLowLeakage();std::cout<<"PASS synthetic detector tests (not real-guitar certification)\n";}
    catch(const std::exception& e) {std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}
}
