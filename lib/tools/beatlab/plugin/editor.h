#pragma once
#include "processor.h"
#include "grid.h"
#include "waveform.h"
#include <future>

class BeatLook final : public juce::LookAndFeel_V4 {
public:
    BeatLook();
    void drawButtonBackground(juce::Graphics&, juce::Button&, const juce::Colour&, bool, bool) override;
    void drawComboBox(juce::Graphics&, int, int, bool, int, int, int, int, juce::ComboBox&) override;
};
class BeatEditor final : public juce::AudioProcessorEditor, public juce::FileDragAndDropTarget, private juce::Timer {
public:
    explicit BeatEditor(BeatProcessor&);
    ~BeatEditor() override;
    void paint(juce::Graphics&) override;
    void resized() override;
    bool isInterestedInFileDrag(const juce::StringArray&) override;
    void filesDropped(const juce::StringArray&, int, int) override;
private:
    BeatProcessor& processor;
    BeatLook look;
    BeatGrid grid;
    BeatWaveform waveform;
    juce::TextButton record{"Record"}, stop{"Stop"};
    juce::ToggleButton click{"Click"};
    juce::ComboBox recordMode;
    juce::Label clockStatus;
    std::uint64_t seenRecording=0;
    unsigned lastHeartbeat=0;
    int silentTicks=0;
    bool awaitingCapture=false;
    bool wasRecording=false;
    void configureRecording();
    void updateRecording();
    juce::TextButton import{"Import WAV"}, analyze{"Reanalyze"}, demo{"Example"}, exportMidi{"Export MIDI File"};
    juce::ComboBox quantize, displayGrid, zoom, channel;
    std::array<juce::ComboBox, 4> mappings;
    std::array<juce::TextButton, 4> hear;
    juce::Slider bpm, gate, strength, pan;
    juce::Label title, subtitle, status, bpmLabel, barLabel, gateLabel, gridLabel, strengthLabel, mappingLabel;
    std::unique_ptr<juce::FileChooser> chooser;
    std::vector<float> take;
    double takeRate = 48000, takeBpm = 120;
    int takeBars = 4;
    std::future<juce::var> pending;
    bool busy = false;
    bool sourceMatchesPattern = false;
    void timerCallback() override;
    void setStatus(const juce::String&);
    void loadPattern(const juce::var&);
    void storePattern();
    void startAnalysis();
    void finishAnalysis();
    void importWav();
    void exportFile();
    void loadWav(const juce::File&);
    bool updateTiming();
    void loadDemo();
    void configureGridControls();
    void chooseFile(bool save, const juce::String& name, const juce::String& filter, std::function<void(juce::File)>);
};
