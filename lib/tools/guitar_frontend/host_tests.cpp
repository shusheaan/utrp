#include <clap/clap.h>
#include <dlfcn.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(bool ok,const char* why) {if (!ok) throw std::runtime_error(why);}
struct Events {
    std::vector<clap_event_param_value_t> input;
    std::vector<clap_event_midi_t> output;
    int midiBudget=-1; bool reject=false; uint32_t frames=0,lastTime=0; bool first=true;
    clap_input_events_t in{this,
        [](const clap_input_events_t* e){return uint32_t(static_cast<Events*>(e->ctx)->input.size());},
        [](const clap_input_events_t* e,uint32_t i)->const clap_event_header_t*{return &static_cast<Events*>(e->ctx)->input.at(i).header;}};
    clap_output_events_t out{this,[](const clap_output_events_t* e,const clap_event_header_t* h){
        auto& s=*static_cast<Events*>(e->ctx);
        require(h->time<s.frames,"output offset inside block");
        require(s.first || h->time>=s.lastTime,"sorted output events");s.first=false;s.lastTime=h->time;
        if (s.reject) return false;
        if (h->type==CLAP_EVENT_MIDI) {
            if (s.midiBudget==0) return false;
            if (s.midiBudget>0) --s.midiBudget;
            s.output.push_back(*reinterpret_cast<const clap_event_midi_t*>(h));
        }
        return true;
    }};
    void set(clap_id id,double value,uint32_t time=0) {
        clap_event_param_value_t e{};e.header={sizeof(e),time,CLAP_CORE_EVENT_SPACE_ID,CLAP_EVENT_PARAM_VALUE,0};
        e.param_id=id;e.note_id=-1;e.port_index=e.channel=e.key=-1;e.value=value;input.push_back(e);
    }
};
struct Stream {
    std::vector<uint8_t> bytes;std::size_t pos=0;
    clap_ostream_t out{this,[](const clap_ostream_t* s,const void* data,uint64_t size)->int64_t{
        auto& b=static_cast<Stream*>(s->ctx)->bytes;const auto* p=static_cast<const uint8_t*>(data);
        const auto n=std::min(uint64_t(3),size);b.insert(b.end(),p,p+n);return int64_t(n);}};
    clap_istream_t in{this,[](const clap_istream_t* s,void* data,uint64_t size)->int64_t{
        auto& x=*static_cast<Stream*>(s->ctx);const auto n=std::min({uint64_t(5),size,uint64_t(x.bytes.size()-x.pos)});
        std::memcpy(data,x.bytes.data()+x.pos,n);x.pos+=n;return int64_t(n);}};
};
const clap_host_t host{CLAP_VERSION,nullptr,"Guitar Frontend test host","UTRP","","1",
    [](const clap_host_t*,const char*)->const void*{return nullptr;},[](const clap_host_t*){},[](const clap_host_t*){},[](const clap_host_t*){}};
