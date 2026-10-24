// Actual JSFX + production command bridge; no parallel judge implementation.
#include "game_control.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <deque>
#include <memory>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <tuple>
#include <vector>
namespace {
void check(bool b,const char* why) { if(!b) throw std::runtime_error(why); }
using Event=std::array<uint8_t,3>;
struct Engine {
    ysfx_config_u cfg{ysfx_config_new()};
    ysfx_u fx{ysfx_new(cfg.get())};
    GameControl control;
    explicit Engine(const char* path) {
        check(ysfx_load_file(fx.get(),path,0)&&ysfx_compile(fx.get(),0),"compile production JSFX");
        ysfx_set_sample_rate(fx.get(),48000); ysfx_set_block_size(fx.get(),256); ysfx_init(fx.get());
        ysfx_slider_set_value(fx.get(),13,1,true);
    }
    double get(const char* name) {auto* value=ysfx_find_var(fx.get(),name);check(value,"missing JSFX variable");return *value;}
    void midi(uint8_t status,uint8_t note,uint8_t value=100,uint32_t offset=0) {
        const uint8_t bytes[]{status,note,value}; const ysfx_midi_event_t e{0,offset,3,bytes};
        check(ysfx_send_midi(fx.get(),&e),"enqueue midi");
    }
    std::vector<Event> block() {
        control.process(fx.get()); ysfx_process_float(fx.get(),nullptr,nullptr,0,0,256); control.publish(fx.get());
        std::vector<Event> out; ysfx_midi_event_t e{};
        while(ysfx_receive_midi(fx.get(),&e)) if(e.size==3) out.push_back({e.data[0],e.data[1],e.data[2]});
        return out;
    }
    void on() { check(control.send({1}),"game on command"); block(); }
    void target(int id=1, double limit=10) {
        GamePacket p{3}; p.limit=limit; p.target.id=id; p.target.count=4;
        const int notes[]{60,64,67,71}, roles[]{0,1,2,3}, letters[]{0,2,4,6}, scale[]{0,2,4,5,7,9,11};
        std::copy(notes,notes+4,p.target.notes);std::copy(roles,roles+4,p.target.roles);std::copy(letters,letters+4,p.target.letters);
        std::copy(scale,scale+7,p.target.scale); p.target.quality=4;
        for(int i=0;i<7;++i)p.target.scaleLetters[i]=i;
        check(control.send(p),"target accepted");block();
    }
};
void race(const char* path) {
    Engine e(path); e.block(); e.on(); e.target();
    check(e.get("game_phase")==2 && e.get("game_count")==4,"answer phase");
    e.midi(0x90,48);e.midi(0x80,48,0);e.block();check(e.get("game_piano_hits")==0,"wrong octave rejected");
    for(auto note:{60,64}) {e.midi(0x90,note);e.midi(0x80,note,0);e.block();}
    for(auto note:{67,71}) {e.midi(0x9e,note);e.midi(0x8e,note,0);e.block();}
    check(e.get("game_phase")==2,"instruments never pool hits");
    check(e.get("game_piano_hits")==2 && e.get("game_guitar_hits")==2,"independent collections");
    e.midi(0x90,60);e.midi(0x80,60,0);e.block();check(e.get("game_piano_hits")==2,"repeat no double credit");
    e.midi(0x9f,72);e.midi(0x8f,72,0);const auto controls=e.block();
    check(std::none_of(controls.begin(),controls.end(),[](auto d){return (d[0]&0xf0)==0x90;}),"computer chord cannot auto-answer");
    for(auto note:{60,64}) {e.midi(0x9e,note);e.midi(0x8e,note,0);e.block();}
    check(e.get("game_phase")==3 && e.get("game_guitar_score")==4096 && e.get("game_piano_score")==0,"guitar wins and replays");
    e.target(2);check(e.get("game_piano_hits")==0 && e.get("game_guitar_hits")==0,"next clears hits");
    for(auto note:{60,64,67,71})e.midi(0x90,note);
    e.block();check(e.get("game_piano_score")==4096,"piano simultaneous chord wins");
    e.target(3);e.midi(0x90,60);e.block();check(e.get("game_piano_hits")==0,"held note not inherited");
    e.midi(0x80,60,0);e.midi(0x80,60,0);e.midi(0x90,60);e.block();check(e.get("game_piano_hits")==1,"fresh attack counts");
}
void timeout(const char* path) {
    Engine e(path);e.block();e.on();e.target();
    check(e.control.send({4}),"pause accepted");e.block();
    for(int i=0;i<2000;++i)e.block();check(e.get("game_phase")==5,"pause excludes elapsed time");
    check(e.get("game_remaining")>9.9,"pause displays retained time");
    check(e.control.send({4}),"resume accepted");e.block();
    std::vector<Event> demo;
    for(int i=0;i<1900 && e.get("game_phase")==2;++i){const auto out=e.block();demo.insert(demo.end(),out.begin(),out.end());}
    check(e.get("game_phase")==3 && e.get("game_timeouts")==1,"10s timeout reveals");
    std::vector<int> notes;
    for(auto d:demo)if(d[0]==0x9f)notes.push_back(d[1]);
    check(notes==std::vector<int>({60,64,67,71}),"exact voicing demonstration, dedicated channel");
    for(auto note:{60,64,67,71})e.midi(0x90,note);
    e.block();check(e.get("game_piano_score")==0,"demo cannot score");
    e.control.off();const auto off=e.block();
    check(std::count_if(off.begin(),off.end(),[](auto d){return d[0]==0x8f;})==4,"off releases demonstration");
    check(std::none_of(off.begin(),off.end(),[](auto d){return (d[0]&15)!=15;}),"off leaves live physical notes untouched");
    check(e.get("game_on")==0 && e.get("game_phase")==0,"off restores normal state");
    e.on();e.target();
    for(int i=0;i<2300;++i)e.block();
    check(e.get("game_phase")==4,"2s demonstration advances");
}
void isolation(const char* path, const char* baseline) {
    Engine normal(baseline), toggled(path);normal.block();toggled.block();
    std::array<double,21> before{};
    for(unsigned i=0;i<21;++i)before[i]=ysfx_slider_get_value(toggled.fx.get(),i);
    for(auto* engine:{&normal,&toggled}) {
        engine->midi(0x9f,90);engine->midi(0x8f,90,0);engine->block();
    }
    for(unsigned i=0;i<21;++i)before[i]=ysfx_slider_get_value(toggled.fx.get(),i);
    ysfx_state_u savedBefore{ysfx_save_state(toggled.fx.get())};
    toggled.on();toggled.target();
    toggled.midi(0x9f,90);toggled.midi(0x8f,90,0);toggled.block();
    ysfx_state_u savedDuring{ysfx_save_state(toggled.fx.get())};
    check(ysfx_is_state_equal(savedBefore.get(),savedDuring.get()),"game cannot alter serialized normal state");
    toggled.control.off();toggled.block();
    for(unsigned i=0;i<21;++i)check(before[i]==ysfx_slider_get_value(toggled.fx.get(),i),"all 21 parameters unchanged by game");
    for(unsigned i=3000;i<3207;++i)check(ysfx_read_vmem_single(normal.fx.get(),i)==ysfx_read_vmem_single(toggled.fx.get(),i),"voicing memory unchanged");
    for(auto d:std::vector<Event>{{0x9f,72,100},{0x9f,79,100},{0x8f,79,0},{0x90,60,90},{0xb0,64,127},{0x80,60,0},{0x8f,72,0},{0xb0,64,0}}) {
        normal.midi(d[0],d[1],d[2]);toggled.midi(d[0],d[1],d[2]);
        check(normal.block()==toggled.block(),"off MIDI equals untouched instance byte-for-byte");
    }
    if(ysfx_find_var(normal.fx.get(),"game_on"))check(normal.get("game_on")==0,"instance isolation");
}
void boundaries(const char* path) {
    Engine e(path);e.block();
    GamePacket invalid{1};invalid.limit=std::numeric_limits<double>::quiet_NaN();
    check(!e.control.send(invalid),"NaN timing rejected");
    invalid.limit=10;invalid.demo=std::numeric_limits<double>::infinity();
    check(!e.control.send(invalid),"infinite timing rejected");
    e.on();e.target();
    ysfx_state_u saved{ysfx_save_state(e.fx.get())};
    check(bool(saved),"save while game active");
    Engine fresh(path);check(ysfx_load_state(fresh.fx.get(),saved.get()),"reload normal saved state");
    fresh.block();check(fresh.get("game_on")==0,"game never persisted into project");
    for(int iteration=0;iteration<25;++iteration) {
        e.control.off();check(e.control.send({1}),"rapid reopen accepted");
        e.block();e.block();check(e.get("game_on")==1,"rapid reopen survives stop latch");
        e.target(iteration+2);
    }
    // Exactly the deadline is too late; preceding sample still counts.
    *ysfx_find_var(e.fx.get(),"game_deadline")=e.get("game_clock")+100;
    e.midi(0x90,60,100,99);e.midi(0x90,64,100,100);e.block();
    check(e.get("game_piano_hits")==1 && e.get("game_phase")==3,"sample-accurate deadline");
    check(e.get("game_timeouts")==1,"deadline counted once");
    e.control.off();e.block();
    check(e.block().empty(),"off sends no ongoing demo or MIDI traffic");
    e.on();e.target();e.control.reset();e.block();
    check(e.control.resets()==1 && e.get("game_on")==0,"host reset closes game safely");
}

void speed_and_success_replay(const char* path) {
    for(int elapsed:{1,3,8}) {
        Engine e(path);e.block();e.on();e.target();
        // Advance audio time, not the deadline: pauses must not lower the award.
        *ysfx_find_var(e.fx.get(),"game_clock")=e.get("game_answer_start")+elapsed*48000;
        const int award=int(std::pow(8-elapsed,4));
        for(int pause=0;pause<2;++pause) {
            check(e.control.send({4}),"pause before completion");e.block();
            for(int i=0;i<500;++i)e.block();
            check(e.control.send({4}),"resume before completion");e.block();
        }
        GameStatus status;e.control.read(status); // simulate editor draining pause telemetry
        for(auto n:{60,64,67,71})e.midi(0x90,n);
        const auto output=e.block();
        check(e.get("game_phase")==3 && e.get("game_winner")==1,"success enters replay");
        check(e.get("game_award")==award,"speed score excludes pause");
        check(e.get("game_timeouts")==0,"success is not a timeout");
        check(std::count_if(output.begin(),output.end(),[](auto d){return d[0]==0x9f;})==4,"success plays exact four-note answer");
        for(auto n:{60,64,67,71}) {
            check(ysfx_read_vmem_single(e.fx.get(),5100+n)==1,"success reveals every target");
            e.midi(0x9e,n);e.midi(0x8e,n,0);
        }
        e.block();check(e.get("game_guitar_score")==0,"second player cannot score during replay");
        e.control.read(status);
        check(status.winner==1 && status.award==award,"winner and award published");
        for(int i=0;i<370;++i)e.block();
        check(e.get("game_phase")==3,"success replay not prematurely skipped");
        for(int i=0;i<10;++i)e.block();
        check(e.get("game_phase")==4 && e.get("game_demo_active")==0,"success advances after two seconds, notes released");
        check(e.get("game_piano_score")==award,"success scored exactly once");
    }
}


void original_score_curve(const char* path) {
    // Fixtures transcribed from the earliest Rust commit 872294a, not JSFX.
    constexpr int awards[]{4096,2401,1296,625,256,81,16,1,0,0};
    for(int rate:{44100,48000,96000}) for(int limit:{1,2,5,10,30,120}) {
        Engine e(path); ysfx_set_sample_rate(e.fx.get(),rate); e.block(); e.on();
        int total=0;
        for(int second=0;second<10;++second) for(int delta:{-1,0,1}) {
            const int samples=second*rate+delta;
            if(samples<256 || samples>=limit*rate) continue;
            e.target(second*3+delta+2,limit);
            const int offset=123;
            *ysfx_find_var(e.fx.get(),"game_clock")=e.get("game_answer_start")+samples-offset;
            for(auto n:{60,64,67,71}) { e.midi(0x90,n,100,offset);e.midi(0x80,n,0,offset); }
            e.block();
            const int expected=awards[second-(delta<0 ? 1 : 0)]; total+=expected;
            check(e.get("game_award")==expected,"original quartic second boundaries independent of timeout/sample rate");
            check(e.get("game_piano_score")==total,"independent cumulative original scoring");
            check(e.get("game_winner")==1 && e.get("game_timeouts")==0,"zero-point success remains success");
        }
    }
}

void extended_session(const char* path) {
    Engine e(path); e.block(); e.on();
    std::unique_ptr<void,decltype(&chordlab_game_free)> planner(chordlab_game_new(20261023),chordlab_game_free);
    check(bool(planner) && chordlab_game_configure(planner.get(),1.0,2,true),"session planner");
    std::deque<GameTarget> preview;
    int piano=0,guitar=0,timeouts=0,approaches=0,modulations=0;
    unsigned visit=0,coverage=0;
    auto fill=[&] {
        while(std::count_if(preview.begin(),preview.end(),[](const auto& t){return t.backbone!=0;})<3) {
            GameTarget t;check(chordlab_game_next(planner.get(),&t),"committed preview");preview.push_back(t);
        }
    };
    fill();
    for(int round=0;round<180;++round) {
        const auto t=preview.front();preview.pop_front();
        if(t.visit!=visit) {
            if(visit) {check(coverage==127,"no modulation before seven successful degrees");++modulations;}
            visit=t.visit;coverage=0;
        }
        if(t.kind==1) ++approaches;
        check(t.count==4,"exact seventh chord target");
        check(e.control.send({3,t,10,1}),"submit committed target");e.block();
        const bool success=round%11!=10;
        const int elapsed=1+round%9, winner=round%2;
        const int award=int(std::pow(std::max(0,8-elapsed),4));
        *ysfx_find_var(e.fx.get(),"game_clock")=e.get("game_answer_start")+(success ? elapsed*48000 : 10*48000);
        if(success) for(unsigned i=0;i<t.count;++i) {
            e.midi(winner ? 0x9e : 0x90,uint8_t(t.notes[i]));
            e.midi(winner ? 0x8e : 0x80,uint8_t(t.notes[i]),0);
        }
        e.block();
        if(success) (winner ? guitar : piano)+=award; else ++timeouts;
        check(e.get("game_award")== (success ? award : 0),"exact per-round speed award");
        check(e.get("game_winner")== (success ? winner+1 : 0),"correct winning instrument");
        // The losing side cannot score during the answer demonstration.
        for(unsigned i=0;i<t.count;++i) {
            e.midi(winner ? 0x90 : 0x9e,uint8_t(t.notes[i]));
            e.midi(winner ? 0x80 : 0x8e,uint8_t(t.notes[i]),0);
        }
        for(int block=0;block<190;++block) {e.block();GameStatus s;e.control.read(s);}
        check(e.get("game_phase")==4,"demo ends before next round");
        check(e.get("game_piano_score")==piano && e.get("game_guitar_score")==guitar,"cumulative separate scores");
        check(e.get("game_timeouts")==timeouts,"timeouts never score");
        check(chordlab_game_complete(planner.get(),t.id,success),"report ordered completion");
        if(success && t.backbone) coverage|=1u<<t.degree;
        fill();
    }
    check(approaches>0 && modulations>1,"session covers approaches and multiple modulations");
    std::cout<<"180 rounds: piano="<<piano<<" guitar="<<guitar<<" timeouts="<<timeouts
             <<" approaches="<<approaches<<" modulations="<<modulations<<": PASS\n";
}

}
int main(int argc,char** argv) {
    try {check(argc==2 || argc==3,"JSFX path and optional original baseline required");original_score_curve(argv[1]);race(argv[1]);timeout(argv[1]);isolation(argv[1],argc==3 ? argv[2] : argv[1]);boundaries(argv[1]);speed_and_success_replay(argv[1]);extended_session(argv[1]);std::cout<<"game race / speed / success replay / timeout / normal isolation: PASS\n";}
    catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
