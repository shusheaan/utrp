#include "game_control.h"
#include <cstdio>
#include <cmath>

bool GameControl::send(const GamePacket& packet)
{
    if (!std::isfinite(packet.limit) || !std::isfinite(packet.demo) || packet.action < 1 || packet.action > 4 || packet.limit < 1 || packet.limit > 120
        || packet.demo < 1 || packet.demo > 10) return false;
    if (packet.action == 3) {
        const auto& t = packet.target;
        if (t.count < 3 || t.count > 5 || t.signature < 0 || t.signature > 11
            || t.tonic < 0 || t.tonic > 11 || t.minor < 0 || t.minor > 1
            || t.root < 0 || t.root > 11 || t.rootLetter < 0 || t.rootLetter > 6
            || t.quality < 0 || t.quality > 12 || t.degree < -1 || t.degree > 6) return false;
        for (unsigned i=0; i<7; ++i)
            if (t.scale[i]<0 || t.scale[i]>11 || t.scaleLetters[i]<0 || t.scaleLetters[i]>6) return false;
        for (unsigned i=0; i<t.count; ++i)
            if (t.notes[i]<40 || t.notes[i]>81 || (i && t.notes[i]<=t.notes[i-1])
                || t.roles[i]<0 || t.roles[i]>4 || t.letters[i]<0 || t.letters[i]>6) return false;
    }
    const auto w=cw.load(std::memory_order_relaxed); const auto next=(w+1)%commands.size();
    if (next==cr.load(std::memory_order_acquire)) return false;
    commands[w]=packet; cw.store(next,std::memory_order_release); return true;
}
bool GameControl::read(GameStatus& status)
{
    auto r=sr.load(std::memory_order_relaxed);
    const auto w=sw.load(std::memory_order_acquire);
    if (r==w) return false;
    while(r!=w) { status=statuses[r]; r=(r+1)%statuses.size(); }
    sr.store(r,std::memory_order_release); return true;
}
void GameControl::bind(ysfx_t* fx)
{
    bound=fx;
    const char* scalars[]{"game_action","game_id","game_count","game_signature","game_tonic","game_minor",
        "game_root","game_root_letter","game_quality","game_degree","game_limit","game_demo_seconds"};
    unsigned index=0;
    for (auto* name:scalars) vars[index++]=ysfx_find_var(fx,name);
    for (auto* prefix:{"game_n","game_r","game_l","game_s","game_sl"}) {
        const int count=index>=27 ? 7 : 5;
        for (int i=0;i<count;++i) {
            char name[32]; std::snprintf(name,sizeof name,"%s%d",prefix,i);
            vars[index++]=ysfx_find_var(fx,name);
        }
    }
    const char* names[]{"game_phase","game_id","game_count","game_piano_hits","game_guitar_hits",
        "game_piano_score","game_guitar_score","game_timeouts","game_remaining"};
    for (unsigned i=0;i<telemetry.size();++i) telemetry[i]=ysfx_find_var(fx,names[i]);
}
void GameControl::process(ysfx_t* fx)
{
    if (bound!=fx) bind(fx);
    if (!vars[0]) return;
    if (stop.exchange(false,std::memory_order_acq_rel)) {
        cr.store(stopBoundary.load(std::memory_order_acquire),std::memory_order_release);
        *vars[0]=2; return;
    }
    auto r=cr.load(std::memory_order_relaxed);
    if (r==cw.load(std::memory_order_acquire)) return;
    const auto& p=commands[r];
    if (p.action==3) {
        const auto& t=p.target;
        const double scalars[]{double(t.id),double(t.count),double(t.signature),double(t.tonic),double(t.minor),
            double(t.root),double(t.rootLetter),double(t.quality),double(t.degree),p.limit,p.demo};
        for(unsigned i=0;i<11;++i) if(vars[i+1]) *vars[i+1]=scalars[i];
        unsigned index=12;
        for(auto* values:{t.notes,t.roles,t.letters,t.scale,t.scaleLetters}) {
            const int count=index>=27 ? 7 : 5;
            for(int i=0;i<count;++i) { if(vars[index]) *vars[index]=values[i]; ++index; }
        }
    }
    *vars[0]=p.action;
    cr.store((r+1)%commands.size(),std::memory_order_release);
}
void GameControl::publish(ysfx_t* fx)
{
    if (bound!=fx) return;
    const auto w=sw.load(std::memory_order_relaxed); const auto next=(w+1)%statuses.size();
    if (next==sr.load(std::memory_order_acquire)) return;
    const auto get=[this](unsigned i){return telemetry[i] ? *telemetry[i] : 0.0;};
    statuses[w]={int(get(0)),int(get(1)),int(get(2)),int(get(3)),int(get(4)),int(get(5)),int(get(6)),int(get(7)),get(8)};
    sw.store(next,std::memory_order_release);
}
