#include "control.h"

void ChordLabControl::key(int note, bool down)
{
    if (note < 0 || note > 127) { release(); return; }
    const auto position = write.load(std::memory_order_relaxed);
    const auto next = (position + 1) % queue.size();
    if (next == read.load(std::memory_order_acquire)) { release(); return; }
    queue[position] = {{{uint8_t(down ? 0x9f : 0x8f), uint8_t(note), uint8_t(down ? 100 : 0)}}};
    write.store(next, std::memory_order_release);
}

void ChordLabControl::process(ysfx_t* fx)
{
    if (panic.exchange(false, std::memory_order_acq_rel)) {
        read.store(write.load(std::memory_order_acquire), std::memory_order_release);
        const uint8_t data[]{0xbf, 123, 0};
        const ysfx_midi_event_t event{0, 0, 3, data};
        if (!ysfx_send_midi(fx, &event)) panic.store(true, std::memory_order_release);
        return;
    }
    auto position = read.load(std::memory_order_relaxed);
    const auto end = write.load(std::memory_order_acquire);
    while (position != end) {
        const ysfx_midi_event_t event{0, 0, 3, queue[position].bytes.data()};
        if (!ysfx_send_midi(fx, &event)) panic.store(true, std::memory_order_release);
        position = (position + 1) % queue.size();
    }
    read.store(position, std::memory_order_release);
}
