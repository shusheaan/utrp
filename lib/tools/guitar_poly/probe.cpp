// Offline probe of pinned upstream PDCT. No audio-device, GUI, or MIDI I/O.
#include "cPdct.h"
#include <array>
#include <iostream>

int main() {
    cPdct detector;
    detector.init();
    detector.reset();
    std::array<double,48> block{};
    std::array<int,NUM_OF_RESONATOR> previous{};
    while (std::cin.read(reinterpret_cast<char*>(block.data()),sizeof(block))) {
        detector.process(block.data(),int(block.size()),1);
        std::array<int,NUM_OF_RESONATOR> current{};
        for (int i=0;i<NUM_OF_RESONATOR;++i) current[i]=detector.getNoteMapState(i);
        if (current==previous) continue;
        std::cout<<detector.getCurrentTime()*1000;
        for (int i=0;i<NUM_OF_RESONATOR;++i)
            if (current[i]) std::cout<<','<<i+FIRST_NOTE_NUMBER;
        std::cout<<'\n';
        previous=current;
    }
    return std::cin.eof() && std::cin.gcount()==0 ? 0 : 1;
}
