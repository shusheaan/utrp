// Isolated, wall-clock-paced CLAP host for headless Sway validation.
// No ALSA/PipeWire devices. MIDI injection comes only from the named test file.
#include <clap/clap.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <atomic>
#include <chrono>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

namespace {
void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
struct Host {
    Display* display{}; Window window{};
    std::thread::id main=std::this_thread::get_id();
    std::atomic<bool> done{false};
    std::mutex mutex; std::vector<clap_event_midi_t> pending;
    uint32_t width{920},height{703};
};
const void* extension(const clap_host_t*,const char* id)
{
    static const clap_host_thread_check_t threads{
        [](const clap_host_t*h){return std::this_thread::get_id()==static_cast<Host*>(h->host_data)->main;},
        [](const clap_host_t*h){return std::this_thread::get_id()!=static_cast<Host*>(h->host_data)->main;}};
    static const clap_host_timer_support_t timers{
        [](const clap_host_t*,uint32_t,clap_id* id){*id=42;return true;},[](const clap_host_t*,clap_id){return true;}};
    static const clap_host_gui_t gui{
        [](const clap_host_t*){},
        [](const clap_host_t*h,uint32_t w,uint32_t v){auto&s=*static_cast<Host*>(h->host_data);s.width=w;s.height=v;XResizeWindow(s.display,s.window,w,v);XFlush(s.display);return true;},
        [](const clap_host_t*){return true;},[](const clap_host_t*){return true;},[](const clap_host_t*,bool){}};
    if(!std::strcmp(id,CLAP_EXT_THREAD_CHECK))return &threads;
    if(!std::strcmp(id,CLAP_EXT_TIMER_SUPPORT))return &timers;
    if(!std::strcmp(id,CLAP_EXT_GUI))return &gui;
    return nullptr;
}
struct Events {
    std::vector<clap_event_midi_t> input;
    std::ofstream& log;
    clap_input_events_t in{this,[](const clap_input_events_t*e){return uint32_t(static_cast<Events*>(e->ctx)->input.size());},
        [](const clap_input_events_t*e,uint32_t i) -> const clap_event_header_t* {return &static_cast<Events*>(e->ctx)->input.at(i).header;}};
    clap_output_events_t out{this,[](const clap_output_events_t*e,const clap_event_header_t*h){
        if(h->space_id==CLAP_CORE_EVENT_SPACE_ID&&h->type==CLAP_EVENT_MIDI){
            const auto*m=reinterpret_cast<const clap_event_midi_t*>(h);
            auto& log=static_cast<Events*>(e->ctx)->log;
            log<<unsigned(m->data[0])<<' '<<unsigned(m->data[1])<<' '<<unsigned(m->data[2])<<'\n';log.flush();
        }return true;}};
};
void inject(Host& host,const char* file,uint64_t& last)
{
    std::ifstream stream(file);uint64_t serial;unsigned status,note,value;
    while(stream>>serial>>status>>note>>value)if(serial>last){
        check(status>=0x80&&status<=0xef&&note<128&&value<128,"invalid test MIDI");last=serial;
        clap_event_midi_t event{{sizeof(event),0,CLAP_CORE_EVENT_SPACE_ID,CLAP_EVENT_MIDI,CLAP_EVENT_IS_LIVE},0,{uint8_t(status),uint8_t(note),uint8_t(value)}};
        std::lock_guard<std::mutex> lock(host.mutex);host.pending.push_back(event);
    }
}
void audio(const clap_plugin_t* plugin,Host& host,const char* logFile)
{
    std::ofstream log(logFile);Events events{{},log};
    if(!plugin->start_processing(plugin)){host.done=true;return;}
    auto next=std::chrono::steady_clock::now();int64_t frame=0;
    while(!host.done){
        {std::lock_guard<std::mutex> lock(host.mutex);events.input.swap(host.pending);host.pending.clear();}
        clap_process_t block{};block.frames_count=256;block.steady_time=frame;
        block.in_events=&events.in;block.out_events=&events.out;
        if(plugin->process(plugin,&block)==CLAP_PROCESS_ERROR){host.done=true;break;}
        events.input.clear();frame+=256;next+=std::chrono::nanoseconds(5333333);
        std::this_thread::sleep_until(next);
    }
    plugin->stop_processing(plugin);
}
}
int main(int argc,char**argv)
{
    try {
        check(argc==4,"usage: game_preview plugin.clap midi-input.txt midi-output.txt");
        Host state;state.display=XOpenDisplay(nullptr);check(state.display,"Xwayland DISPLAY required");
        state.window=XCreateSimpleWindow(state.display,DefaultRootWindow(state.display),600,340,920,703,0,0,0);
        XStoreName(state.display,state.window,"Chord Lab - isolated game preview");
        XClassHint hint{const_cast<char*>("chordlab-game-test"),const_cast<char*>("Chord Lab")};XSetClassHint(state.display,state.window,&hint);
        XSelectInput(state.display,state.window,StructureNotifyMask);XMapWindow(state.display,state.window);XFlush(state.display);
        auto* library=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);check(library,"load built CLAP");
        auto* entry=static_cast<const clap_plugin_entry_t*>(dlsym(library,"clap_entry"));check(entry&&entry->init(argv[1]),"CLAP entry");
        auto* factory=static_cast<const clap_plugin_factory_t*>(entry->get_factory(CLAP_PLUGIN_FACTORY_ID));check(factory,"CLAP factory");
        clap_host_t host{CLAP_VERSION,&state,"UTRP isolated preview","UTRP","","1",extension,
            [](const clap_host_t*){},[](const clap_host_t*){},[](const clap_host_t*){}};
        auto* plugin=factory->create_plugin(factory,&host,factory->get_plugin_descriptor(factory,0)->id);
        check(plugin&&plugin->init(plugin),"initialize plugin");
        auto* gui=static_cast<const clap_plugin_gui_t*>(plugin->get_extension(plugin,CLAP_EXT_GUI));
        auto* timer=static_cast<const clap_plugin_timer_support_t*>(plugin->get_extension(plugin,CLAP_EXT_TIMER_SUPPORT));
        check(gui&&timer&&gui->create(plugin,CLAP_WINDOW_API_X11,false),"create GUI");
        clap_window_t parent{};parent.api=CLAP_WINDOW_API_X11;parent.x11=state.window;
        check(gui->set_parent(plugin,&parent)&&gui->show(plugin),"show GUI");
        check(plugin->activate(plugin,48000,256,256),"activate");
        std::thread processing(audio,plugin,std::ref(state),argv[3]);uint64_t serial=0;
        try {
            while(!state.done){
                while(XPending(state.display)){
                    XEvent event;XNextEvent(state.display,&event);
                    if(event.type==DestroyNotify)state.done=true;
                    if(event.type==ConfigureNotify){
                        const auto& c=event.xconfigure;
                        if(c.width!=int(state.width)||c.height!=int(state.height)){
                            state.width=uint32_t(c.width);state.height=uint32_t(c.height);gui->set_size(plugin,state.width,state.height);
                        }
                    }
                }
                inject(state,argv[2],serial);plugin->on_main_thread(plugin);timer->on_timer(plugin,42);
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        }catch(...){state.done=true;processing.join();throw;}
        processing.join();gui->destroy(plugin);plugin->deactivate(plugin);plugin->destroy(plugin);entry->deinit();dlclose(library);XCloseDisplay(state.display);
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
