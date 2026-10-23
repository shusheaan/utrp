#pragma once
#include "game_controls.h"

// A numeric field: no +/- buttons, one wheel tick per configured interval.
class GameWheelValue final : public juce::Slider {
public:
    GameWheelValue()
    {
        setSliderStyle(juce::Slider::LinearBar);
        setTextBoxStyle(juce::Slider::NoTextBox,true,0,0);
        setWantsKeyboardFocus(false);
        setColour(juce::Slider::trackColourId,juce::Colours::transparentBlack);
        setColour(juce::Slider::thumbColourId,juce::Colours::transparentBlack);
    }
    float fontHeight{float(chordlabStyle::choice_font_size)};
    void paint(juce::Graphics& g) override
    {
        gameControls::pill(g,getLocalBounds(),isMouseOverOrDragging(),isEnabled());
        g.setFont(gameControls::font(fontHeight));
        g.setColour(juce::Colour(chordlabStyle::game_text));
        g.drawFittedText(getName()+" "+getTextFromValue(getValue()),getLocalBounds().reduced(5,0),
            juce::Justification::centred,1);
    }
    void mouseWheelMove(const juce::MouseEvent& event,const juce::MouseWheelDetails& wheel) override
    {
        if(!isEnabled() || event.mods.isAnyMouseButtonDown() || wheel.deltaY==0 || wheel.isInertial) return;
        const float direction=wheel.deltaY*(wheel.isReversed ? -1.0f : 1.0f);
        setValue(getValue()+(direction>0 ? getInterval() : -getInterval()),juce::sendNotificationSync);
    }
};
