#pragma once
#include "control_style.h"
#include <juce_gui_basics/juce_gui_basics.h>

// Game-local metrics, derived from the same theme as the chord capsules.
namespace gameControls {
inline constexpr int height=chordlabStyle::choice_height-2*chordlabStyle::selection_inset;
inline constexpr int gap=2*chordlabStyle::selection_inset;
inline constexpr int margin=chordlabStyle::choice_height/2;
inline constexpr int settingsHeight=4*height+7*gap;
inline juce::Font font(float size) {
    // Resolve a real platform sans face; absent named faces can yield a null
    // Typeface in JUCE's point-height metrics (DejaVu is not installed here).
    return juce::Font(juce::FontOptions(juce::Font::getDefaultSansSerifFontName(),size,juce::Font::plain)
        .withMetricsKind(juce::TypefaceMetricsKind::legacy).withPointHeight(size));
}
inline void pill(juce::Graphics& g,juce::Rectangle<int> bounds,bool hover,bool enabled) {
    const auto area=bounds.toFloat().reduced(0.5f);
    auto fill=juce::Colour(chordlabStyle::choice_button_selected);
    g.setColour((hover && enabled ? fill.brighter(0.12f) : fill).withMultipliedAlpha(enabled ? 1.0f : 0.5f));
    g.fillRoundedRectangle(area,area.getHeight()/2);
    g.setColour(juce::Colour(chordlabStyle::game_muted).withAlpha(enabled ? 0.5f : 0.2f));
    g.drawRoundedRectangle(area,area.getHeight()/2,0.7f);
}
}

// Never installed globally: normal-mode controls keep their existing appearance.
class GameCapsuleLookAndFeel final : public juce::LookAndFeel_V4 {
public:
    GameCapsuleLookAndFeel() {
        setColour(juce::PopupMenu::backgroundColourId,juce::Colours::transparentBlack);
    }
    float fontHeight{float(chordlabStyle::choice_font_size)};
    juce::Font getTextButtonFont(juce::TextButton&,int) override { return gameControls::font(fontHeight); }
    juce::Font getComboBoxFont(juce::ComboBox&) override { return gameControls::font(fontHeight); }
    juce::Font getPopupMenuFont() override { return gameControls::font(fontHeight); }
    juce::Component* getParentComponentForMenuOptions(const juce::PopupMenu::Options& options) override {
        // Keep the menu inside the game panel, without a separate X11 window
        // whose opaque backing can turn the rounded corners white.
        if(auto* target=options.getTargetComponent()) return target->getParentComponent();
        return options.getParentComponent();
    }
    void preparePopupMenuWindow(juce::Component& menu) override { menu.setOpaque(false); }
    void drawPopupMenuBackground(juce::Graphics& g,int width,int h) override {
        g.setColour(juce::Colour(chordlabStyle::game_background));
        g.fillRoundedRectangle(0,0,float(width),float(h),float(gameControls::height)/2);
    }
    void getIdealPopupMenuItemSize(const juce::String& text,bool,int,int& w,int& h) override {
        juce::GlyphArrangement glyphs;glyphs.addLineOfText(getPopupMenuFont(),text,0,0);
        w=int(std::ceil(glyphs.getBoundingBox(0,-1,true).getWidth()))+36;
        h=gameControls::height+gameControls::gap;
    }
    void drawPopupMenuItem(juce::Graphics& g,const juce::Rectangle<int>& area,bool,bool active,
                          bool hover,bool ticked,bool,const juce::String& text,const juce::String&,
                          const juce::Drawable*,const juce::Colour*) override {
        const auto bounds=area.reduced(3,gameControls::gap/2);
        gameControls::pill(g,bounds,hover,active);
        g.setColour(juce::Colour(chordlabStyle::game_text));g.setFont(getPopupMenuFont());
        g.drawFittedText(text,bounds.reduced(18,0),juce::Justification::centred,1);
        if(ticked) {
            g.setColour(juce::Colour(chordlabStyle::game_reason));
            g.fillEllipse(float(bounds.getX()+8),float(bounds.getCentreY()-3),6,6);
        }
    }
    void drawButtonBackground(juce::Graphics& g,juce::Button& b,const juce::Colour&,bool hover,bool down) override {
        gameControls::pill(g,b.getLocalBounds(),hover || down,b.isEnabled());
    }
    void drawToggleButton(juce::Graphics& g,juce::ToggleButton& b,bool hover,bool down) override {
        gameControls::pill(g,b.getLocalBounds(),hover || down,b.isEnabled());
        g.setFont(gameControls::font(fontHeight));
        g.setColour(juce::Colour(chordlabStyle::game_text));
        g.drawFittedText(b.getButtonText()+(b.getToggleState() ? "  On" : "  Off"),
            b.getLocalBounds().reduced(12,0),juce::Justification::centred,1);
        g.setColour(juce::Colour(b.getToggleState() ? chordlabStyle::on : chordlabStyle::off));
        g.fillEllipse(10.0f,float(b.getHeight())/2-3,6.0f,6.0f);
    }
    void drawComboBox(juce::Graphics& g,int width,int h,bool down,int,int,int,int,juce::ComboBox& box) override {
        gameControls::pill(g,{0,0,width,h},down || box.isMouseOver(),box.isEnabled());
        g.setColour(juce::Colour(chordlabStyle::game_text));
        juce::Path arrow; const float x=float(width)-16, y=float(h)/2;
        arrow.startNewSubPath(x-3,y-1);arrow.lineTo(x,y+2);arrow.lineTo(x+3,y-1);
        g.strokePath(arrow,juce::PathStrokeType(1));
    }
    void positionComboBoxText(juce::ComboBox& box,juce::Label& label) override {
        label.setBounds(12,0,box.getWidth()-36,box.getHeight());
        label.setFont(getComboBoxFont(box));label.setJustificationType(juce::Justification::centred);
    }
};
