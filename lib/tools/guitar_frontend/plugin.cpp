#include <clap/clap.h>
#include "engine.h"
#include "defaults.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <new>

namespace {
constexpr unsigned editable=7, parameterCount=10;
struct Parameter { clap_id id; const char* name; double minimum, maximum, initial; bool stepped; };
constexpr std::array<Parameter,parameterCount> definitions{{
    {0,"Detect",0,1,guitar::defaults::enabled,true},
    {1,"Gate (dBFS)",-80,-12,guitar::defaults::gate_db,false},
    {2,"Confidence threshold",0.70,0.99,guitar::defaults::confidence,false},
    {3,"Stability (ms)",8,64,guitar::defaults::stability_ms,false},
    {4,"Release (ms)",8,160,guitar::defaults::release_ms,false},
    {5,"MIDI velocity",1,127,guitar::defaults::velocity,true},
    {6,"Analysis input: 0=left 1=right",0,1,guitar::defaults::input_channel,true},
    {100,"Detected MIDI note (-1=none)",-1,127,-1,true},
    {101,"Input level (dBFS)",-120,18,-120,false},
    {102,"Pitch confidence",0,1,0,false},
}};
const char* const features[]={CLAP_PLUGIN_FEATURE_AUDIO_EFFECT,CLAP_PLUGIN_FEATURE_NOTE_EFFECT,CLAP_PLUGIN_FEATURE_UTILITY,nullptr};
const clap_plugin_descriptor_t descriptor{CLAP_VERSION,"org.utrp.guitar-frontend","Guitar Frontend","UTRP",
    "","","","0.2.1","Clean monophonic guitar to MIDI; dry audio unchanged",features};
static_assert(std::atomic<double>::is_always_lock_free,"Audio-thread parameter access requires lock-free double atomics");
int indexOf(clap_id id) {
    for (unsigned i=0;i<definitions.size();++i) if (definitions[i].id==id) return int(i);
    return -1;
}
struct Instance {
    clap_plugin_t plugin{};
    const clap_host_t* host;
    const clap_host_params_t* hostParams=nullptr;
    std::array<std::atomic<double>,parameterCount> values{};
    std::array<double,3> reported{{-2,-121,-1}};
    std::atomic<bool> resetRequested{false};
    guitar::Detector detector{};
    bool active=false, processing=false;
    uint32_t maximumFrames=0;
    int sentNote=-1, wantedNote=-1;
    bool retrigger=false;
    explicit Instance(const clap_host_t* h) : host(h) {
        for (unsigned i=0;i<definitions.size();++i) values[i].store(definitions[i].initial);
    }
    guitar::Settings settings() const {
        return {values[0].load()!=0,values[1].load(),values[2].load(),values[3].load(),values[4].load()};
    }
    void clear() { detector.reset(); wantedNote=-1; retrigger=false; values[7].store(-1); values[9].store(0); }
};
Instance& self(const clap_plugin_t* p) { return *static_cast<Instance*>(p->plugin_data); }
bool validValue(unsigned i,double v) {
    const auto& d=definitions[i];
    return std::isfinite(v) && v>=d.minimum && v<=d.maximum && (!d.stepped || v==std::trunc(v));
}
void parameterEvent(Instance& s,const clap_event_header_t* h) {
    if (!h || h->space_id!=CLAP_CORE_EVENT_SPACE_ID || h->type!=CLAP_EVENT_PARAM_VALUE || h->size<sizeof(clap_event_param_value_t)) return;
    const auto& e=*reinterpret_cast<const clap_event_param_value_t*>(h);
    const int i=indexOf(e.param_id);
    if (i<0 || i>=int(editable) || e.note_id!=-1 || e.port_index!=-1 || e.channel!=-1 || e.key!=-1 || !validValue(unsigned(i),e.value)) return;
    const double before=s.values[unsigned(i)].exchange(e.value);
    if ((i==0 || i==6) && before!=e.value) s.resetRequested.store(true);
}
bool midi(const clap_output_events_t* out,uint32_t time,int note,bool on,int velocity) {
    const clap_event_midi_t event{{sizeof(event),time,CLAP_CORE_EVENT_SPACE_ID,CLAP_EVENT_MIDI,0},0,
        {uint8_t(on ? 0x91 : 0x81),uint8_t(note),uint8_t(on ? velocity : 0)}};
    return out && out->try_push && out->try_push(out,&event.header);
}
void reconcile(Instance& s,const clap_output_events_t* out,uint32_t time) {
    // A rejected note-off is retried before any new note-on. Never forget a delivered voice.
    if (s.sentNote>=0 && (s.sentNote!=s.wantedNote || s.retrigger)) {
        if (!midi(out,time,s.sentNote,false,0)) return;
        s.sentNote=-1; s.retrigger=false;
    }
    if (s.sentNote<0 && s.wantedNote>=0 && midi(out,time,s.wantedNote,true,int(s.values[5].load())))
        s.sentNote=s.wantedNote;
}
void meters(Instance& s,const clap_output_events_t* out,uint32_t time) {
    if (!out || !out->try_push) return;
    for (unsigned i=0;i<3;++i) {
        const double value=s.values[editable+i].load();
        if (value==s.reported[i]) continue;
        clap_event_param_value_t event{};
        event.header={sizeof(event),time,CLAP_CORE_EVENT_SPACE_ID,CLAP_EVENT_PARAM_VALUE,CLAP_EVENT_DONT_RECORD};
        event.param_id=definitions[editable+i].id; event.note_id=-1;
        event.port_index=event.channel=event.key=-1; event.value=value;
        if (out->try_push(out,&event.header)) s.reported[i]=value;
    }
}
bool audioValid(const clap_process_t* b) {
    if (!b || b->audio_inputs_count!=1 || b->audio_outputs_count!=1 || !b->audio_inputs || !b->audio_outputs) return false;
    const auto& in=b->audio_inputs[0]; const auto& out=b->audio_outputs[0];
    if (in.channel_count!=2 || out.channel_count!=2) return false;
    const bool floats=in.data32 && out.data32 && in.data32[0] && in.data32[1] && out.data32[0] && out.data32[1];
    const bool doubles=in.data64 && out.data64 && in.data64[0] && in.data64[1] && out.data64[0] && out.data64[1];
    return floats || doubles;
}
double copySample(const clap_process_t& b,uint32_t frame,unsigned selected) {
    const auto& in=b.audio_inputs[0]; auto& out=b.audio_outputs[0];
    if (in.data32 && out.data32) {
        const double value=in.data32[selected][frame];
        for (unsigned c=0;c<2;++c) out.data32[c][frame]=in.data32[c][frame];
        return value;
    }
    const double value=in.data64[selected][frame];
    for (unsigned c=0;c<2;++c) out.data64[c][frame]=in.data64[c][frame];
    return value;
}
clap_process_status process(const clap_plugin_t* p,const clap_process_t* b) {
    auto& s=self(p);
    if (!s.processing || !audioValid(b) || b->frames_count>s.maximumFrames) return CLAP_PROCESS_ERROR;
    auto settings=s.settings();
    if (s.resetRequested.exchange(false)) s.clear();
    const auto* input=b->in_events;
    const uint32_t count=input && input->size && input->get ? input->size(input) : 0;
    uint32_t eventIndex=0; double peak=0;
    reconcile(s,b->out_events,0);
    for (uint32_t i=0;i<b->frames_count;++i) {
        while (eventIndex<count) {
            const auto* h=input->get(input,eventIndex);
            if (h && h->time>i) break;
            parameterEvent(s,h); ++eventIndex; settings=s.settings();
            if (s.resetRequested.exchange(false)) { s.clear(); reconcile(s,b->out_events,i); }
        }
        const double sample=copySample(*b,i,unsigned(s.values[6].load()));
        if (std::isfinite(sample)) peak=std::max(peak,std::abs(sample));
        const auto update=s.detector.push(sample,settings);
        if (update.ready) {
            s.wantedNote=update.note; s.retrigger=s.retrigger || update.retrigger;
            s.values[7].store(update.note); s.values[9].store(update.observation.confidence);
            reconcile(s,b->out_events,i);
        }
    }
    b->audio_outputs[0].constant_mask=0;
    s.values[8].store(std::clamp(20*std::log10(std::max(peak,1e-6)),-120.0,18.0));
    meters(s,b->out_events,b->frames_count ? b->frames_count-1 : 0);
    return CLAP_PROCESS_CONTINUE;
}
const clap_plugin_audio_ports_t audioPorts{
    [](const clap_plugin_t*,bool){return 1u;},
    [](const clap_plugin_t*,uint32_t index,bool,clap_audio_port_info_t* info){
        if (index || !info) return false;
        *info={}; info->id=0; std::snprintf(info->name,sizeof(info->name),"Dry guitar (stereo; analyze one channel)");
        info->flags=CLAP_AUDIO_PORT_IS_MAIN | CLAP_AUDIO_PORT_SUPPORTS_64BITS | CLAP_AUDIO_PORT_REQUIRES_COMMON_SAMPLE_SIZE;
        info->channel_count=2; info->port_type=CLAP_PORT_STEREO; info->in_place_pair=0; return true;
    }};
const clap_plugin_note_ports_t notePorts{
    [](const clap_plugin_t*,bool input){return input ? 0u : 1u;},
    [](const clap_plugin_t*,uint32_t index,bool input,clap_note_port_info_t* info){
        if (index || input || !info) return false;
        *info={}; info->id=0; info->supported_dialects=info->preferred_dialect=CLAP_NOTE_DIALECT_MIDI;
        std::snprintf(info->name,sizeof(info->name),"Detected notes (MIDI channel 2)"); return true;
    }};
const clap_plugin_params_t parameters{
    [](const clap_plugin_t*){return parameterCount;},
    [](const clap_plugin_t*,uint32_t i,clap_param_info_t* info){
        if (i>=parameterCount || !info) return false;
        const auto& d=definitions[i]; *info={}; info->id=d.id;
        info->flags=(d.stepped ? CLAP_PARAM_IS_STEPPED : 0) |
            (i<editable ? CLAP_PARAM_IS_AUTOMATABLE | CLAP_PARAM_REQUIRES_PROCESS : CLAP_PARAM_IS_READONLY);
        std::snprintf(info->name,sizeof(info->name),"%s",d.name);
        info->min_value=d.minimum; info->max_value=d.maximum; info->default_value=d.initial; return true;
    },
    [](const clap_plugin_t* p,clap_id id,double* value){
        const int i=indexOf(id); if (i<0 || !value) return false;
        *value=self(p).values[unsigned(i)].load(); return true;
    },
    [](const clap_plugin_t*,clap_id id,double value,char* text,uint32_t size){
        const int i=indexOf(id); if (i<0 || !text || !size || !validValue(unsigned(i),value)) return false;
        if (id==0) std::snprintf(text,size,"%s",value!=0 ? "On (mono)" : "Off");
        else if (id==6) std::snprintf(text,size,"%s",value!=0 ? "Right" : "Left");
        else if (id==100) {
            constexpr const char* names[]={"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
            if (value<0) std::snprintf(text,size,"None");
            else std::snprintf(text,size,"%s%d (MIDI %d)",names[int(value)%12],int(value)/12-1,int(value));
        } else std::snprintf(text,size,"%.2f",value);
        return true;
    },
    [](const clap_plugin_t*,clap_id id,const char* text,double* value){
        const int i=indexOf(id); if (i<0 || i>=int(editable) || !text || !value) return false;
        char* end=nullptr; const double v=std::strtod(text,&end);
        if (end==text || *end!='\0' || !validValue(unsigned(i),v)) return false;
        *value=v; return true;
    },
    [](const clap_plugin_t* p,const clap_input_events_t* in,const clap_output_events_t*){
        if (in && in->size && in->get) for (uint32_t i=0;i<in->size(in);++i) parameterEvent(self(p),in->get(in,i));
    }};
constexpr std::size_t stateSize=8+8*editable;
const clap_plugin_state_t state{
    [](const clap_plugin_t* p,const clap_ostream_t* stream){
        if (!stream || !stream->write) return false;
        std::array<uint8_t,stateSize> bytes{{'G','F','R','O','N','T',1,0}};
        for (unsigned i=0;i<editable;++i) {
            const double value=self(p).values[i].load(); uint64_t bits=0; std::memcpy(&bits,&value,8);
            for (unsigned j=0;j<8;++j) bytes[8+i*8+j]=uint8_t(bits>>(8*j));
        }
        uint64_t pos=0;
        while (pos<bytes.size()) { const auto n=stream->write(stream,bytes.data()+pos,bytes.size()-pos);
            if (n<=0 || uint64_t(n)>bytes.size()-pos) return false;
            pos+=uint64_t(n);
        }
        return true;
    },
    [](const clap_plugin_t* p,const clap_istream_t* stream){
        if (!stream || !stream->read) return false;
        std::array<uint8_t,stateSize> bytes{}; uint64_t pos=0;
        while (pos<bytes.size()) { const auto n=stream->read(stream,bytes.data()+pos,bytes.size()-pos);
            if (n<=0 || uint64_t(n)>bytes.size()-pos) return false;
            pos+=uint64_t(n);
        }
        const uint8_t magic[]{'G','F','R','O','N','T'};
        if (std::memcmp(bytes.data(),magic,6) || bytes[7]!=0 || (bytes[6]!=1 && bytes[6]!=2)) return false;
        // Import retired v2 experiments without reviving their Mode parameter.
        // Consume and validate the extra field before committing any settings.
        if (bytes[6]==2) {
            std::array<uint8_t,8> extra{}; uint64_t cursor=0;
            while (cursor<extra.size()) {
                const auto n=stream->read(stream,extra.data()+cursor,extra.size()-cursor);
                if (n<=0 || uint64_t(n)>extra.size()-cursor) return false;
                cursor+=uint64_t(n);
            }
            uint64_t bits=0; for (unsigned j=0;j<8;++j) bits|=uint64_t(extra[j])<<(8*j);
            double retiredMode=0; std::memcpy(&retiredMode,&bits,8);
            if (retiredMode!=0 && retiredMode!=1) return false;
        }
        std::array<double,editable> next{};
        for (unsigned i=0;i<editable;++i) {
            uint64_t bits=0; for (unsigned j=0;j<8;++j) bits|=uint64_t(bytes[8+i*8+j])<<(8*j);
            std::memcpy(&next[i],&bits,8); if (!validValue(i,next[i])) return false;
        }
        auto& s=self(p); for (unsigned i=0;i<editable;++i) s.values[i].store(next[i]);
        s.resetRequested.store(true);
        if (s.hostParams && s.hostParams->rescan) s.hostParams->rescan(s.host,CLAP_PARAM_RESCAN_VALUES);
        return true;
    }};
const void* extension(const clap_plugin_t*,const char* id) {
    if (!id) return nullptr;
    if (!std::strcmp(id,CLAP_EXT_AUDIO_PORTS)) return &audioPorts;
    if (!std::strcmp(id,CLAP_EXT_NOTE_PORTS)) return &notePorts;
    if (!std::strcmp(id,CLAP_EXT_PARAMS)) return &parameters;
    if (!std::strcmp(id,CLAP_EXT_STATE)) return &state;
    return nullptr;
}
const clap_plugin_t* create(const clap_plugin_factory_t*,const clap_host_t* host,const char* id) {
    if (!host || !id || std::strcmp(id,descriptor.id) || !clap_version_is_compatible(host->clap_version)) return nullptr;
    auto* s=new(std::nothrow) Instance(host); if (!s) return nullptr;
    s->plugin={&descriptor,s,
        [](const clap_plugin_t* p){auto& s=self(p);
            if (s.host->get_extension) s.hostParams=static_cast<const clap_host_params_t*>(s.host->get_extension(s.host,CLAP_EXT_PARAMS));
            return true;},
        [](const clap_plugin_t* p){delete &self(p);},
        [](const clap_plugin_t* p,double rate,uint32_t min,uint32_t max){auto& s=self(p);
            if (s.active || !min || min>max || max>uint32_t(INT32_MAX) || !s.detector.prepare(rate)) return false;
            s.maximumFrames=max; s.active=true; s.wantedNote=-1; s.retrigger=false; return true;},
        [](const clap_plugin_t* p){auto& s=self(p); s.active=s.processing=false; s.clear();},
        [](const clap_plugin_t* p){auto& s=self(p); if (!s.active || s.processing) return false; s.processing=true; return true;},
        [](const clap_plugin_t* p){auto& s=self(p); s.processing=false; s.clear();},
        [](const clap_plugin_t* p){self(p).clear();},process,extension,[](const clap_plugin_t*){}};
    return &s->plugin;
}
const clap_plugin_factory_t factory{
    [](const clap_plugin_factory_t*){return 1u;},
    [](const clap_plugin_factory_t*,uint32_t i){return i==0 ? &descriptor : nullptr;},create};
}
extern "C" CLAP_EXPORT const clap_plugin_entry_t clap_entry{
    CLAP_VERSION,[](const char*){return true;},[]{},
    [](const char* id)->const void*{return id && !std::strcmp(id,CLAP_PLUGIN_FACTORY_ID) ? &factory : nullptr;}};
