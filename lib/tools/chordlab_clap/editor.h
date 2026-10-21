#pragma once
#include <juce_audio_processors/juce_audio_processors.h>
#include "components/graphics_view.h"
#include "keyboard.h"
#include "physical_keys.h"
#include "state_button.h"
class YsfxProcessor;

class YsfxEditor final : public juce::AudioProcessorEditor,
                        private juce::KeyListener, private juce::Timer {
public:
    explicit YsfxEditor(YsfxProcessor&);
    ~YsfxEditor() override;
    void resized() override;
    void paint(juce::Graphics&) override;
private:
    bool keyPressed(const juce::KeyPress&, juce::Component*) override;
    bool keyStateChanged(bool, juce::Component*) override;
    void timerCallback() override;
    void visibilityChanged() override;
    void mouseDown(const juce::MouseEvent&) override;
    void mouseUp(const juce::MouseEvent&) override;
    bool focusInput();
    void releaseKeys();
    void dispatchNativeKeys();
    bool hasInputFocus() const;
    void updateLabel();
    void showAppearanceMenu();
    YsfxProcessor& processor;
    YsfxGraphicsView view;
    StateButton sustain{"S"}, capture{"A"};
    juce::Label errorLabel;
    juce::TooltipWindow tooltips{this, 700};
    KeyboardState keyboard;
    PhysicalKeys physical;
    bool enabled{true}, hadFocus{false}, ignoreCaptureClick{false}, captureWasActive{false};
    bool appearanceMenuOpen{false};
    bool initialFocusPending{true};
    ysfx_t* displayedEffect{nullptr};
};
