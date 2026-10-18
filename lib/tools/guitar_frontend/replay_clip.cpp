// Offline diagnostic, not part of the CLAP: native float64 mono, 48 kHz stdin.
#include "engine.h"
#include "defaults.h"
#include <iomanip>
#include <iostream>

int main() {
    guitar::Detector detector;
    if (!detector.prepare(48000)) return 2;
    const guitar::Settings settings{true,guitar::defaults::gate_db,guitar::defaults::confidence,
        guitar::defaults::stability_ms,guitar::defaults::release_ms};
    double sample=0;
    unsigned long long frame=0;
    std::cout<<"seconds,current,observed,frequency,confidence,rms\n";
    while (std::cin.read(reinterpret_cast<char*>(&sample),sizeof(sample))) {
        const auto update=detector.push(sample,settings);
        ++frame;
        if (!update.ready) continue;
        const auto& observation=update.observation;
        std::cout<<std::setprecision(10)<<frame/48000.0<<','<<update.note<<','<<observation.note<<','
            <<observation.frequency<<','<<observation.confidence<<','<<observation.rms<<'\n';
    }
    return std::cin.eof() && std::cin.gcount()==0 ? 0 : 1;
}
