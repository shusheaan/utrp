#pragma once
#include "game_control.h"
#include <juce_gui_basics/juce_gui_basics.h>
#include <deque>
#include <vector>

enum class GameStepState { Upcoming, Current, Complete, Missed };
struct GameTrailStep { GameTarget target; bool success; };
struct GameViewStep { GameTarget target; GameStepState state; };
using GameRows = std::array<std::vector<GameViewStep>,3>;

struct GameCapsuleStyle { int keyWidth{57}, chordWidth{115}; float fontHeight{10}; };
juce::Rectangle<int> gamePanelBounds(juce::Rectangle<int> slot, int editorHeight, int editorWidth);
juce::String gameAwardText(const GameStatus&, int instrument, bool replaying);
GameCapsuleStyle gameCapsuleStyle(int leftWidth,int panelWidth,float fontHeight);

GameRows gamePracticeRows(const GameTarget&, const std::deque<GameTarget>&,
    const std::deque<GameTrailStep>&, bool replaying, int winner);
int gamePracticeHeight(const GameRows&,const GameCapsuleStyle&,int availableHeight=0);
void paintGamePractice(juce::Graphics&, juce::Rectangle<int>, const GameTarget&,
    const std::deque<GameTarget>&, const std::deque<GameTrailStep>&,
    const GameStatus&, bool replaying, const GameCapsuleStyle&, int scroll=0);
