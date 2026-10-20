#pragma once
#include "recorder.h"
#include "style.h"
#include <juce_gui_basics/juce_gui_basics.h>

class BeatWaveform final : public juce::Component {
public:
    explicit BeatWaveform(BeatRecorder& value) : recorder(value) {}
    void setAudio(const std::vector<float>& audio) {
        saved.fill(0);
        for (std::size_t i=0;i<audio.size();++i) {
            const auto bin=std::min(saved.size()-1,i*saved.size()/audio.size());
            saved[bin]=std::max(saved[bin],std::abs(audio[i]));
        }
        hasAudio=!audio.empty(); repaint();
    }
    void paint(juce::Graphics& g) override {
        const auto bounds=getLocalBounds().toFloat();
        g.setColour(juce::Colour(beatstyle::wave_background)); g.fillRoundedRectangle(bounds,9);
        const float width=bounds.getWidth()-24, left=12, centre=bounds.getHeight()*0.57f;
        g.setColour(juce::Colour(beatstyle::wave_grid));
        for (int beat=0;beat<=16;++beat) {
            const float x=left+width*beat/16;
            g.drawVerticalLine(static_cast<int>(x),22,bounds.getBottom()-8);
            if (beat%4==0 && beat<16) {
                g.setColour(juce::Colours::white); g.setFont(12);
                g.drawText("Bar "+juce::String(beat/4+1),static_cast<int>(x+3),3,70,18,juce::Justification::left);
                g.setColour(juce::Colour(beatstyle::wave_grid));
            }
        }
        const bool live=recorder.active();
        g.setColour(juce::Colour(beatstyle::wave_signal));
        for (std::size_t i=0;i<saved.size();++i) {
            const float peak=live ? recorder.peaks[i].load() : saved[i];
            const float height=std::min(1.0f,peak)*(bounds.getHeight()-35)*0.5f;
            const float x=left+width*static_cast<float>(i)/saved.size();
            g.drawLine(x,centre-height,x,centre+height,2);
        }
        if (live) {
            g.setColour(juce::Colours::white);
            const float x=left+width*recorder.progress.load(); g.drawLine(x,22,x,bounds.getBottom()-8,2);
            if (recorder.state.load()==BeatRecorder::State::countIn) {
                g.setFont(30); g.drawText(juce::String(recorder.countdown.load()),getLocalBounds(),juce::Justification::centred);
            }
        } else if (!hasAudio) {
            g.setColour(juce::Colours::white); g.setFont(14);
            g.drawText("Record 4 bars or import WAV",getLocalBounds(),juce::Justification::centred);
        }
    }
private:
    BeatRecorder& recorder;
    std::array<float,BeatRecorder::bins> saved{};
    bool hasAudio=false;
};
