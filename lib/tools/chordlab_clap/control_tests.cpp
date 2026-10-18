#include "control.h"
#include <cstdlib>
#include <iostream>
#include <vector>
struct ysfx_s { std::vector<std::array<uint8_t,3>> events; bool accept{true}; };
extern "C" bool ysfx_send_midi(ysfx_t* fx, const ysfx_midi_event_t* e)
{
    if (!fx->accept) return false;
    if (e->size != 3 || e->bus != 0 || e->offset != 0) std::abort();
    fx->events.push_back({e->data[0],e->data[1],e->data[2]}); return true;
}
void check(bool passed) { if (!passed) { std::cerr << "Control queue invariant failed\n"; std::exit(1); } }
int main()
{
    ChordLabControl queue; ysfx_s fx;
    queue.key(74,true);queue.key(74,false);queue.process(&fx);
    check(fx.events.size()==2 && fx.events[0][0]==0x9f && fx.events[1][0]==0x8f);
    check(fx.events[0][1]==74 && fx.events[0][2]==100 && fx.events[1][2]==0);
    fx.events.clear();queue.process(&fx);check(fx.events.empty());
    for (int i=0;i<600;++i) queue.key(74,true);
    queue.process(&fx);
    check(fx.events.size()==1 && fx.events[0]==std::array<uint8_t,3>{0xbf,123,0});
    fx.events.clear();queue.key(74,true);queue.process(&fx);check(fx.events.size()==1);
    fx.events.clear();queue.release();queue.key(74,true);queue.process(&fx);
    check(fx.events.size()==1 && fx.events[0][0]==0xbf);
    fx.events.clear();fx.accept=false;queue.key(74,true);queue.process(&fx);check(fx.events.empty());
    fx.accept=true;queue.process(&fx);check(fx.events.size()==1 && fx.events[0][0]==0xbf);
    fx.events.clear();queue.key(128,true);queue.process(&fx);check(fx.events.size()==1 && fx.events[0][0]==0xbf);
    fx.events.clear();queue.key(82,true);queue.key(82,false);queue.process(&fx);
    check(fx.events.size()==2 && fx.events[0]==std::array<uint8_t,3>{0x9f,82,100}
          && fx.events[1]==std::array<uint8_t,3>{0x8f,82,0});
    fx.events.clear();queue.release();queue.process(&fx);
    check(fx.events.size()==1 && fx.events[0]==std::array<uint8_t,3>{0xbf,123,0});
    std::cout << "11 control queue checks passed\n";
}
