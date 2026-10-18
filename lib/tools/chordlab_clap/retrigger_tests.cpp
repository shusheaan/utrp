// Verify actual JSFX MIDI events, including attack count, velocity and offsets.
#include "ysfx.h"
#include <array>
#include <cstdio>
#include <stdexcept>
#include <vector>

struct Event { uint32_t frame; std::array<uint8_t,3> bytes; };
using Events=std::vector<Event>;
void require(bool ok,const char* message) { if (!ok) throw std::runtime_error(message); }
Events send(ysfx_t* fx,int status,int note,int velocity,int frame=37) {
    const uint8_t bytes[]{uint8_t(status),uint8_t(note),uint8_t(velocity)};
    const ysfx_midi_event_t in{0,uint32_t(frame),3,bytes};
    require(ysfx_send_midi(fx,&in),"Input accepted");
    ysfx_process_float(fx,nullptr,nullptr,0,0,256);
    Events out;ysfx_midi_event_t event{};
    while (ysfx_receive_midi(fx,&event)) {
        require(event.size==3,"Three-byte events");
        out.push_back({event.offset,{event.data[0],event.data[1],event.data[2]}});
    }
    return out;
}
void command(ysfx_t* fx,int cmd) { send(fx,0x9f,60+cmd,100);send(fx,0x8f,60+cmd,0); }
void attack(const Events& events,int channel,int note,int velocity,bool retrigger) {
    require(events.size()==(retrigger?2u:1u),"Every press has exactly one attack, with balanced retrigger");
    if (retrigger) require(events[0].bytes==std::array<uint8_t,3>{uint8_t(0x80+channel),uint8_t(note),0},"NoteOff before repeated NoteOn");
    require(events.back().bytes==std::array<uint8_t,3>{uint8_t(0x90+channel),uint8_t(note),uint8_t(velocity)},"Physical velocity/channel/pitch unchanged");
    for (const auto& event:events) require(event.frame==37,"Sample offset preserved");
}
void physical_matrix(ysfx_t* fx) {
    for (int ch=0;ch<14;++ch) for (int note=0;note<128;++note) {
        attack(send(fx,0x90+ch,note,1),ch,note,1,false);
        attack(send(fx,0x90+ch,note,127),ch,note,127,true);
        require(send(fx,0x80+ch,note,0).empty(),"One remaining held input survives first release");
        const auto end=send(fx,0x90+ch,note,0);
        require(end.size()==1 && end[0].bytes[2]==0,"Velocity-zero final release forwarded");
        require(ysfx_read_vmem_single(fx,ch*128+note)==0,"No held input leak");
        attack(send(fx,0x90+ch,note,43),ch,note,43,false);
        require(send(fx,0x80+ch,note,0).size()==1,"Repress after release works");
    }
}
void mixed_matrix(ysfx_t* fx) {
    for (int mode:{28,29}) for (int key=0;key<12;++key) for (int kind=0;kind<3;++kind)
    for (int slot=72;slot<79;++slot) for (bool computerFirst:{false,true})
    for (bool computerOffFirst:{false,true}) {
        command(fx,key); command(fx,mode);
        ysfx_slider_set_value(fx,15,kind,true);
        // Set the selected degree's remembered kind using the real command path.
        send(fx,0x9f,slot,100);
        while (int(ysfx_slider_get_value(fx,15))!=kind) command(fx,25);
        const int shared=int(ysfx_read_vmem_single(fx,2200));
        send(fx,0x8f,slot,0);
        require(shared>=0 && shared<=127,"Real chord pitch");
        if (!computerFirst) attack(send(fx,0x90,shared,43),0,shared,43,false);
        const auto chord=send(fx,0x9f,slot,100);
        if (!computerFirst) {
            int off=0,on=0;
            for (const auto& e:chord) if(e.bytes[1]==shared) {
                off+=e.bytes[0]==0x80;on+=e.bytes[0]==0x90;
            }
            require(off==1 && on==1,"Computer attack also retriggers hardware-owned pitch");
        }
        if (computerFirst) attack(send(fx,0x90,shared,43),0,shared,43,true);
        require(send(fx,0x80,shared,0).empty(),"Computer-held pitch survives physical release");
        attack(send(fx,0x90,shared,96),0,shared,96,true);
        if (computerOffFirst) {
            const auto release=send(fx,0x8f,slot,0);
            for(const auto& e:release) require(e.bytes[1]!=shared,"Computer release preserves physical hold");
            require(send(fx,0x80,shared,0).size()==1,"Physical final release");
        } else {
            require(send(fx,0x90,shared,0).empty(),"Velocity-zero release preserves chord");
            const auto release=send(fx,0x8f,slot,0);int off=0;
            for(const auto& e:release) off+=e.bytes[0]==0x80 && e.bytes[1]==shared;
            require(off==1,"Computer final release");
        }
        require(ysfx_read_vmem_single(fx,shared)==0 && ysfx_read_vmem_single(fx,2048+shared)==0,"Both owners released");
    }
}
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    auto* config=ysfx_config_new();auto* fx=ysfx_new(config);int result=0;
    try {
        require(ysfx_load_file(fx,argv[1],0) && ysfx_compile(fx,0),"Compile actual engine");
        ysfx_set_sample_rate(fx,48000);ysfx_set_block_size(fx,256);ysfx_init(fx);
        ysfx_slider_set_value(fx,13,1,true);
        command(fx,23);physical_matrix(fx);mixed_matrix(fx);
        std::puts("1792 physical pitch/channel cases, 2016 mixed chord ownership cases: PASS");
    } catch(const std::exception& e) {std::fprintf(stderr,"FAIL: %s\n",e.what());result=1;}
    ysfx_free(fx);ysfx_config_free(config);return result;
}