template<class T> const T* ext(const clap_plugin_t* p,const char* id) {
    const auto* result=static_cast<const T*>(p->get_extension(p,id));require(result,id);return result;
}
double value(const clap_plugin_t* p,clap_id id) {
    double v=0;require(ext<clap_plugin_params_t>(p,CLAP_EXT_PARAMS)->get_value(p,id,&v),"get param");return v;
}
void set(const clap_plugin_t* p,clap_id id,double v) {
    Events e;e.set(id,v);ext<clap_plugin_params_t>(p,CLAP_EXT_PARAMS)->flush(p,&e.in,nullptr);
}
void metadata(const clap_plugin_t* p) {
    const auto* audio=ext<clap_plugin_audio_ports_t>(p,CLAP_EXT_AUDIO_PORTS);
    for (bool input:{true,false}) {
        require(audio->count(p,input)==1,"one stereo audio port");clap_audio_port_info_t info{};
        require(audio->get(p,0,input,&info) && info.channel_count==2 && (info.flags&CLAP_AUDIO_PORT_SUPPORTS_64BITS),"stereo32/64");
        require(!audio->get(p,1,input,&info),"invalid audio index");
    }
    const auto* notes=ext<clap_plugin_note_ports_t>(p,CLAP_EXT_NOTE_PORTS);
    require(notes->count(p,true)==0 && notes->count(p,false)==1,"audio to MIDI ports");
    clap_note_port_info_t ni{};require(notes->get(p,0,false,&ni) && ni.preferred_dialect==CLAP_NOTE_DIALECT_MIDI,"MIDI output");
    const auto* params=ext<clap_plugin_params_t>(p,CLAP_EXT_PARAMS);require(params->count(p)==10,"10 mono controls/meters");
    for (unsigned i=0;i<10;++i) {clap_param_info_t info{};require(params->get_info(p,i,&info),"param info");
        require(value(p,info.id)==info.default_value,"defaults");
        require(bool(info.flags&CLAP_PARAM_IS_READONLY)==(i>=7),"meter readonly");}
    require(!p->activate(p,8000,32,256),"invalid sample rate");
    require(!p->activate(p,48000,0,256),"invalid block range");
    require(!p->get_extension(p,"not-an-extension"),"unknown extension");
    std::cout<<"metadata, parameters, boundaries: PASS\n";
}
template<class T> void block(const clap_plugin_t* p,Events& e,unsigned frames,double rate,uint64_t start,int note,bool right=false,bool silence=false,bool inplace=false) {
    std::array<T,1024> left{},r{},ol{},orr{};require(frames<=left.size(),"test block size");
    for (unsigned i=0;i<frames;++i) {
        const double time=(start+i)/rate;
        const double phase=6.283185307179586*440*std::exp2((note-69)/12.0)*time;
        const double sampleValue=.2*std::sin(phase);
        const T sample=silence ? 0 : T(sampleValue);
        (right?r:left)[i]=sample;
    }
    T* ins[]{left.data(),r.data()};T* outs[]{inplace?left.data():ol.data(),inplace?r.data():orr.data()};
    clap_audio_buffer_t in{},out{};in.channel_count=out.channel_count=2;
    if constexpr(sizeof(T)==4) {in.data32=ins;out.data32=outs;} else {in.data64=ins;out.data64=outs;}
    clap_process_t b{};b.steady_time=int64_t(start);b.frames_count=frames;b.audio_inputs=&in;b.audio_outputs=&out;
    b.audio_inputs_count=b.audio_outputs_count=1;b.in_events=&e.in;b.out_events=&e.out;
    e.frames=frames;e.first=true;e.lastTime=0;
    require(p->process(p,&b)==CLAP_PROCESS_CONTINUE,"process continues");
    for (unsigned i=0;i<frames;++i) {
        require(outs[0][i]==left[i] && outs[1][i]==r[i],"bit-exact dry audio");
    }
    e.input.clear();
}
void matrix(const clap_plugin_t* p) {
    unsigned cases=0;
    for (double rate:{32000.,44100.,48000.,96000.,192000.}) for (unsigned size:{32u,64u,256u,1024u}) for (bool doubles:{false,true}) {
        require(p->activate(p,rate,1,1024),"activate matrix");require(p->start_processing(p),"start matrix");
        Events e;const auto total=uint64_t(rate*.4);
        for (uint64_t pos=0;pos<total;pos+=size) {
            if (doubles) block<double>(p,e,size,rate,pos,64,false,pos>rate*.20,true);
            else block<float>(p,e,size,rate,pos,64,false,pos>rate*.20);
        }
        require(e.output.size()==2 && e.output[0].data[0]==0x91 && e.output[0].data[1]==64 && e.output[0].data[2]==90 && e.output[1].data[0]==0x81,"one on/off channel2");
        p->stop_processing(p);p->deactivate(p);++cases;
    }
    std::cout<<"rate/block/float64 matrix="<<cases<<": PASS\n";
}
void lifecycle(const clap_plugin_t* p) {
    require(p->activate(p,48000,1,1024) && p->start_processing(p),"lifecycle activate");
    Events e;
    for (uint64_t pos=0;pos<12000;pos+=256) block<float>(p,e,256,48000,pos,60);
    require(e.output.size()==1,"initial note");
    e.reject=true;p->reset(p);block<float>(p,e,256,48000,0,60,false,true);
    e.reject=false;block<float>(p,e,256,48000,256,60,false,true);
    require(e.output.size()==2 && e.output.back().data[0]==0x81,"rejected noteoff retried after reset");
    e.output.clear();e.reject=true;
    for (uint64_t pos=0;pos<12000;pos+=256) block<float>(p,e,256,48000,pos,60);
    require(e.output.empty(),"rejected noteon not considered sent");e.reject=false;
    block<float>(p,e,256,48000,12000,60);require(e.output.size()==1 && e.output[0].data[0]==0x91,"noteon retried");
    e.set(0,0,83);block<float>(p,e,256,48000,12256,60);
    require(e.output.size()==2 && e.output.back().data[0]==0x81 && e.output.back().header.time==83,"sample-offset disable releases");
    set(p,0,1);set(p,6,1);e.output.clear();
    for (uint64_t pos=0;pos<12000;pos+=256) block<float>(p,e,256,48000,pos,67,true);
    require(e.output.size()==1 && e.output[0].data[1]==67,"right channel");
    p->stop_processing(p);require(p->start_processing(p),"resume");e.output.clear();
    block<float>(p,e,256,48000,0,67,true,true);require(e.output.size()==1 && e.output[0].data[0]==0x81,"stop/start releases delivered voice");
    p->stop_processing(p);p->deactivate(p);set(p,6,0);
    std::cout<<"event backpressure, reset, disable offsets, right input, stop/start: PASS\n";
}
void serialization(const clap_plugin_t* a,const clap_plugin_t* b) {
    const auto* sa=ext<clap_plugin_state_t>(a,CLAP_EXT_STATE);const auto* sb=ext<clap_plugin_state_t>(b,CLAP_EXT_STATE);
    set(a,1,-36);set(a,5,71);Stream bytes;require(sa->save(a,&bytes.out),"partial stream save");
    require(bytes.bytes.size()==64 && bytes.bytes[6]==1,"save mono v1 state");
    require(sb->load(b,&bytes.in) && value(b,1)==-36 && value(b,5)==71,"cross-instance state load");
    for (double mode:{0.,1.,-1.,.5,2.,std::numeric_limits<double>::quiet_NaN()}) {
        Stream old;old.bytes=bytes.bytes;old.bytes[6]=2;
        uint64_t bits=0;std::memcpy(&bits,&mode,8);
        for (unsigned j=0;j<8;++j) old.bytes.push_back(uint8_t(bits>>(8*j)));
        set(b,1,-40);
        const bool valid=mode==0 || mode==1;
        require(sb->load(b,&old.in)==valid,"retired v2 mode validation");
        require(value(b,1)==(valid?-36:-40),"v2 transactional import");
        old.pos=0;old.bytes.pop_back();set(b,1,-40);
        require(!sb->load(b,&old.in) && value(b,1)==-40,"truncated v2 transactional");
    }
    bytes.pos=0;require(sb->load(b,&bytes.in),"restore mono state");
    Stream unknown;unknown.bytes=bytes.bytes;unknown.bytes[6]=3;
    require(!sb->load(b,&unknown.in) && value(b,1)==-36,"unknown version transactional");
    set(a,1,-45);require(value(b,1)==-36,"instance isolation");
    bytes.pos=0;bytes.bytes[0]=0;require(!sb->load(b,&bytes.in) && value(b,1)==-36,"bad state transactional");
    bytes.pos=0;bytes.bytes.resize(12);require(!sb->load(b,&bytes.in),"truncated state");
    for (double invalid:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-1000.}) set(b,1,invalid);
    require(value(b,1)==-36,"invalid parameter values ignored");set(b,5,71.5);require(value(b,5)==71,"fractional stepped rejected");
    set(b,100,60);require(value(b,100)==-1,"meter host-write ignored");
    const auto* params=ext<clap_plugin_params_t>(b,CLAP_EXT_PARAMS);double parsed=0;char text[64]{};
    require(params->text_to_value(b,1,"-42",&parsed) && parsed==-42,"parse text");
    require(!params->text_to_value(b,1,"nan",&parsed) && !params->text_to_value(b,1,"-42oops",&parsed),"bad text rejected");
    require(params->value_to_text(b,100,64,text,sizeof(text)) && std::string(text)=="E4 (MIDI 64)","note names");
    require(!params->get_value(b,7,&parsed) && !params->get_value(b,103,&parsed),"retired parameters absent");
    require(!params->text_to_value(b,7,"Mono",&parsed),"Mode is not exposed");
    std::cout<<"portable transactional state, partial streams, invalid values, two instances: PASS\n";
}
}
int main(int argc,char** argv) {
    try {
        require(argc==2,"plugin path required");void* library=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);require(library,dlerror());
        const auto* entry=static_cast<const clap_plugin_entry_t*>(dlsym(library,"clap_entry"));require(entry && entry->init(argv[1]),"entry init");
        const auto* factory=static_cast<const clap_plugin_factory_t*>(entry->get_factory(CLAP_PLUGIN_FACTORY_ID));require(factory && factory->get_plugin_count(factory)==1,"factory");
        const auto* description=factory->get_plugin_descriptor(factory,0);require(description && std::string(description->id)=="org.utrp.guitar-frontend","stable ID");
        require(!factory->create_plugin(factory,&host,"wrong"),"invalid ID");
        const auto* a=factory->create_plugin(factory,&host,description->id);const auto* b=factory->create_plugin(factory,&host,description->id);
        require(a && b && a->init(a) && b->init(b),"instantiate");
        metadata(a);matrix(a);lifecycle(a);serialization(a,b);
        a->destroy(a);b->destroy(b);entry->deinit();dlclose(library);
        std::cout<<"PASS independent CLAP host (not DAW certification)\n";
    } catch(const std::exception& e) {std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}
}
