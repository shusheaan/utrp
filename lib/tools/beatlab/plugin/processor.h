#pragma once
#include <juce_audio_utils/juce_audio_utils.h>
#include "recorder.h"

class BeatProcessor final : public juce::AudioProcessor {
public:
    BeatProcessor();
    const juce::String getName() const override { return "Beat Lab"; }
    void prepareToPlay(double rate, int) override { sampleRate.store(rate); }
    void releaseResources() override { auditioning.store(false); recorder.interrupt(); }
    bool isBusesLayoutSupported(const BusesLayout&) const override;
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; } // Offline .mid export in this prototype.
    double getTailLengthSeconds() const override { return 0; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock&) override;
    void setStateInformation(const void*, int) override;
    BeatRecorder recorder;
    std::atomic<std::uint64_t> recordingRevision{0};
    std::atomic<double> hostBpm{0};
    std::atomic<bool> hostFourFour{true};
    std::atomic<double> manualBpm{120};
    std::atomic<double> analysisGateDb{-36};
    std::atomic<unsigned> audioHeartbeat{0};
    struct Source { std::vector<float> audio; double rate=48000, bpm=120; bool matched=false; };
    Source getSource() const;
    bool collectRecording();
    void setSource(const std::vector<float>&, double rate, double bpm, bool matched);
    std::atomic<double> sampleRate{48000};
    std::atomic<int> inputChannel{0};
    std::atomic<bool> auditioning{false};
    bool audition(const std::vector<float>& audio, double sourceRate, std::size_t start);
    juce::var getPattern() const;
    void setPattern(const juce::var&);
private:
    mutable juce::CriticalSection stateLock;
    juce::String patternJson;
    Source source;
    std::uint64_t collectedTake=0;
    std::array<float, 192000> auditionSamples{};
    std::size_t auditionSize = 0, auditionPosition = 0;
};
