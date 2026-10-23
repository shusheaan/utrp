// Actual JSFX + production command bridge; no parallel judge implementation.
#include "game_control.h"
#include <algorithm>
#include <array>
#include <cmath>
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
    void target(int id=1) {
        GamePacket p{3}; p.target.id=id; p.target.count=4;
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
    check(e.get("game_phase")==4 && e.get("game_guitar_score")==1 && e.get("game_piano_score")==0,"guitar wins");
    e.target(2);check(e.get("game_piano_hits")==0 && e.get("game_guitar_hits")==0,"next clears hits");
    for(auto note:{60,64,67,71})e.midi(0x90,note);
    e.block();check(e.get("game_piano_score")==1,"piano simultaneous chord wins");
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
    ysfx_state_u savedBefore{ysfx_save_state(toggled.fx.get())};
    toggled.on();toggled.target();
    ysfx_state_u savedDuring{ysfx_save_state(toggled.fx.get())};
    check(ysfx_is_state_equal(savedBefore.get(),savedDuring.get()),"game cannot alter serialized normal state");
    toggled.control.off();toggled.block();
    for(unsigned i=0;i<21;++i)check(before[i]==ysfx_slider_get_value(toggled.fx.get(),i),"all 21 parameters unchanged by game");
    for(unsigned i=3000;i<3107;++i)check(ysfx_read_vmem_single(normal.fx.get(),i)==ysfx_read_vmem_single(toggled.fx.get(),i),"voicing memory unchanged");
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

}
int main(int argc,char** argv) {
    try {check(argc==2 || argc==3,"JSFX path and optional original baseline required");race(argv[1]);timeout(argv[1]);isolation(argv[1],argc==3 ? argv[2] : argv[1]);boundaries(argv[1]);std::cout<<"game race / timeout / demo / normal isolation: PASS\n";}
    catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
