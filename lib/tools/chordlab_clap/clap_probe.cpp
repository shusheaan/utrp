// Small independent CLAP host smoke test. Not a replacement for host certification.
#include <clap/clap.h>
#include <chrono>
#include <dlfcn.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <iostream>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <thread>
#include <vector>

void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
void gui_focus_probe(const clap_plugin_t* plugin);
struct HostState { std::thread::id main = std::this_thread::get_id(); std::atomic<bool> callback{false}; };
const void* extension(const clap_host_t*, const char* id)
{
    static const clap_host_thread_check_t threads{
        [](const clap_host_t* h) { return std::this_thread::get_id() == static_cast<HostState*>(h->host_data)->main; },
        [](const clap_host_t* h) { return std::this_thread::get_id() != static_cast<HostState*>(h->host_data)->main; }};
    static const clap_host_timer_support_t timers{
        [](const clap_host_t*, uint32_t, clap_id* id) { *id = 42; return true; },
        [](const clap_host_t*, clap_id) { return true; }};
    if (std::strcmp(id, CLAP_EXT_TIMER_SUPPORT) == 0) return &timers;
    return std::strcmp(id, CLAP_EXT_THREAD_CHECK) == 0 ? &threads : nullptr;
}
struct Events {
    std::vector<clap_event_midi_t> input;
    std::vector<clap_event_midi_t> output;
    std::vector<clap_event_param_value_t> parameters;
    std::vector<clap_event_param_gesture_t> gestures;
    clap_event_midi_sysex_t sysex{};
    std::vector<uint8_t> sysexOutput;
    uint32_t sysexTime{};
    clap_input_events_t in{this,
        [](const clap_input_events_t* e) { return uint32_t(static_cast<Events*>(e->ctx)->input.size() + (static_cast<Events*>(e->ctx)->sysex.buffer ? 1 : 0)); },
        [](const clap_input_events_t* e, uint32_t i) -> const clap_event_header_t* { auto& events = *static_cast<Events*>(e->ctx);
            return i < events.input.size() ? &events.input.at(i).header : &events.sysex.header; }};
    clap_output_events_t out{this, [](const clap_output_events_t* e, const clap_event_header_t* h) {
        if (h->space_id == CLAP_CORE_EVENT_SPACE_ID &&
            (h->type == CLAP_EVENT_PARAM_GESTURE_BEGIN || h->type == CLAP_EVENT_PARAM_GESTURE_END))
            static_cast<Events*>(e->ctx)->gestures.push_back(*reinterpret_cast<const clap_event_param_gesture_t*>(h));
        if (h->space_id == CLAP_CORE_EVENT_SPACE_ID && h->type == CLAP_EVENT_PARAM_VALUE)
            static_cast<Events*>(e->ctx)->parameters.push_back(*reinterpret_cast<const clap_event_param_value_t*>(h));
        if (h->space_id == CLAP_CORE_EVENT_SPACE_ID && h->type == CLAP_EVENT_MIDI)
            static_cast<Events*>(e->ctx)->output.push_back(*reinterpret_cast<const clap_event_midi_t*>(h));
        if (h->space_id == CLAP_CORE_EVENT_SPACE_ID && h->type == CLAP_EVENT_MIDI_SYSEX) {
            const auto& sysex = *reinterpret_cast<const clap_event_midi_sysex_t*>(h);
            auto& events = *static_cast<Events*>(e->ctx);
            events.sysexOutput.assign(sysex.buffer,sysex.buffer+sysex.size); events.sysexTime = h->time;
        }
        return true;
    }};
    void midi(uint32_t time, uint8_t status, uint8_t a, uint8_t b)
    { input.push_back({{sizeof(clap_event_midi_t), time, CLAP_CORE_EVENT_SPACE_ID, CLAP_EVENT_MIDI, 0}, 0, {status,a,b}}); }
};
struct State {
    std::vector<uint8_t> bytes;
    size_t position{};
    clap_ostream_t out{this, [](const clap_ostream_t* s, const void* data, uint64_t size) -> int64_t {
        auto& bytes = static_cast<State*>(s->ctx)->bytes;
        const auto* p = static_cast<const uint8_t*>(data);
        bytes.insert(bytes.end(), p, p + size); return int64_t(size);
    }};
    clap_istream_t in{this, [](const clap_istream_t* s, void* data, uint64_t size) -> int64_t {
        auto& state = *static_cast<State*>(s->ctx);
        auto count = std::min(size, uint64_t(state.bytes.size() - state.position));
        std::memcpy(data, state.bytes.data() + state.position, count); state.position += count;
        return int64_t(count);
    }};
};

