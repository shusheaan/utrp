#pragma once
#include <juce_gui_extra/juce_gui_extra.h>

class BeatGrid final : public juce::Component {
public:
    juce::var pattern;
    int visibleBars = 4;
    double startBeat = 0.0;
    int divisions = 4; // Display/edit grid, independent of output quantization.
    std::function<void()> changed;
    void paint(juce::Graphics&) override;
    void mouseDown(const juce::MouseEvent&) override;
    double displayBeat(const juce::var&) const;
    double beatAtX(float x) const;
    float xForBeat(double beat) const;
    double insertionBeat(float x) const;
    int hitEvent(int lane, float x) const;
private:
    static constexpr int left = 105, top = 48, rowHeight = 50;
    void paintRuler(juce::Graphics&) const;
    void paintEvents(juce::Graphics&) const;
};
