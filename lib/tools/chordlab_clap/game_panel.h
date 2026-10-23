#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include "game_control.h"
#include <deque>

class GamePanel final : public juce::Component {
public:
    explicit GamePanel(GameControl&);
    ~GamePanel() override;
    bool activate();
    void deactivate();
    void tick();
    void resized() override;
    void paint(juce::Graphics&) override;
    std::function<void()> returnFocus;
private:
    void start();
    bool plan();
    bool present();
    GameControl& control;
    void* planner{};
    std::deque<GameTarget> preview;
    GameTarget current{};
    GameStatus status{};
    juce::TextButton startButton{"Start"}, pauseButton{"Pause"};
    juce::Slider limit, demo;
    bool active{}, running{}, pending{};
    uint64_t seed{};
    uint32_t targetSerial{};
    juce::String error;
};