template<class T> const T* get(const clap_plugin_t* p, const char* id)
{ const auto* ext = static_cast<const T*>(p->get_extension(p, id)); require(ext != nullptr, id); return ext; }
void startup_sustain(const clap_plugin_t* p)
{
    require(p->activate(p,48000,256,256), "Startup activate");
    std::exception_ptr failure;
    std::thread audio([&] { try {
        require(p->start_processing(p), "Startup start");
        for (int cycle=0;cycle<3;++cycle) {
            Events events;
            if (cycle==1) { events.midi(37,0x9f,87,100); events.midi(38,0x8f,87,0); }
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&events.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Startup process");
            const int expected=cycle==0?28:cycle==1?14:0;
            if (events.output.size()!=unsigned(expected)) {
                std::cerr << "Startup cycle " << cycle << ": expected " << expected
                          << " MIDI events, observed " << events.output.size() << '\n';
                for (const auto& event:events.output)
                    std::cerr << unsigned(event.data[0]) << ' ' << unsigned(event.data[1])
                              << ' ' << unsigned(event.data[2]) << " @" << event.header.time << '\n';
            }
            require(events.output.size()==unsigned(expected),"Startup ON once; manual OFF is retained");
            for (int i=0;i<expected;++i) {
                const auto& event=events.output[i];
                require(event.data[0]==0xb0+i%14 && event.data[1]==64 &&
                        event.data[2]==(cycle==0 && i>=14?127:0) &&
                        event.header.time==unsigned(cycle==0?0:37),"Exact startup/reset CC64 sequence");
            }
        }
        p->stop_processing(p);
    } catch (...) { failure=std::current_exception(); } });
    audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    std::cout << "Startup Sustain ON, old-state override, manual OFF preserved: PASS\n";
}
void metadata(const clap_plugin_t* p)
{
    auto* notes = get<clap_plugin_note_ports_t>(p, CLAP_EXT_NOTE_PORTS);
    for (bool input : {true, false}) {
        require(notes->count(p, input) == 1, "Expected one MIDI port per direction");
        clap_note_port_info_t info{}; require(notes->get(p, 0, input, &info), "Note port info");
        require(info.supported_dialects == CLAP_NOTE_DIALECT_MIDI, "MIDI 1.0 dialect only");
    }
    auto* audio = get<clap_plugin_audio_ports_t>(p, CLAP_EXT_AUDIO_PORTS);
    require(audio->count(p,true) == 0 && audio->count(p,false) == 0, "MIDI effect has no audio ports");
    auto* params = get<clap_plugin_params_t>(p, CLAP_EXT_PARAMS);
    require(params->count(p) == 21, "19 existing parameters plus Voicing mode and Voice 6");
    for (uint32_t i = 0; i < 21; ++i) {
        clap_param_info_t info{}; double value{};
        require(params->get_info(p,i,&info) && params->get_value(p,info.id,&value), "Parameter metadata/value");
        require(info.name[0] && info.max_value > info.min_value, "Nonempty parameter range");
        if (i == 13) require(value == 1, "Computer mode enabled on construction");
        if (i == 18) require(value == 0, "Dark appearance on construction");
    }
    auto* gui = get<clap_plugin_gui_t>(p, CLAP_EXT_GUI);
    require(gui->is_api_supported(p, CLAP_WINDOW_API_X11, false), "Embedded X11 GUI");
    for (int cycle = 0; cycle < 2; ++cycle) {
        require(gui->create(p, CLAP_WINDOW_API_X11, false), "Create real editor");
        uint32_t width{}, height{};
        require(gui->get_size(p, &width, &height) && width == 920 && height == 703,
                "Padded editor default size (884x683 content)");
        for (auto size : {std::pair<uint32_t,uint32_t>{736,580}, {1636,1220}, {920,703}}) {
            const auto requested = size;
            require(gui->adjust_size(p, &size.first, &size.second), "Adjust editor size");
            require(size == requested, "Padding preserves original canvas resize range");
            require(gui->set_size(p, size.first, size.second), "Resize editor");
            require(gui->get_size(p, &width, &height) && width == size.first && height == size.second,
                    "Host sees actual padded dimensions");
        }
        gui->destroy(p);
    }
    std::cout << "ports, 21 parameters, default Dark/computer mode, X11 GUI create/resize/recreate: PASS\n";
}
void parameter_writes(const clap_plugin_t* p)
{
    const auto* params = get<clap_plugin_params_t>(p, CLAP_EXT_PARAMS);
    require(p->activate(p,48000,32,256), "Parameter-test activate");
    for (uint32_t index : {13u, 0u, 18u, 19u}) for (double value : {0.0, 1.0, 0.0, 1.0}) {
        clap_param_info_t info{}; require(params->get_info(p,index,&info), "Parameter-test info");
        std::exception_ptr failure;
        std::thread audio([&] { try {
            require(p->start_processing(p), "Parameter-test start");
            clap_event_param_value_t event{};
            event.header = {sizeof(event),0,CLAP_CORE_EVENT_SPACE_ID,CLAP_EVENT_PARAM_VALUE,0};
            event.param_id = info.id; event.cookie = info.cookie; event.note_id = -1;
            event.port_index = event.channel = event.key = -1; event.value = value;
            clap_input_events_t input{&event, [](const clap_input_events_t*) { return 1u; },
                [](const clap_input_events_t* in, uint32_t) -> const clap_event_header_t* { return &static_cast<clap_event_param_value_t*>(in->ctx)->header; }};
            Events output;
            params->flush(p,&input,&output.out);
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&output.in; block.out_events=&output.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Parameter-test process");
            p->stop_processing(p);
        } catch (...) { failure=std::current_exception(); } });
        audio.join(); if (failure) std::rethrow_exception(failure);
        double actual{}; require(params->get_value(p,info.id,&actual) && actual==value,
            "Host write must survive audio readback before deferred main-thread notification");
    }
    p->deactivate(p);
    std::cout << "16 host parameter writes including Appearance/Voicing mode survive process before callbacks: PASS\n";
}
void key_notification(const clap_plugin_t* p)
{
    auto* params = get<clap_plugin_params_t>(p, CLAP_EXT_PARAMS);
    auto* timer = get<clap_plugin_timer_support_t>(p, CLAP_EXT_TIMER_SUPPORT);
    clap_param_info_t key{}; require(params->get_info(p,0,&key), "Key parameter info");
    require(p->activate(p,48000,256,256), "Key notification activate");
    Events observed;
    for (int cycle = 0; cycle < 10; ++cycle) {
        std::exception_ptr failure;
        std::thread audio([&] { try {
            require(p->start_processing(p), "Key notification start");
            Events events;
            if (cycle == 1) events.midi(0,0x9f,64,100); // E major / C# minor, command 4
            if (cycle == 2) events.midi(0,0x8f,64,0);
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&observed.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR, "Key notification process");
            p->stop_processing(p);
        } catch (...) { failure=std::current_exception(); } });
        audio.join(); if (failure) std::rethrow_exception(failure);
        p->on_main_thread(p);
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
        timer->on_timer(p,42);
    }
    p->deactivate(p);
    const auto event = std::find_if(observed.parameters.begin(),observed.parameters.end(),[&](const auto& e) {
        return e.param_id==key.id && std::abs(e.value-4.0/11)<0.00001;
    });
    require(event!=observed.parameters.end(), "Computer key emits host Key parameter change");
    for (auto type : {CLAP_EVENT_PARAM_GESTURE_BEGIN, CLAP_EVENT_PARAM_GESTURE_END})
        require(std::any_of(observed.gestures.begin(),observed.gestures.end(),[&](const auto& e) {
            return e.param_id==key.id && e.header.type==type;
        }), "Key change has complete host edit gesture");
    require(event->header.flags & CLAP_EVENT_IS_LIVE, "User key change must be marked live");
    require(event->note_id==-1 && event->port_index==-1 && event->channel==-1 && event->key==-1,
        "UI Key change must target global parameter, not note 0");
    std::cout << "Key selection emits globally targeted CLAP parameter notification: PASS\n";
}

