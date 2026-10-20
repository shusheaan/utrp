#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <vector>

// Host audio I/O only. Analysis/classification remains in the Rust engine.
// Single audio-thread producer; UI requests commands and reads completed takes.
class BeatRecorder final {
public:
    enum class State { idle, countIn, recording, ready };
    enum class Error { none, invalidClock, clockChanged, interrupted };
    static constexpr std::size_t bins = 256;
    BeatRecorder();
    void start(bool loop) noexcept;
    void stop() noexcept;
    void interrupt() noexcept; // Host has suspended processing.
    void beginBlock(double bpm, double rate, bool fourFour) noexcept;
    float process(float input) noexcept; // Returns click only, never microphone audio.
    bool copyCompleted(std::vector<float>&, double& rate, double& bpm, std::uint64_t& seen);
    bool active() const noexcept;
    bool pending() const noexcept { return command.load()!=Command::none; }
    std::atomic<State> state{State::idle};
    std::atomic<Error> error{Error::none};
    std::atomic<bool> clickDuringTake{true};
    std::atomic<float> progress{0}, inputPeak{0};
    std::atomic<int> countdown{0}, cycles{0};
    std::array<std::atomic<float>, bins> peaks{};
private:
    enum class Command { none, once, loop, stop };
    static constexpr std::size_t capacity = 192000 * 24; // 4 bars, 40 BPM, max supported rate.
    std::array<std::vector<float>,2> buffers;
    std::atomic<Command> command{Command::none};
    std::atomic<bool> reading{false};
    std::uint64_t generation = 0;
    bool looping = false, haveCompleted = false;
    int writing = 0, completed = 1;
    std::size_t cursor = 0, countCursor = 0, countLength = 0, length = 0, completedLength = 0;
    double clockBpm = 120, clockRate = 48000, completedBpm = 120, completedRate = 48000;
    void begin(double bpm, double rate, bool loop) noexcept;
    void halt(Error) noexcept;
    void clearPeaks() noexcept;
    float click(std::size_t position, bool enabled) const noexcept;
};
