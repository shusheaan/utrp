#pragma once
#include <juce_core/juce_core.h>
#include <juce_graphics/juce_graphics.h>
#include <vector>

// Explicit G transitions only. No polling service or desktop-wide rules.
class GameLayout final {
public:
    void remember();
    void arrange();
    void prepareRestore();
    void restore();
    juce::String error;
    bool noSpace{};
private:
    struct Window { int64_t id{}, pid{}; juce::String title, app; juce::Rectangle<int> rect; bool focused{}, bitwigOwned{}; };
    struct Move { Window original; juce::Rectangle<int> placed; };
    std::vector<Window> windows;
    std::vector<Move> moved;
    Window original;
    juce::Rectangle<int> bounds;
    bool armed{}, restoreOwn{};
    juce::Point<int> ownRestorePoint;
    juce::var request(uint32_t,const juce::String&);
    bool scan();
    bool move(int64_t,juce::Point<int>);
    void notifyOwner();
};
