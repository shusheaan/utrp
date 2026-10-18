// Physical CC64 temporarily inverts the displayed, pedal-up baseline.
#include "ysfx.h"
#include <array>
#include <cstdio>
#include <stdexcept>
#include <vector>

struct Event { uint32_t frame; std::array<uint8_t,3> bytes; };
using Events = std::vector<Event>;
void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
Events send(ysfx_t* fx, int status, int note, int value) {
    const uint8_t bytes[]{uint8_t(status),uint8_t(note),uint8_t(value)};
    const ysfx_midi_event_t input{0,37,3,bytes};
    require(ysfx_send_midi(fx,&input),"Accept MIDI input");
    ysfx_process_float(fx,nullptr,nullptr,0,0,256);
    Events out; ysfx_midi_event_t event{};
    while (ysfx_receive_midi(fx,&event)) {
        require(event.size==3,"Three-byte MIDI output");
        out.push_back({event.offset,{event.data[0],event.data[1],event.data[2]}});
    }
    return out;
}
Events command(ysfx_t* fx, int cmd) {
    const auto out=send(fx,0x9f,60+cmd,100);
    require(send(fx,0x8f,60+cmd,0).empty(),"Command release is silent");
    return out;
}
void cc(const Event& event, int channel, int value) {
    require(event.bytes==std::array<uint8_t,3>{uint8_t(0xb0+channel),64,uint8_t(value)},
            "Correct channel and effective sustain; no note-off or mute messages");
    require(event.frame==37,"Pedal has no extra sample delay");
}
void baseline(ysfx_t* fx, int value) {
    require(ysfx_slider_get_value(fx,17)==value,"S indicator remains the pedal-up baseline");
}
void truth_table(ysfx_t* fx) {
    for (int base : {0,1}) {
        if (base) command(fx,22);
        for (int channel=0;channel<14;++channel) {
            for (int value : {0,63,64,127,127,64,63,0}) {
                const auto out=send(fx,0xb0+channel,64,value);
                require(out.size()==1,"One CC per pedal event");
                cc(out[0],channel,(base!=(value>=64))?127:0);
                baseline(fx,base);
            }
        }
    }
    command(fx,22);
}
void toggling_while_pressed(ysfx_t* fx) {
    send(fx,0xb0,64,127); send(fx,0xb5,64,127);
    for (int base : {1,0}) {
        const auto out=command(fx,22);
        require(out.size()==14,"Space updates only 14 musical channels");
        for (int channel=0;channel<14;++channel)
            cc(out[channel],channel,(base!=(channel==0 || channel==5))?127:0);
        baseline(fx,base);
    }
    send(fx,0xb0,64,0); send(fx,0xb5,64,0);
}
void sustained_hold(ysfx_t* fx) {
    for (int base : {0,1}) {
        if (base) command(fx,22);
        cc(send(fx,0xb0,64,127).at(0),0,base?0:127);
        for (int block=0;block<750;++block) { // Four seconds without another pedal event.
            ysfx_process_float(fx,nullptr,nullptr,0,0,256);
            ysfx_midi_event_t event{};
            require(!ysfx_receive_midi(fx,&event),"Holding pedal never toggles or times out");
            baseline(fx,base);
            require(ysfx_read_vmem_single(fx,2480)==1,"Physical pedal stays down until release");
        }
        cc(send(fx,0xb0,64,0).at(0),0,base?127:0);
        baseline(fx,base);
    }
    command(fx,22);
}
void held_notes_and_reserved_channels(ysfx_t* fx) {
    send(fx,0x90,60,96);
    send(fx,0x9f,74,100);
    for (int base : {1,0}) {
        command(fx,22);
        for (int value : {127,0}) {
            const auto out=send(fx,0xb0,64,value);
            require(out.size()==1,"Pedal does not release held notes");
            cc(out[0],0,(base!=(value>=64))?127:0);
            require(ysfx_read_vmem_single(fx,60)==1,"Physical note ownership survives pedal");
            require(ysfx_slider_get_value(fx,8)==1,"Computer chord survives pedal");
            require(send(fx,0xbe,64,value).empty(),"Guitar analysis cannot affect sustain");
            require(send(fx,0xbf,64,value).empty(),"Control channel cannot affect sustain");
            baseline(fx,base);
        }
    }
    send(fx,0x8f,74,0); send(fx,0x80,60,0);
}
void focus_and_reset(ysfx_t* fx) {
    send(fx,0xb0,64,127); command(fx,22);
    const auto focus=command(fx,23);
    require(focus.empty(),"Focus loss must not change pedal or baseline");
    baseline(fx,1);
    require(send(fx,0xbf,123,0).empty(),"Editor close cleanup preserves baseline");
    baseline(fx,1);
    cc(send(fx,0xb0,64,0).at(0),0,127);
    cc(send(fx,0xb0,64,127).at(0),0,0);
    cc(send(fx,0xb0,64,0).at(0),0,127);
    send(fx,0xb5,64,127);
    const auto reset=send(fx,0xb5,121,0);
    require(reset.size()==2 && reset[0].bytes[1]==121,"Reset controllers forwarded first");
    cc(reset[1],5,127); baseline(fx,1);
    command(fx,22);
    for (int resetCC : {120,123}) {
        send(fx,0xb0,64,127); send(fx,0xb0,resetCC,0);
        const auto out=command(fx,22);
        cc(out[0],0,127); // Reset discarded the stale physical pedal-down state.
        command(fx,22);
    }
}
int main(int argc,char** argv) {
    if (argc!=2) return 2;
    auto* config=ysfx_config_new(); auto* fx=ysfx_new(config); int result=0;
    try {
        require(ysfx_load_file(fx,argv[1],0) && ysfx_compile(fx,0),"Compile actual engine");
        ysfx_set_sample_rate(fx,48000); ysfx_set_block_size(fx,256); ysfx_init(fx);
        ysfx_slider_set_value(fx,13,1,true);
        command(fx,23);
        truth_table(fx); toggling_while_pressed(fx); sustained_hold(fx);
        held_notes_and_reserved_channels(fx); focus_and_reset(fx);
        std::puts("Pedal baseline: 224 threshold/channel cases, mid-pedal toggles, indicator, held notes, reset and isolation: PASS");
    } catch (const std::exception& error) { std::fprintf(stderr,"FAIL: %s\n",error.what()); result=1; }
    ysfx_free(fx); ysfx_config_free(config); return result;
}
