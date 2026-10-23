#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

// A numeric field: no +/- buttons, one wheel tick per configured interval.
class GameWheelValue final : public juce::Slider {
public:
    GameWheelValue()
    {
        setSliderStyle(juce::Slider::LinearBar);
        setTextBoxStyle(juce::Slider::TextBoxLeft,true,60,24);
        setWantsKeyboardFocus(false);
        setColour(juce::Slider::trackColourId,juce::Colours::transparentBlack);
        setColour(juce::Slider::thumbColourId,juce::Colours::transparentBlack);
    }
    void mouseWheelMove(const juce::MouseEvent& event,const juce::MouseWheelDetails& wheel) override
    {
        if(!isEnabled() || event.mods.isAnyMouseButtonDown() || wheel.deltaY==0 || wheel.isInertial) return;
        const float direction=wheel.deltaY*(wheel.isReversed ? -1.0f : 1.0f);
        setValue(getValue()+(direction>0 ? getInterval() : -getInterval()),juce::sendNotificationSync);
    }
};
