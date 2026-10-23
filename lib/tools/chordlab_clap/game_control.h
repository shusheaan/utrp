#pragma once
#include "ysfx.h"
#include <array>
#include <atomic>
#include <cstdint>

// Must match the Rust repr(C) Target. No allocator or Rust call on the audio thread.
struct GameTarget {
    uint32_t id{}, count{};
    int32_t notes[5]{}, roles[5]{}, letters[5]{}, scale[7]{}, scaleLetters[7]{};
    int32_t tonic{}, signature{}, minor{}, root{}, rootLetter{}, quality{}, degree{}, movement{};
    uint32_t phrase{};
    char label[96]{}, keyLabel[64]{}, reason[256]{};
    uint32_t visit{}, backbone{};
    char action[48]{}, route[128]{};
    uint32_t group{}, kind{};
    int32_t paletteRole{};
    char capsule[64]{}, bass[32]{};
};
static_assert(sizeof(GameTarget) == 868, "Rust/C++ game target ABI drift");
extern "C" {
    void* chordlab_game_new(uint64_t seed);
    void chordlab_game_free(void*);
    bool chordlab_game_next(void*, GameTarget*);
    bool chordlab_game_configure(void*, double probability, int32_t direction, bool approaches);
    bool chordlab_game_complete(void*, uint32_t id, bool success);
}
struct GamePacket { int action{}; GameTarget target{}; double limit{10}, demo{2}; };
struct GameStatus {
    int phase{}, id{-1}, count{}, pianoHits{}, guitarHits{}, pianoScore{}, guitarScore{}, timeouts{};
    double remaining{};
    int winner{}, award{};
};

// Separate SPSC queues: UI -> audio commands; audio -> UI telemetry.
// Full command queue fails explicitly. Closing uses an independent emergency latch.
class GameControl final {
public:
    bool send(const GamePacket&);
    void off() {
        stopBoundary.store(cw.load(std::memory_order_acquire), std::memory_order_release);
        stop.store(true, std::memory_order_release);
    }
    void reset() { off(); resetSerial.fetch_add(1, std::memory_order_release); }
    uint32_t resets() const { return resetSerial.load(std::memory_order_acquire); }
    bool read(GameStatus&);
    void process(ysfx_t*);
    void publish(ysfx_t*);
private:
    void bind(ysfx_t*);
    std::array<GamePacket, 8> commands{};
    std::array<GameStatus, 128> statuses{};
    std::atomic<unsigned> cw{0}, cr{0}, sw{0}, sr{0};
    std::atomic<bool> stop{false};
    std::atomic<unsigned> stopBoundary{0};
    std::atomic<uint32_t> resetSerial{0};
    ysfx_t* bound{};
    // 12 scalar fields + five notes/roles/letters + seven scale PCs/letters.
    std::array<ysfx_real*, 41> vars{};
    std::array<ysfx_real*, 11> telemetry{};
};
