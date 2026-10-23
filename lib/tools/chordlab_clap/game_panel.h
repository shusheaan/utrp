#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include "game_view.h"
#include "game_wheel_value.h"
#include <deque>

class GamePanel final : public juce::Component {
public:
    explicit GamePanel(GameControl&);
    ~GamePanel() override;
    bool activate();
    void deactivate();
    void tick();
    double progress() const;
    void setCapsuleStyle(GameCapsuleStyle style) { capsuleStyle=style; }
    void resized() override;
    void paint(juce::Graphics&) override;
    void mouseWheelMove(const juce::MouseEvent&,const juce::MouseWheelDetails&) override;
    std::function<void()> returnFocus;
private:
    void start();
    bool plan();
    bool present();
    GameControl& control;
    void* planner{};
    std::deque<GameTarget> preview;
    std::deque<GameTrailStep> trail;
    GameTarget current{};
    GameStatus status{};
    juce::TextButton startButton{"Start"}, pauseButton{"Pause"};
    GameWheelValue limit, demo, modulation;
    GameCapsuleStyle capsuleStyle;
    int practiceScroll{};
    double answerDuration{10}, demoDuration{2};
    juce::ComboBox direction;
    juce::ToggleButton approaches{"Approach chords"};
    unsigned coverage{}, presented{};
    bool active{}, running{}, pending{}, replaying{};
    uint64_t seed{};
    uint32_t targetSerial{};
    juce::String error;
};