void process_matrix(const clap_plugin_t* p)
{
    for (double rate : {44100.0, 48000.0, 96000.0}) {
        require(p->activate(p,rate,32,1024), "activate");
        std::exception_ptr failure;
        std::thread audio([&] { try {
            require(p->start_processing(p), "start processing");
            for (uint32_t frames : {32u,64u,256u,1024u}) {
                Events e; e.midi(1,0xb0,1,91); e.midi(3,0xd0,45,0); e.midi(7,0xc0,7,0); e.midi(9,0xf8,0,0);
                const uint8_t data[]{0xf0,0x7d,0x01,0xf7};
                e.sysex = {{sizeof(clap_event_midi_sysex_t),11,CLAP_CORE_EVENT_SPACE_ID,CLAP_EVENT_MIDI_SYSEX,0},0,data,4};
                clap_process_t block{}; block.steady_time = -1; block.frames_count = frames;
                block.in_events = &e.in; block.out_events = &e.out;
                require(p->process(p,&block) != CLAP_PROCESS_ERROR, "process");
                for (const auto& event : e.input)
                    require(std::any_of(e.output.begin(),e.output.end(),[&](const auto& out) {
                        return out.header.time == event.header.time && std::memcmp(out.data,event.data,3)==0;
                    }), "CC / pressure / program bytes and sample offsets");
                require(e.sysexTime == 11 && e.sysexOutput == std::vector<uint8_t>(data,data+4), "SysEx bytes and sample offset");
                p->reset(p);
            }
            p->stop_processing(p);
        } catch (...) { failure = std::current_exception(); } });
        audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    }
    std::cout << "12 sample-rate/block-size combinations, reset/reactivation: PASS\n";
}

