// Exercise the actual embedded JSFX, not a reimplementation of its MIDI logic.
#include "ysfx.h"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <set>
#include <vector>

using Notes = std::set<int>;
void check(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
ysfx_t* load(ysfx_config_t* config, const char* path) {
    auto* fx=ysfx_new(config);
    check(ysfx_load_file(fx,path,0) && ysfx_compile(fx,0), "Compile actual engine");
    ysfx_set_sample_rate(fx,48000); ysfx_set_block_size(fx,256); ysfx_init(fx);
    const ysfx_time_info_t time{120,ysfx_playback_stopped,0,0,{4,4}};
    ysfx_set_time_info(fx,&time);
    ysfx_slider_set_value(fx,13,1,true);
    return fx;
}
void process(ysfx_t* fx, Notes& notes) {
    ysfx_process_float(fx,nullptr,nullptr,0,0,256);
    ysfx_midi_event_t event{};
    while (ysfx_receive_midi(fx,&event)) {
        check(event.size==3, "Three-byte MIDI");
        const auto* d=event.data;
        check((d[0]&15)!=15,"Control channel never leaks");
        if ((d[0]&0xf0)==0x90 && d[2]) check(notes.insert(d[1]).second,"No duplicate MIDI NoteOn");
        if ((d[0]&0xf0)==0x80 || ((d[0]&0xf0)==0x90 && !d[2]))
            check(notes.erase(d[1])==1,"No unmatched NoteOff");
    }
}
void midi(ysfx_t* fx, Notes& notes, uint8_t status, uint8_t note, uint8_t velocity=100) {
    const uint8_t bytes[]{status,note,velocity};
    ysfx_midi_event_t event{0,0,3,bytes};
    check(ysfx_send_midi(fx,&event),"MIDI accepted"); process(fx,notes);
}
void command(ysfx_t* fx, Notes& notes, int command) {
    midi(fx,notes,0x9f,60+command); midi(fx,notes,0x8f,60+command,0);
}
void validate(ysfx_t* fx, const Notes& notes) {
    constexpr int steps[]{0,2,4,5,7,9,11};
    const int key=ysfx_slider_get_value(fx,0), degree=ysfx_slider_get_value(fx,1);
    const int count=3+ysfx_slider_get_value(fx,15);
    Notes pcs, expected;
    for (int i=0;i<count;++i) expected.insert((key+steps[(degree+2*i)%7])%12);
    for (int note:notes) { pcs.insert(note%12); check(note>=0&&note<=127,"MIDI range"); }
    check(pcs==expected,"All and only chord pitch classes, including ninth");
    if (ysfx_slider_get_value(fx,19)==1) {
        bool found=false;
        for (int anchor=0;anchor<=18;++anchor) {
            Notes region;
            for (int open : {40,45,50,55,59,64})
                for (int fret=anchor;fret<anchor+3;++fret)
                    if (expected.count((open+fret)%12)) region.insert(open+fret);
            found |= notes==region;
        }
        check(found,"Exact union of all distinct pitches in a three-fret hand region");
    } else check(notes.size()==size_t(count),"Piano retains closed-position voice count");
}
void matrix(ysfx_t* fx, Notes& notes) {
    for (int key=0;key<12;++key) {
        command(fx,notes,key);
        for (int degree=0;degree<7;++degree) {
            midi(fx,notes,0x9f,72+degree);
            for (int kind=0;kind<3;++kind) {
                command(fx,notes,28); const Notes piano=notes; validate(fx,notes);
                command(fx,notes,29); validate(fx,notes);
                const Notes guitar=notes;
                command(fx,notes,29); check(notes==guitar,"K is idempotent");
                // Reach each edge and visit all intermediate regions while held.
                for (int i=0;i<16;++i) { command(fx,notes,19); validate(fx,notes); }
                const Notes lowest=notes; command(fx,notes,19); check(notes==lowest,"Lower edge clamps");
                for (int i=0;i<16;++i) { command(fx,notes,20); validate(fx,notes); }
                const Notes highest=notes; command(fx,notes,20); check(notes==highest,"Upper edge clamps");
                command(fx,notes,28); check(notes==piano,"Piano voicing preserved through Guitar navigation");
                command(fx,notes,29); check(notes==highest,"Guitar position preserved through Piano mode");
                command(fx,notes,28); command(fx,notes,25);
            }
            midi(fx,notes,0x8f,72+degree,0); check(notes.empty(),"Release all voices");
        }
    }
}
void persistence(ysfx_config_t* config, const char* path, ysfx_t* fx, Notes& notes) {
    command(fx,notes,29); midi(fx,notes,0x9f,74); command(fx,notes,19);
    const Notes guitar=notes; midi(fx,notes,0x8f,74,0);
    ysfx_state_t* saved=ysfx_save_state(fx); check(saved!=nullptr,"Save v3 state");
    ysfx_t* restored=load(config,path);
    check(ysfx_load_state(restored,saved),"Restore independent instance");
    Notes actual; process(restored,actual); check(actual.empty(),"State does not replay held notes");
    check(ysfx_slider_get_value(restored,19)==1,"Guitar mode persists");
    midi(restored,actual,0x9f,74); check(actual==guitar,"Guitar position persists");
    midi(restored,actual,0x8f,74,0); check(actual.empty(),"Restored notes release");
    ysfx_state_free(saved); ysfx_free(restored);
}
void upper_position_persistence(ysfx_config_t* config, const char* path) {
    auto* fx=load(config,path); Notes notes; process(fx,notes);
    command(fx,notes,1); command(fx,notes,29); midi(fx,notes,0x9f,74);
    for (int i=0;i<20;++i) command(fx,notes,20);
    check(ysfx_read_vmem_single(fx,3100)==18,"Dbmaj7 reaches anchor 18");
    check(notes.count(84)==1,"Twentieth fret high E string sounds C6");
    const Notes upper=notes; midi(fx,notes,0x8f,74,0);
    auto* saved=ysfx_save_state(fx); check(saved!=nullptr,"Save high anchor");
    auto* restored=load(config,path);
    check(ysfx_load_state(restored,saved),"Restore high anchor");
    process(restored,notes); check(notes.empty(),"High anchor does not replay notes");
    check(ysfx_read_vmem_single(restored,3100)==18,"Anchor 18 survives v3 validation");
    midi(restored,notes,0x9f,74); check(notes==upper,"Restored upper region matches");
    midi(restored,notes,0x8f,74,0); check(notes.empty(),"Upper region releases cleanly");
    ysfx_state_free(saved); ysfx_free(restored); ysfx_free(fx);
}
void mixed(ysfx_t* fx, Notes& notes) {
    command(fx,notes,29); midi(fx,notes,0x9f,74);
    const auto guitar=notes; const int shared=*guitar.begin();
    midi(fx,notes,0x90,shared,43);
    command(fx,notes,28); check(notes.count(shared),"Mode switch preserves hardware-owned pitch");
    command(fx,notes,29); check(notes==guitar,"Mixed-input guitar return");
    midi(fx,notes,0x8f,74,0); check(notes==Notes{shared},"Computer release preserves hardware note");
    midi(fx,notes,0x80,shared,0); check(notes.empty(),"Final hardware release");
    midi(fx,notes,0x9f,74); command(fx,notes,23); check(notes.empty(),"Focus loss releases all region voices");
}
void open_position_persistence(ysfx_config_t* config, const char* path) {
    auto* fx=load(config,path); Notes notes; process(fx,notes);
    command(fx,notes,0); command(fx,notes,29); midi(fx,notes,0x9f,74);
    check(ysfx_slider_get_value(fx,15)==1,"Initial major seventh");
    for (int i=0;i<16;++i) command(fx,notes,19);
    check(notes==Notes{40,47,52,55,59,60,64},"Cmaj7 open region sounds all seven distinct pitches");
    midi(fx,notes,0x8f,74,0); check(notes.empty(),"Open chord releases cleanly");
    auto* saved=ysfx_save_state(fx); check(saved!=nullptr,"Save anchor zero");
    auto* restored=load(config,path);
    check(ysfx_load_state(restored,saved),"Load anchor zero");
    process(restored,notes); check(notes.empty(),"No replay on restoring open position");
    midi(restored,notes,0x9f,74);
    check(notes==Notes{40,47,52,55,59,60,64},"Fret zero survives state validation, not reset to default");
    command(restored,notes,20);
    check(notes==Notes{43,48,55,59,60,64,67},"H/L jumps directly from anchor zero to user anchor three");
    command(restored,notes,19);
    check(notes==Notes{40,47,52,55,59,60,64},"Held chord returns to open position");
    midi(restored,notes,0x8f,74,0); check(notes.empty(),"No stuck notes after open-position navigation");
    ysfx_state_free(saved); ysfx_free(restored); ysfx_free(fx);
}
void expanded_voice_ownership(ysfx_config_t* config, const char* path) {
    auto* fx=load(config,path); Notes notes; process(fx,notes);
    command(fx,notes,0); command(fx,notes,29); midi(fx,notes,0x9f,74);
    for (int i=0;i<16;++i) command(fx,notes,19);
    check(notes.size()==7,"Region exceeds legacy six-voice limit");
    const int high=*notes.rbegin();
    midi(fx,notes,0x90,high,27);
    command(fx,notes,20); validate(fx,notes);
    midi(fx,notes,0x8f,74,0);
    check(notes==Notes{high},"Seventh voice remains owned by physical MIDI");
    midi(fx,notes,0x80,high,0); check(notes.empty(),"Seventh voice hardware release");
    midi(fx,notes,0x9f,74); command(fx,notes,22);
    command(fx,notes,23); check(notes.empty(),"Focus loss releases expanded chord with sustain");
    midi(fx,notes,0x8f,74,0); check(notes.empty(),"Late key-up after focus loss is harmless");
    ysfx_free(fx);
}
void automatic_position_recall(ysfx_config_t* config, const char* path) {
    for (int mode : {28,29}) {
        auto* fx=load(config,path); Notes notes; process(fx,notes);
        command(fx,notes,mode);
        for (int slot=72;slot<=78;++slot) {
            midi(fx,notes,0x9f,slot); const Notes initial=notes;
            command(fx,notes,19); const Notes moved=notes;
            check(moved!=initial,"H moves the currently sounding chord");
            midi(fx,notes,0x8f,slot,0); check(notes.empty(),"Release after move");
            midi(fx,notes,0x9f,slot); check(notes==moved,"Repress recalls H position without confirm/save key");
            command(fx,notes,20); check(notes==initial,"Held L returns to original position");
            midi(fx,notes,0x8f,slot,0);
            command(fx,notes,19); check(notes.empty(),"Idle navigation never auditions a chord");
            const int other=72+(slot-72+1)%7;
            midi(fx,notes,0x9f,other); midi(fx,notes,0x8f,other,0);
            midi(fx,notes,0x9f,slot); check(notes==moved,"Another degree does not erase this position");
            midi(fx,notes,0x8f,slot,0);
        }
        ysfx_free(fx);
    }
}
void current_chord_reset(ysfx_config_t* config, const char* path) {
    for (int mode : {28,29}) for (int key=0;key<12;++key) for (int kind=0;kind<3;++kind) {
        auto* fx=load(config,path); Notes notes; process(fx,notes);
        command(fx,notes,key); command(fx,notes,mode);
        for (int slot=72;slot<=78;++slot) {
            midi(fx,notes,0x9f,slot);
            while (ysfx_slider_get_value(fx,15)!=kind) command(fx,notes,25);
            command(fx,notes,21); const Notes initial=notes;
            if (ysfx_slider_get_value(fx,0)!=key || ysfx_slider_get_value(fx,15)!=kind)
                std::fprintf(stderr,"reset context mode=%d key=%d kind=%d slot=%d actual key=%g kind=%g\n",
                             mode,key,kind,slot,ysfx_slider_get_value(fx,0),ysfx_slider_get_value(fx,15));
            check(ysfx_slider_get_value(fx,0)==key && ysfx_slider_get_value(fx,15)==kind,
                  "Reset preserves key and chord type");
            validate(fx,notes);
            // Keep a moved voicing in the other mode, which reset must not touch.
            const int otherMode=mode==28 ? 29 : 28;
            command(fx,notes,otherMode); command(fx,notes,19); const Notes otherVoicing=notes;
            command(fx,notes,mode);
            command(fx,notes,19); check(notes!=initial,"Move away from default before reset");
            command(fx,notes,30); check(ysfx_read_vmem_single(fx,3200+(slot-72+5)%7)==1,"Enable RL before held reset");
            command(fx,notes,21); check(notes==initial,"Held reset restores rooted default pitch set");
            check(ysfx_read_vmem_single(fx,3200+(slot-72+5)%7)==0,"Enter clears current RL flag");
            command(fx,notes,otherMode); check(notes==otherVoicing,"Reset preserves other mode memory");
            command(fx,notes,mode); check(notes==initial,"Reset position recalled after mode switch");
            midi(fx,notes,0x8f,slot,0);
            const int other=72+(slot-72+1)%7;
            midi(fx,notes,0x9f,other); command(fx,notes,19); command(fx,notes,30); const Notes otherChord=notes;
            midi(fx,notes,0x8f,other,0);
            midi(fx,notes,0x9f,slot); command(fx,notes,19); command(fx,notes,30); midi(fx,notes,0x8f,slot,0);
            command(fx,notes,21); check(notes.empty(),"Idle reset does not audition");
            midi(fx,notes,0x9f,other); check(notes==otherChord,"Reset preserves other degree memory");
            midi(fx,notes,0x8f,other,0);
            midi(fx,notes,0x9f,slot); check(notes==initial,"Repress recalls reset without confirmation");
            midi(fx,notes,0x8f,slot,0); check(notes.empty(),"No stuck notes after reset");
        }
        auto* state=ysfx_save_state(fx); check(state!=nullptr,"Save reset state");
        auto* restored=load(config,path); check(ysfx_load_state(restored,state),"Load reset state");
        Notes actual; process(restored,actual);
        midi(fx,notes,0x9f,78); midi(restored,actual,0x9f,78);
        check(actual==notes,"Reset memory survives state save/load");
        midi(fx,notes,0x8f,78,0); midi(restored,actual,0x8f,78,0);
        ysfx_state_free(state); ysfx_free(restored); ysfx_free(fx);
    }
}
void display_only_notes(ysfx_config_t* config, const char* path) {
    auto* fx=load(config,path); Notes notes; process(fx,notes);
    for (int note=0;note<128;++note) {
        midi(fx,notes,0x9e,note,90);
        check(notes.empty(),"Display input never sounds");
        check(ysfx_read_vmem_single(fx,14*128+note)==1,"Display pitch enters visual held map");
        midi(fx,notes,0x8e,note,0);
        check(ysfx_read_vmem_single(fx,14*128+note)==0,"Display releases without lingering highlight");
    }
    for (int mode : {28,29}) for (bool displayFirst : {false,true}) {
        command(fx,notes,mode); midi(fx,notes,0x9f,74); const Notes chord=notes;
        const int shared=*chord.begin(); midi(fx,notes,0x8f,74,0);
        if (displayFirst) midi(fx,notes,0x9e,shared,90);
        midi(fx,notes,0x9f,74);
        if (!displayFirst) midi(fx,notes,0x9e,shared,90);
        check(notes==chord,"Display cannot silence or double-trigger computer chord");
        midi(fx,notes,0x8f,74,0);
        check(notes.empty(),"Computer releases even while identical analysis pitch remains");
        check(ysfx_read_vmem_single(fx,14*128+shared)==1,"Analysis highlight survives computer release");
        midi(fx,notes,0xbe,123,0);
        check(ysfx_read_vmem_single(fx,14*128+shared)==0,"Analysis All Notes Off clears only display");
    }
    midi(fx,notes,0x9e,50,90); command(fx,notes,23);
    check(ysfx_read_vmem_single(fx,14*128+50)==1,"Computer focus loss does not kill live guitar display");
    midi(fx,notes,0x9e,50,90); midi(fx,notes,0x8e,50,0);
    check(ysfx_read_vmem_single(fx,14*128+50)==1,"Overlapping display note ownership");
    midi(fx,notes,0x9e,50,0);
    check(ysfx_read_vmem_single(fx,14*128+50)==0,"Velocity-zero Note On releases display");
    ysfx_free(fx);
}
Notes without_root(const Notes& notes, int root) {
    Notes result;
    for (int note:notes) if (note%12!=root) result.insert(note);
    return result;
}
void rootless_matrix(ysfx_config_t* config, const char* path) {
    constexpr int steps[]{0,2,4,5,7,9,11};
    auto* fx=load(config,path); Notes notes; process(fx,notes);
    for (int key=0;key<12;++key) {
        command(fx,notes,key);
        for (int slot=72;slot<=78;++slot) {
            midi(fx,notes,0x9f,slot);
            const int degree=(slot-72+5)%7, root=(key+steps[degree])%12;
            for (int kind=0;kind<3;++kind) {
                while (ysfx_slider_get_value(fx,15)!=kind) command(fx,notes,25);
                for (int mode:{28,29}) {
                    command(fx,notes,mode); command(fx,notes,21);
                    for (int inversion=0;inversion<3+kind;++inversion) {
                        const Notes rooted=notes;
                        // Holding G/repeated key-down must toggle exactly once.
                        midi(fx,notes,0x9f,90);
                        check(notes==without_root(rooted,root),"G removes only harmonic roots, preserving all other exact pitches");
                        midi(fx,notes,0x9f,90);
                        check(notes==without_root(rooted,root),"Held G is not a second toggle");
                        midi(fx,notes,0x8f,90,0);
                        command(fx,notes,30); check(notes==rooted,"G restores exact rooted pitches");
                        command(fx,notes,20);
                    }
                }
            }
            midi(fx,notes,0x8f,slot,0); check(notes.empty(),"Rootless toggles leave no owned notes");
        }
    }
    ysfx_free(fx);
}
void rootless_navigation(ysfx_config_t* config, const char* path) {
    auto* fx=load(config,path); Notes notes; process(fx,notes);
    midi(fx,notes,0x9f,74);
    for (int kind=0;kind<3;++kind) {
        while (ysfx_slider_get_value(fx,15)!=kind) command(fx,notes,25);
        command(fx,notes,21); command(fx,notes,30);
        for (int direction:{20,19}) for (int i=0;i<75;++i) {
            const Notes before=notes; command(fx,notes,direction);
            check(notes.size()==size_t(2+kind),"Rootless H/L preserves reduced voice count");
            check(notes==without_root(notes,0),"H/L and Tab do not reintroduce roots");
            if (notes!=before) check(direction==20 ? *notes.begin()>*before.begin() : *notes.begin()<*before.begin(),
                                    "Rootless H/L strictly moves actual bass, or clamps at edge");
        }
    }
    midi(fx,notes,0x8f,74,0); check(notes.empty(),"Release navigated rootless chord");
    ysfx_free(fx);
}
void rootless_memory(ysfx_config_t* config, const char* path) {
    auto* fx=load(config,path); Notes notes; process(fx,notes);
    midi(fx,notes,0x9f,74); const Notes rooted=notes;
    command(fx,notes,30); const Notes reduced=notes;
    midi(fx,notes,0x8f,74,0);
    midi(fx,notes,0x9f,75); check(notes.size()==4,"Another degree defaults rooted");
    midi(fx,notes,0x8f,75,0);
    midi(fx,notes,0x9f,74); check(notes==reduced,"Degree remembers rootless independently");
    // Physical roots remain owned by hardware; G only filters generated chords.
    const int root=*rooted.begin(); midi(fx,notes,0x90,root);
    command(fx,notes,30); command(fx,notes,30);
    check(notes.count(root)==1,"Rootless toggle never cuts a held hardware root");
    midi(fx,notes,0x80,root,0); check(notes==reduced,"Physical root releases normally");
    midi(fx,notes,0x8f,74,0);
    auto* saved=ysfx_save_state(fx); check(saved!=nullptr,"Save rootless state");
    auto* restored=load(config,path); check(ysfx_load_state(restored,saved),"Load rootless state");
    process(restored,notes); check(notes.empty(),"Restore is silent");
    midi(restored,notes,0x9f,74); check(notes==reduced,"Rootless survives independent instance restore");
    midi(restored,notes,0x8f,74,0);
    midi(restored,notes,0x9f,75); check(notes.size()==4,"Other degree remains rooted after restore");
    midi(restored,notes,0x8f,75,0);
    ysfx_state_free(saved); ysfx_free(restored); ysfx_free(fx);
}

void rootless_legacy(ysfx_config_t* config, const char* path) {
    auto* fx=load(config,path); Notes notes; process(fx,notes);
    midi(fx,notes,0x9f,74); const Notes rooted=notes;
    command(fx,notes,30); midi(fx,notes,0x8f,74,0);
    auto* saved=ysfx_save_state(fx); check(saved && saved->data_size==43*4,"v4 appends seven flags without changing v3 offsets");
    const auto set_float=[](uint8_t* bytes,float value) { std::memcpy(bytes,&value,4); };
    for(int version:{1,2,3}) {
        auto* legacy=ysfx_state_dup(saved);
        if(version==1) {
            std::free(legacy->data); legacy->data_size=253*4;
            legacy->data=static_cast<uint8_t*>(std::calloc(legacy->data_size,1));
            check(legacy->data!=nullptr,"allocate v1 fixture");
            for(int i=0;i<84;++i) {
                set_float(legacy->data+4*(1+3*i),1);
                set_float(legacy->data+4*(3+3*i),60);
            }
        } else legacy->data_size=(version==2 ? 29 : 36)*4;
        set_float(legacy->data,float(version));
        check(ysfx_load_state(fx,saved),"reload rootless before each legacy load"); process(fx,notes);
        check(ysfx_load_state(fx,legacy),"load legacy into previously rootless instance"); process(fx,notes);
        for(int d=0;d<7;++d) check(ysfx_read_vmem_single(fx,3200+d)==0,"legacy state clears every rootless flag");
        midi(fx,notes,0x9f,74); check(notes==rooted,"legacy pitches remain rooted");
        midi(fx,notes,0x8f,74,0); ysfx_state_free(legacy);
    }
    for(float invalid:{-1.f,2.f,0.5f,std::numeric_limits<float>::quiet_NaN()}) {
        auto* malformed=ysfx_state_dup(saved); set_float(malformed->data+36*4,invalid);
        check(ysfx_load_state(fx,malformed),"load malformed flag state"); process(fx,notes);
        check(ysfx_read_vmem_single(fx,3200)==0,"invalid rootless values default rooted");
        ysfx_state_free(malformed);
    }
    auto* truncated=ysfx_state_dup(saved); truncated->data_size=36*4;
    check(ysfx_load_state(fx,saved),"prime rootless for truncation test"); process(fx,notes);
    check(ysfx_load_state(fx,truncated),"truncated appended flags are safe"); process(fx,notes);
    check(ysfx_read_vmem_single(fx,3200)==0,"missing appended flags default rooted");
    ysfx_state_free(truncated); ysfx_state_free(saved); ysfx_free(fx);
}

int main(int argc,char** argv) {
    if (argc!=2) return 2;
    try {
        auto* config=ysfx_config_new();
        ysfx_set_log_reporter(config,[](intptr_t,ysfx_log_level,const char* s){std::fprintf(stderr,"%s\n",s);});
        auto* fx=load(config,argv[1]); Notes notes; process(fx,notes);
        current_chord_reset(config,argv[1]);
        rootless_matrix(config,argv[1]); rootless_navigation(config,argv[1]); rootless_memory(config,argv[1]); rootless_legacy(config,argv[1]);
        matrix(fx,notes); persistence(config,argv[1],fx,notes); mixed(fx,notes);
        upper_position_persistence(config,argv[1]);
        automatic_position_recall(config,argv[1]);
        display_only_notes(config,argv[1]);
        open_position_persistence(config,argv[1]); expanded_voice_ownership(config,argv[1]);
        ysfx_free(fx); ysfx_config_free(config);
        std::puts("252 chords: held-mode switches, user anchors, MIDI ownership, open-position persistence: PASS");
        return 0;
    } catch (const std::exception& e) { std::fprintf(stderr,"FAIL: %s\n",e.what()); return 1; }
}
