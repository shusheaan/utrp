#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include "control_style.h"

// Circular state indicators inset like the selected pills in the same rail.
class StateButton final : public juce::TextButton {
public:
    using juce::TextButton::TextButton;

    void paintButton(juce::Graphics& graphics, bool highlighted, bool down) override
    {
        auto colour = findColour(getToggleState() ? buttonOnColourId : buttonColourId);
        if (down) colour = colour.darker(0.12f);
        else if (highlighted) colour = colour.brighter(0.04f);
        graphics.setColour(colour);
        const auto bounds = getLocalBounds();
        // Same radius as a selected JSFX capsule: (height-2*inset-1)/2.
        // Keep the existing click target; only the visible circle is smaller.
        graphics.fillEllipse(bounds.toFloat().reduced(float(chordlabStyle::selection_inset) + 0.5f));
        graphics.setColour(juce::Colour(chordlabStyle::foreground));
        graphics.setFont(juce::Font(juce::FontOptions("DejaVu Sans",
            float(chordlabStyle::font_size), juce::Font::plain)));
        graphics.drawText(getButtonText(), bounds, juce::Justification::centred, false);
    }
};
