#pragma once
#include "ysfx.h"
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>

// One producer (editor/message thread), one consumer (audio thread).
class ChordLabControl final {
public:
    void key(int note, bool down);
    void release() { panic.store(true, std::memory_order_release); }
    void process(ysfx_t* fx);
private:
    struct Packet { std::array<uint8_t, 3> bytes; };
    std::array<Packet, 512> queue{};
    std::atomic<std::size_t> read{0}, write{0};
    std::atomic<bool> panic{false};
};
