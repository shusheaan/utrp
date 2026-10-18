#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace guitar {
struct Settings {
    bool enabled;
    double gateDb, confidence, stabilityMs, releaseMs;
};
struct Observation {
    int note = -1;
    double frequency = 0, confidence = 0, rms = 0;
};
struct Update {
    bool ready = false;
    int note = -1;
    bool retrigger = false;
    Observation observation{};
};
struct Lowpass {
    double b0=0, b1=0, b2=0, a1=0, a2=0, z1=0, z2=0;
    void prepare(double rate, double cutoff, double q);
    double push(double input);
};
// No heap allocation, I/O or host dependency in the audio path.
class Detector final {
public:
    bool prepare(double rate);
    void reset();
    Update push(double sample, const Settings& settings);
    int currentNote() const { return current; }
    double hopMilliseconds() const { return 1000.0 * hop / analysisRate; }
private:
    static constexpr std::size_t capacity = 2048;
    std::array<double, capacity> ring{}, frame{}, difference{}, window{};
    Lowpass filter1{}, filter2{};
    double sampleRate=48000, analysisRate=12000;
    unsigned decimation=4, decimateCount=0, length=768, hop=96;
    unsigned write=0, filled=0, sinceHop=0, stable=0, missing=0;
    int candidate=-1, current=-1;
    double previousRms=0, lastOnMs=-10000, elapsedMs=0;
    bool pendingAttack=false;
    double spectralPower(double hz) const;
    Observation supportedPitch(Observation result) const;
    Observation analyze(const Settings& settings);
    Update update(const Observation& observation, const Settings& settings);
};
}