void appearance_preserves_held_midi(const clap_plugin_t* p)
{
    const auto* params = get<clap_plugin_params_t>(p, CLAP_EXT_PARAMS);
    clap_param_info_t info{}; require(params->get_info(p,18,&info), "Appearance parameter");
    require(p->activate(p,48000,32,256), "Appearance MIDI activate");
    std::exception_ptr failure;
    std::thread audio([&] { try {
        require(p->start_processing(p), "Appearance MIDI start");
        const auto process = [&](Events& events) {
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&events.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Appearance MIDI process");
        };
        Events warmup; process(warmup);
        Events held; held.midi(1,0x90,60,64); held.midi(3,0x90,67,91); held.midi(5,0x9f,74,100);
        process(held);
        for (const auto& input : {held.input[0], held.input[1]})
            require(std::any_of(held.output.begin(),held.output.end(),[&](const auto& out) {
                return out.header.time==input.header.time && std::memcmp(out.data,input.data,3)==0;
            }), "Hardware notes/velocity preserved alongside computer chord");
        for (double value : {0.0,1.0,0.0,1.0}) {
            clap_event_param_value_t event{};
            event.header={sizeof(event),0,CLAP_CORE_EVENT_SPACE_ID,CLAP_EVENT_PARAM_VALUE,0};
            event.param_id=info.id; event.cookie=info.cookie; event.note_id=-1;
            event.port_index=event.channel=event.key=-1; event.value=value;
            clap_input_events_t input{&event,[](const clap_input_events_t*) { return 1u; },
                [](const clap_input_events_t* in,uint32_t) -> const clap_event_header_t* {
                    return &static_cast<clap_event_param_value_t*>(in->ctx)->header; }};
            Events changed; params->flush(p,&input,&changed.out); process(changed);
            require(changed.output.empty(), "Theme change must not emit notes, note-offs or CC");
        }
        Events release; release.midi(1,0x8f,74,0); release.midi(3,0x80,60,0); release.midi(5,0x80,67,0);
        process(release);
        require(!release.output.empty(), "Mixed notes release after theme changes");
        p->stop_processing(p);
    } catch (...) { failure=std::current_exception(); } });
    audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    std::cout << "Dark/Bright switching preserves held mixed MIDI without generated events: PASS\n";
}
void display_only_channel(const clap_plugin_t* p)
{
    require(p->activate(p,48000,256,256), "Display-only activate");
    std::exception_ptr failure;
    std::thread audio([&] { try {
        require(p->start_processing(p), "Display-only start");
        const auto process = [&](Events& events) {
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&events.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Display-only process");
        };
        Events warmup; process(warmup);
        for (int note=0;note<128;++note) {
            Events display; display.midi(1,0x9e,note,90); display.midi(9,0x8e,note,0);
            process(display); require(display.output.empty(),"Analysis notes never reach instrument");
        }
        for (int status : {0xae,0xbe,0xce,0xde,0xee}) {
            Events display; display.midi(1,status,64,127); process(display);
            require(display.output.empty(),"Analysis channel controllers never reach instrument");
        }
        for (bool displayFirst : {false,true}) {
            Events first; first.midi(1,displayFirst?0x9e:0x90,60,73); process(first);
            require(first.output.size()==(displayFirst?0u:2u),"Independent note on ownership plus sustain sync");
            Events second; second.midi(1,displayFirst?0x90:0x9e,60,73); process(second);
            require(second.output.size()==(displayFirst?2u:0u),"Analysis cannot suppress real MIDI or its sustain sync");
            Events off; off.midi(1,0x8e,60,0); process(off);
            require(off.output.empty(),"Analysis release cannot cut real MIDI");
            Events realOff; realOff.midi(1,0x80,60,0); process(realOff);
            require(realOff.output.size()==1 && realOff.output[0].data[0]==0x80,
                    "Real MIDI releases normally");
        }
        p->stop_processing(p);
    } catch (...) { failure=std::current_exception(); } });
    audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    std::cout << "Display-only channel: 128 pitches, controller isolation, same-note real MIDI ownership: PASS\n";
}
void mixed_retrigger(const clap_plugin_t* p)
{
    require(p->activate(p,48000,256,256), "Retrigger activate");
    std::exception_ptr failure;
    std::thread audio([&] { try {
        require(p->start_processing(p), "Retrigger start");
        const auto process = [&](Events& events) {
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&events.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Retrigger process");
        };
        const auto send = [&](uint8_t status,uint8_t note,uint8_t value) {
            Events events; events.midi(37,status,note,value); process(events); return events.output;
        };
        Events warmup; process(warmup);
        // This case reuses a plugin whose prior startup-state test leaves S off.
        // Establish our baseline explicitly rather than relying on activate().
        send(0x9f,87,100); send(0x8f,87,0); // Explicit sustain off.
        send(0x9f,82,100); send(0x8f,82,0); // Toggle baseline on.
        for (bool pedal : {false,true}) for (bool computerOffFirst : {false,true}) {
            send(0xb0,64,pedal?127:0);
            const auto chord=send(0x9f,74,100);
            require(chord.size()>=3,"Retrigger chord sounds");
            const auto firstNote=std::find_if(chord.begin(),chord.end(),[](const auto& e){return e.data[0]==0x90;});
            require(firstNote!=chord.end(),"Computer chord contains a NoteOn after sustain sync");
            const auto note=firstNote->data[1];
            send(0x9e,note,100); // Guitar analysis must not add instrument ownership.
            for (uint8_t velocity : {1,43,96,127}) {
                const auto attack=send(0x90,note,velocity);
                require(attack.size()==3,"Shared physical press syncs sustain then emits off/on pair");
                require(attack[0].data[0]==0xb0 && attack[0].data[1]==64 && attack[0].data[2]==(pedal?0:127),
                        "Effective pedal state precedes the repeated attack");
                require(attack[1].data[0]==0x80 && attack[1].data[1]==note && attack[1].data[2]==0,
                        "Retrigger releases preceding synth voice first");
                require(attack[2].data[0]==0x90 && attack[2].data[1]==note && attack[2].data[2]==velocity,
                        "Retrigger preserves exact physical velocity");
                require(attack[0].header.time==37 && attack[1].header.time==37 && attack[2].header.time==37,"No extra retrigger delay");
                require(send(0x80,note,0).empty(),"Chord survives physical release");
            }
            send(0x90,note,75);
            if (computerOffFirst) {
                for (const auto& e : send(0x8f,74,0))
                    require(e.data[1]!=note,"Physical hold survives chord release");
                require(send(0x80,note,0).size()==1,"Physical final release ignores guitar display");
            } else {
                require(send(0x90,note,0).empty(),"Zero-velocity release preserves chord");
                const auto release=send(0x8f,74,0);
                require(std::count_if(release.begin(),release.end(),[&](const auto& e) {
                    return e.data[0]==0x80 && e.data[1]==note;
                })==1,"Computer final release ignores guitar display");
            }
            require(send(0x8e,note,0).empty(),"Analysis release stays display-only");
            send(0xb0,64,0);
        }
        p->stop_processing(p);
    } catch (...) { failure=std::current_exception(); } });
    audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    std::cout << "Mixed retrigger: velocities 1/43/96/127, sustain, both release orders, display isolation, exact offsets: PASS\n";
}
void held_chord_navigation(const clap_plugin_t* p)
{
    require(p->activate(p,48000,256,256), "Held navigation activate");
    std::exception_ptr failure;
    std::thread audio([&] { try {
        require(p->start_processing(p), "Held navigation start");
        std::array<bool,128> sounding{};
        const auto process = [&](Events& events) {
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&events.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Held navigation process");
            for (const auto& e : events.output) {
                const int kind=e.data[0]&0xf0, note=e.data[1];
                if (kind==0x90) sounding[note]=e.data[2]!=0;
                if (kind==0x80) sounding[note]=false;
            }
        };
        Events warmup; process(warmup);
        for (int degree=72; degree<=78; ++degree) {
            Events reset; reset.midi(0,0x9f,81,100); reset.midi(1,0x8f,81,0); process(reset);
            Events held; held.midi(0,0x9f,degree,100); process(held);
            const auto initial=sounding;
            require(std::count(initial.begin(),initial.end(),true)>=3,"Held chord sounds");
            for (int command : {80,80,79,79}) {
                const auto previous=sounding;
                Events move; move.midi(0,0x9f,command,100); move.midi(1,0x8f,command,0); process(move);
                const auto low=std::find(sounding.begin(),sounding.end(),true)-sounding.begin();
                const auto oldLow=std::find(previous.begin(),previous.end(),true)-previous.begin();
                require(command==80 ? low>oldLow : low<oldLow,"Held chord moves in requested direction");
                require(std::count(sounding.begin(),sounding.end(),true)==std::count(initial.begin(),initial.end(),true),
                        "Voicing preserves note count without stuck notes");
            }
            require(sounding==initial,"L L H H returns to original voicing while chord remains held");
            Events release; release.midi(0,0x8f,degree,0); process(release);
            require(std::none_of(sounding.begin(),sounding.end(),[](bool down){return down;}),
                    "Chord release after navigation releases all notes");
        }
        p->stop_processing(p);
    } catch (...) { failure=std::current_exception(); } });
    audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    std::cout << "7 held degrees: L/L/H/H audible voicing, exact return and full release: PASS\n";
}
void guitar_mode(const clap_plugin_t* p)
{
    require(p->activate(p,48000,256,256), "Guitar activate");
    std::exception_ptr failure;
    std::thread audio([&] { try {
        require(p->start_processing(p), "Guitar start");
        std::array<bool,128> sounding{};
        const auto process = [&](Events& events) {
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&events.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Guitar process");
            for (const auto& e : events.output) {
                const int type=e.data[0]&0xf0, note=e.data[1];
                if (type==0x90 && e.data[2]) {
                    require(!sounding[note],"Guitar duplicate NoteOn"); sounding[note]=true;
                }
                if (type==0x80 || (type==0x90 && !e.data[2])) {
                    require(sounding[note],"Guitar unmatched NoteOff"); sounding[note]=false;
                }
            }
        };
        const auto command = [&](int cmd) {
            Events e; e.midi(0,0x9f,60+cmd,100); e.midi(1,0x8f,60+cmd,0); process(e);
        };
        Events warmup; process(warmup);
        for (int degree=72; degree<=78; ++degree) {
            command(28); Events held; held.midi(0,0x9f,degree,100); process(held);
            const auto piano=sounding;
            command(29);
            require(std::count(sounding.begin(),sounding.end(),true)>=3,"Guitar sounds");
            for (int i=0;i<16;++i) command(19);
            const auto low=sounding;
            for (int i=0;i<16;++i) command(20);
            require(sounding!=low,"Guitar fingerings change along fretboard");
            const auto high=sounding;
            command(28); require(sounding==piano,"CLAP preserves Piano voicing");
            command(29); require(sounding==high,"CLAP preserves Guitar fingering");
            Events up; up.midi(0,0x8f,degree,0); process(up);
            require(std::count(sounding.begin(),sounding.end(),true)==0,"Guitar fully releases");
        }
        p->stop_processing(p);
    } catch (...) { failure=std::current_exception(); } });
    audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    std::cout << "Guitar/Piano CLAP switches, held H/L across catalog, exact recall, no stuck/duplicate notes: PASS\n";
}
void pedal_baseline(const clap_plugin_t* p)
{
    require(p->activate(p,48000,256,256), "Pedal activate");
    std::exception_ptr failure;
    std::thread audio([&] { try {
        require(p->start_processing(p), "Pedal start");
        const auto process = [&](Events& events) {
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&events.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Pedal process");
        };
        const auto send = [&](uint8_t status,uint8_t note,uint8_t value) {
            Events events; events.midi(37,status,note,value); process(events); return events.output;
        };
        const auto toggle = [&] {
            const auto result=send(0x9f,82,100); send(0x8f,82,0); return result;
        };
        Events warmup; process(warmup);
        send(0x9f,87,100); send(0x8f,87,0); // Explicit baseline reset, independent of prior probes.
        for (int base : {0,1}) {
            if (base) toggle();
            for (int channel=0;channel<14;++channel) {
                for (int value : {0,63,64,127,127,0}) {
                    const auto out=send(0xb0+channel,64,value);
                    require(out.size()==1,"CLAP emits only one effective pedal CC");
                    const auto& event=out[0];
                    require(event.data[0]==0xb0+channel && event.data[1]==64 &&
                            event.data[2]==((base!=(value>=64))?127:0) && event.header.time==37,
                            "CLAP pedal XOR baseline, channel and exact offset");
                }
            }
        }
        send(0xb0,64,127); // Baseline ON, physical down: effective OFF.
        const auto out=toggle(); // Baseline OFF while held: channel 1 ON, others OFF.
        require(out.size()==14,"CLAP baseline toggles update every musical channel");
        for (int channel=0;channel<14;++channel)
            require(out[channel].data[2]==(channel==0?127:0),"CLAP remembers pedal per channel");
        send(0xb0,64,0);
        toggle(); // Baseline ON; focus cleanup must not turn it off.
        require(send(0xbf,123,0).empty(),"CLAP focus cleanup preserves baseline without CC output");
        require(send(0x9f,83,100).empty(),"CLAP focus command preserves baseline");
        send(0x8f,83,0);
        for (int value : {127,127,0,0,127,0}) {
            const auto held=send(0xb0,64,value);
            require(held.size()==1 && held[0].data[2]==(value?0:127),
                    "CLAP pedal remains momentary after focus loss with inverted baseline");
        }
        toggle(); // Restore OFF for subsequent probes.
        require(send(0xbe,64,127).empty() && send(0xbf,64,127).empty(),"Reserved pedal channels isolated");
        p->stop_processing(p);
    } catch (...) { failure=std::current_exception(); } });
    audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    std::cout << "CLAP pedal baseline: both defaults, 14 channels, threshold, repeat, held toggle, reserved isolation: PASS\n";
}
void performance_controls(const clap_plugin_t* p)
{
    require(p->activate(p,48000,256,256), "Performance controls activate");
    std::exception_ptr failure;
    std::thread audio([&] { try {
        require(p->start_processing(p), "Performance controls start");
        const auto process = [&](Events& events) {
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&events.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Performance controls process");
        };
        Events warmup; process(warmup);
        for (int channel=0;channel<16;++channel) {
            for (int controller : {1,7,11}) {
                for (int value=0;value<128;++value) {
                    Events events; events.midi(37,0xb0+channel,controller,value); process(events);
                    require(events.output.size()==(channel<14?1u:0u),"CC routed only for musical channels");
                    if (channel<14) {
                        const auto& out=events.output[0];
                        require(out.header.time==37 && out.data[0]==0xb0+channel &&
                            out.data[1]==controller && out.data[2]==value,"CC preserved byte-for-byte and sample-exact");
                    }
                }
            }
            for (int bend : {0,1,4096,8191,8192,8193,12288,16383}) {
                Events events; events.midi(53,0xe0+channel,bend&127,bend>>7); process(events);
                require(events.output.size()==(channel<14?1u:0u),"Bend routed only for musical channels");
                if (channel<14) {
                    const auto& out=events.output[0];
                    require(out.header.time==53 && out.data[0]==0xe0+channel &&
                        out.data[1]==(bend&127) && out.data[2]==(bend>>7),"Full 14-bit pitch bend preserved");
                }
            }
        }
        p->stop_processing(p);
    } catch (...) { failure=std::current_exception(); } });
    audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    std::cout << "Performance controls: CC1/7/11 all values, 14-bit bend, 14 musical + 2 reserved channels: PASS\n";
}
void sustain_press_toggle(const clap_plugin_t* p)
{
    require(p->activate(p,48000,256,256), "Sustain activate");
    std::exception_ptr failure;
    std::thread audio([&] { try {
        require(p->start_processing(p), "Sustain start");
        const auto process = [&](Events& events) {
            clap_process_t block{}; block.frames_count=256; block.steady_time=-1;
            block.in_events=&events.in; block.out_events=&events.out;
            require(p->process(p,&block)!=CLAP_PROCESS_ERROR,"Sustain process");
        };
        Events warmup; process(warmup);
        Events chord; chord.midi(0,0x9f,74,100); process(chord);
        for (int value : {127,0}) {
            Events press; press.midi(0,0x9f,82,100); process(press);
            require(press.output.size()==14,"Sustain emits CC on 14 musical channels, not display/control channels");
            for (const auto& e : press.output)
                require((e.data[0]&0xf0)==0xb0 && (e.data[0]&0xf)<14 && e.data[1]==64 && e.data[2]==value,
                        "Space press toggles correct pedal value without note changes");
            Events repeat; repeat.midi(0,0x9f,82,100); process(repeat);
            require(repeat.output.empty(),"Holding Space does not retoggle");
            Events up; up.midi(0,0x8f,82,0); process(up);
            require(up.output.empty(),"Space release does not retoggle");
        }
        Events release; release.midi(0,0x8f,74,0); process(release);
        require(!release.output.empty(),"Held chord still releases after Sustain toggles");
        p->stop_processing(p);
    } catch (...) { failure=std::current_exception(); } });
    audio.join(); p->deactivate(p); if (failure) std::rethrow_exception(failure);
    std::cout << "Space command: toggle on press, no repeat/release toggle, no chord reset: PASS\n";
}
int main(int argc, char** argv)
{
    try {
        require(argc == 2 || argc == 3, "Usage: clap_probe /path/Chord Lab.clap [legacy-state.bin|--focus]");
        const bool focusProbe=argc==3 && std::strcmp(argv[2],"--focus")==0;
        auto* library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL); require(library, "dlopen");
        auto* entry = static_cast<const clap_plugin_entry_t*>(dlsym(library,"clap_entry"));
        require(entry && entry->init(argv[1]), "entry init");
        auto* factory = static_cast<const clap_plugin_factory_t*>(entry->get_factory(CLAP_PLUGIN_FACTORY_ID));
        require(factory && factory->get_plugin_count(factory) == 1, "One dedicated plugin");
        auto* desc = factory->get_plugin_descriptor(factory,0);
        require(std::strcmp(desc->id,"org.utrp.chordlab") == 0, "Stable plugin ID");
        HostState state;
        clap_host_t host{CLAP_VERSION, &state, "ChordLab probe", "UTRP", "", "0.1",
            extension, [](const clap_host_t*) {}, [](const clap_host_t*) {},
            [](const clap_host_t* h) { static_cast<HostState*>(h->host_data)->callback = true; }};
        auto* a = factory->create_plugin(factory,&host,desc->id); require(a && a->init(a), "Instance A init");
        if (argc == 3 && !focusProbe) {
            std::ifstream file(argv[2], std::ios::binary);
            require(file.good(), "Open legacy state");
            State legacy; legacy.bytes.assign(std::istreambuf_iterator<char>(file), {});
            require(!legacy.bytes.empty() && get<clap_plugin_state_t>(a, CLAP_EXT_STATE)->load(a,&legacy.in),
                    "Legacy 18-parameter state loads without an Appearance entry");
            std::cout << "legacy state import: PASS\n";
        }
        metadata(a); startup_sustain(a);
        State savedOff;
        require(get<clap_plugin_state_t>(a,CLAP_EXT_STATE)->save(a,&savedOff.out),"Save explicitly disabled Sustain");
        display_only_channel(a); mixed_retrigger(a); held_chord_navigation(a); pedal_baseline(a); performance_controls(a); sustain_press_toggle(a); parameter_writes(a); key_notification(a); process_matrix(a); appearance_preserves_held_midi(a); guitar_mode(a);
        State saved; auto* sa = get<clap_plugin_state_t>(a,CLAP_EXT_STATE);
        require(sa->save(a,&saved.out) && !saved.bytes.empty(), "State save");
        std::string bytes(saved.bytes.begin(), saved.bytes.end());
        require(bytes.find("/tmp/") == std::string::npos, "State must not reference temporary source path");
        auto* b = factory->create_plugin(factory,&host,desc->id); require(b && b->init(b), "Instance B init");
        require(get<clap_plugin_state_t>(b,CLAP_EXT_STATE)->load(b,&savedOff.in), "Restore explicitly disabled Sustain");
        startup_sustain(b);
        require(get<clap_plugin_state_t>(b,CLAP_EXT_STATE)->load(b,&saved.in), "State restore in independent instance");
        clap_param_info_t appearance{}; double appearanceValue{};
        auto* params = get<clap_plugin_params_t>(b, CLAP_EXT_PARAMS);
        require(params->get_info(b,18,&appearance) && params->get_value(b,appearance.id,&appearanceValue)
                && appearanceValue == 1, "Bright appearance restored in independent instance");
        clap_param_info_t mode{}; double modeValue{};
        require(params->get_info(b,19,&mode) && params->get_value(b,mode.id,&modeValue)
                && modeValue == 1, "Guitar mode restored in independent CLAP instance");
        startup_sustain(b); process_matrix(b);
        if (focusProbe) gui_focus_probe(b);
        b->destroy(b); a->destroy(a); entry->deinit(); dlclose(library);
        std::cout << "portable state, two independent instances, lifecycle: PASS\n"; return 0;
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
