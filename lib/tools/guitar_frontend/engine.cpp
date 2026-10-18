#include "engine.h"
#include "defaults.h"
#include <algorithm>
#include <cmath>

namespace guitar {
namespace {
constexpr double pi = 3.14159265358979323846;
double frequency(int note) { return 440.0 * std::exp2((note - 69) / 12.0); }
}
void Lowpass::prepare(double rate, double cutoff, double q)
{
    const double w = 2 * pi * cutoff / rate, c = std::cos(w), alpha = std::sin(w)/(2*q);
    const double scale = 1/(1+alpha);
    b0=(1-c)*0.5*scale; b1=(1-c)*scale; b2=b0;
    a1=-2*c*scale; a2=(1-alpha)*scale; z1=z2=0;
}
double Lowpass::push(double input)
{
    const double output=b0*input+z1;
    z1=b1*input-a1*output+z2; z2=b2*input-a2*output;
    // Avoid persistent denormals in long silent tails.
    if (std::abs(z1)<1e-25) z1=0;
    if (std::abs(z2)<1e-25) z2=0;
    return output;
}
bool Detector::prepare(double rate)
{
    if (!std::isfinite(rate) || rate<defaults::min_sample_rate || rate>defaults::max_sample_rate) return false;
    sampleRate=rate; decimation=static_cast<unsigned>(rate/defaults::target_rate);
    analysisRate=rate/decimation;
    length=static_cast<unsigned>(std::ceil(analysisRate*defaults::frame_ms/1000));
    hop=static_cast<unsigned>(std::ceil(analysisRate*defaults::hop_ms/1000));
    if (length>capacity || hop==0 || hop>=length) return false;
    for (unsigned i=0;i<length;++i) window[i]=0.5-0.5*std::cos(2*pi*i/(length-1));
    reset(); return true;
}
void Detector::reset()
{
    ring.fill(0); frame.fill(0); difference.fill(0);
    write=filled=sinceHop=decimateCount=stable=missing=0;
    candidate=current=-1; previousRms=elapsedMs=0; lastOnMs=-10000; pendingAttack=false;
    // Fourth-order Butterworth anti-alias filter; dry audio never enters this path.
    filter1.prepare(sampleRate,defaults::lowpass_hz,0.541196100146197);
    filter2.prepare(sampleRate,defaults::lowpass_hz,1.306562964876377);
}
double Detector::spectralPower(double hz) const
{
    const double angle=2*pi*hz/analysisRate, stepR=std::cos(angle), stepI=std::sin(angle);
    double phaseR=1, phaseI=0, real=0, imag=0;
    for (unsigned i=0;i<length;++i) {
        const double value=frame[i]*window[i]; real+=value*phaseR; imag+=value*phaseI;
        const double next=phaseR*stepR-phaseI*stepI;
        phaseI=phaseR*stepI+phaseI*stepR; phaseR=next;
    }
    return real*real+imag*imag;
}
Observation Detector::supportedPitch(Observation result) const
{
    // A shared period of two ringing strings need not be an actual low note.
    // Require measured fundamental energy before accepting that virtual pitch.
    std::array<double,9> power{};
    for (unsigned h=1;h<power.size();++h) {
        const double hz=result.frequency*h;
        if (hz<analysisRate/2) power[h]=spectralPower(hz);
    }
    const double strongest=*std::max_element(power.begin()+1,power.end());
    // Energy alone can be leakage from a nearby real low string. Require a
    // local peak, allowing the estimator's cents tolerance at high pitches.
    // Half a spectral bin covers low pitches; no additional audio buffering.
    const double offset=std::max(0.5*analysisRate/length,
        2*result.frequency*(std::exp2(defaults::spectral_peak_cents/1200)-1));
    const bool peak=power[1]>=spectralPower(result.frequency-offset) &&
        power[1]>=spectralPower(result.frequency+offset);
    if (peak && power[1]>=strongest*defaults::fundamental_power_ratio) return result;
    double best=0, second=0; unsigned winner=0;
    for (unsigned h=2;h<power.size();++h) {
        const double hz=result.frequency*h;
        if (hz>frequency(int(defaults::max_note)+1)) break;
        const double score=power[h]+(2*h<power.size() ? 0.5*power[2*h] : 0)+
            (3*h<power.size() ? 0.25*power[3*h] : 0);
        if (score>best) { second=best; best=score; winner=h; } else second=std::max(second,score);
    }
    result.note=-1;
    if (!winner || best<second*defaults::spectral_margin) return result;
    const double period=analysisRate/(result.frequency*winner);
    const unsigned center=unsigned(std::lround(period));
    if (center<2 || center+2>=length) return result;
    unsigned lag=center;
    for (unsigned i=center-1;i<=center+1;++i) if (difference[i]<difference[lag]) lag=i;
    const double a=difference[lag-1], b=difference[lag], c=difference[lag+1];
    if (b>1-defaults::subharmonic_confidence || b>a || b>c) return result;
    // The short-period minimum is shifted by the other string. Use the longer
    // shared-period estimate, scaled to the spectrally supported component.
    result.frequency*=winner; result.confidence=1-b;
    const int note=int(std::lround(69+12*std::log2(result.frequency/440.0)));
    if (note>=defaults::min_note && note<=defaults::max_note) result.note=note;
    return result;
}
Observation Detector::analyze(const Settings& settings)
{
    double square=0;
    for (unsigned i=0;i<length;++i) { frame[i]=ring[(write+i)%length]; square+=frame[i]*frame[i]; }
    Observation result{}; result.rms=std::sqrt(square/length);
    if (result.rms<std::pow(10.0,settings.gateDb/20.0)) return result;
    const unsigned maxLag=static_cast<unsigned>(std::ceil(analysisRate/frequency(int(defaults::min_note)-1)));
    const unsigned minLag=static_cast<unsigned>(std::floor(analysisRate/frequency(int(defaults::max_note)+1)));
    const unsigned comparison=length-maxLag;
    double sum=0; difference[0]=1;
    for (unsigned lag=1;lag<=maxLag;++lag) {
        double value=0;
        for (unsigned i=0;i<comparison;++i) { const double delta=frame[i]-frame[i+lag]; value+=delta*delta; }
        sum+=value; difference[lag]=sum>1e-30 ? value*lag/sum : 1;
    }
    // YIN cumulative mean normalized difference, first confident local minimum.
    for (unsigned lag=std::max(2u,minLag);lag<maxLag;++lag) {
        if (difference[lag]>=1-settings.confidence || difference[lag]>difference[lag-1] || difference[lag]>difference[lag+1]) continue;
        const double a=difference[lag-1], b=difference[lag], c=difference[lag+1];
        const double denominator=a-2*b+c;
        const double correction=std::abs(denominator)>1e-20 ? std::clamp(0.5*(a-c)/denominator,-0.5,0.5) : 0;
        result.frequency=analysisRate/(lag+correction); result.confidence=1-b;
        const int note=static_cast<int>(std::lround(69+12*std::log2(result.frequency/440.0)));
        if (note>=defaults::min_note && note<=defaults::max_note) result.note=note;
        return result.note>=0 ? supportedPitch(result) : result;
    }
    return result;
}
Update Detector::update(const Observation& observation, const Settings& settings)
{
    const double dt=hopMilliseconds(); elapsedMs+=dt;
    // Same-note re-picks: rising short-window energy, not arbitrary periodic retrigger.
    double recent=0;
    for (unsigned i=length-hop;i<length;++i) recent+=frame[i]*frame[i];
    recent=std::sqrt(recent/hop);
    const double floor=std::pow(10.0,settings.gateDb/20.0);
    if (recent>std::max(floor*2,previousRms*defaults::retrigger_ratio) && elapsedMs-lastOnMs>defaults::retrigger_cooldown_ms)
        pendingAttack=true;
    previousRms=0.75*previousRms+0.25*recent;
    if (observation.note<0) {
        candidate=-1; stable=0; ++missing;
        if (missing*dt>=settings.releaseMs) { current=-1; pendingAttack=false; }
        return {true,current,false,observation};
    }
    missing=0;
    if (candidate!=observation.note) { candidate=observation.note; stable=1; } else ++stable;
    bool retrigger=false;
    if (stable*dt>=settings.stabilityMs) {
        retrigger=current==candidate && pendingAttack;
        if (current!=candidate || retrigger) { current=candidate; lastOnMs=elapsedMs; }
        pendingAttack=false;
    }
    return {true,current,retrigger,observation};
}
Update Detector::push(double sample, const Settings& settings)
{
    if (!settings.enabled) return {};
    if (!std::isfinite(sample)) sample=0;
    const double filtered=filter2.push(filter1.push(std::clamp(sample,-8.0,8.0)));
    if (++decimateCount<decimation) return {};
    decimateCount=0; ring[write]=filtered; write=(write+1)%length;
    filled=std::min(filled+1,length);
    if (++sinceHop<hop) return {};
    sinceHop=0;
    if (filled<length) return {};
    return update(analyze(settings),settings);
}
}
