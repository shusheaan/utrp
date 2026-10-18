#include "keyboard.h"
#include <cstdlib>
#include <iostream>
#include <utility>
#include <vector>

void check(bool passed) { if (!passed) { std::cerr << "Keyboard invariant failed\n"; std::exit(1); } }
std::size_t pairs()
{
    std::size_t sequences = 0;
    for (const auto first : chordlabKeys) {
        check(first.key >= 0 && first.key < 256);
        for (const auto second : chordlabKeys) {
            check(second.key >= 0 && second.key < 256);
            if (first.key == second.key) continue;
            for (bool firstReleasedFirst : {false, true}) {
                KeyboardState state;
                std::array<bool, 256> down{};
                std::vector<std::pair<int, bool>> events;
                const auto emit = [&](int note, bool held) { events.emplace_back(note, held); };
                down[first.key] = down[second.key] = true;
                check(state.press(first.key, emit));
                check(state.press(second.key, emit));
                state.press(first.key, emit); state.press(second.key, emit);
                check(events.size() == 2);
                check(events[0] == std::make_pair(first.note, true));
                check(events[1] == std::make_pair(second.note, true));
                const auto a = firstReleasedFirst ? first : second;
                const auto b = firstReleasedFirst ? second : first;
                down[a.key] = false;
                state.releaseMissing([&](int key) { return down[key]; }, emit);
                check(events.size() == 3 && events.back() == std::make_pair(a.note, false));
                down[b.key] = false;
                state.releaseMissing([&](int key) { return down[key]; }, emit);
                check(events.size() == 4 && events.back() == std::make_pair(b.note, false));
                state.releaseAll(emit);
                check(events.size() == 4);
                ++sequences;
            }
        }
    }
    return sequences;
}
void heldChordNavigation()
{
    for (const int degree : {'Z', 'X', 'C', 'A', 'S', 'D', 'F'}) {
        KeyboardState state;
        std::array<bool, 256> down{};
        std::vector<std::pair<int, bool>> events;
        const auto emit = [&](int note, bool held) { events.emplace_back(note, held); };
        down[degree] = true;
        check(state.press(degree, emit));
        const int chordNote = events.front().first;
        for (const int move : {'L', 'L', 'H', 'H'}) {
            const auto before = events.size();
            down[move] = true;
            check(state.press(move, emit));
            for (int repeat = 0; repeat < 20; ++repeat) state.press(move, emit);
            check(events.size() == before + 1);
            check(events.back() == std::make_pair(move == 'L' ? 80 : 79, true));
            down[move] = false;
            state.releaseMissing([&](int key) { return down[key]; }, emit);
            check(events.size() == before + 2);
            check(events.back() == std::make_pair(move == 'L' ? 80 : 79, false));
        }
        check(!state.press(27, emit)); // Esc no longer moves voicing.
        down[degree] = false;
        state.releaseMissing([&](int key) { return down[key]; }, emit);
        check(events.back() == std::make_pair(chordNote, false));
        check(events.size() == 10); // No premature release of the held chord.
    }
}
void spaceSustain()
{
    KeyboardState state;
    std::vector<std::pair<int, bool>> events;
    const auto emit = [&](int note, bool down) { events.emplace_back(note, down); };
    check(state.press('C', emit));
    for (int i = 0; i < 100; ++i) check(state.press(' ', emit));
    check(events.size() == 2 && events.back() == std::make_pair(82, true));
    state.releaseMissing([](int key) { return key == 'C'; }, emit);
    check(events.size() == 3 && events.back() == std::make_pair(82, false));
    check(state.press(' ', emit));
    check(events.size() == 4 && events.back() == std::make_pair(82, true));
    state.releaseAll(emit);
    const auto size = events.size();
    state.press(' ', emit); // Preheld Space after focus loss cannot toggle again.
    check(events.size() == size);
}
void enterReset()
{
    KeyboardState state;
    std::vector<std::pair<int, bool>> events;
    const auto emit = [&](int note, bool down) { events.emplace_back(note, down); };
    check(state.press('C', emit));
    for (int i = 0; i < 100; ++i) check(state.press(13, emit));
    check(events.size() == 2 && events.back() == std::make_pair(81, true));
    state.releaseMissing([](int key) { return key == 'C'; }, emit);
    check(events.size() == 3 && events.back() == std::make_pair(81, false));
    check(state.press(13, emit));
    state.releaseAll(emit);
    const auto count = events.size();
    state.press(13, emit);
    check(events.size() == count); // No held Enter replay after focus loss.
}
int main()
{
    enterReset();
    spaceSustain();
    heldChordNavigation();
    std::size_t checks = 0;
    for (const auto mapping : chordlabKeys) {
        KeyboardState state;
        std::vector<std::pair<int, bool>> events;
        const auto emit = [&](int note, bool down) { events.emplace_back(note, down); };
        check(state.press(mapping.key, emit)); ++checks;
        for (int i = 0; i < 100; ++i) state.press(mapping.key, emit);
        check(events.size() == 1 && events[0] == std::make_pair(mapping.note, true)); ++checks;
        state.releaseAll(emit);
        check(events.size() == 2 && events.back() == std::make_pair(mapping.note, false)); ++checks;
        state.press(mapping.key, emit);
        check(events.size() == 2); ++checks; // Still physically down after focus loss.
        state.releaseMissing([](int) { return false; }, emit);
        state.press(mapping.key, emit);
        check(events.size() == 3); ++checks;
        state.releaseMissing([](int) { return false; }, emit);
        check(events.size() == 4 && !events.back().second); ++checks;
        check(!state.press(12345, emit)); ++checks;
        if (mapping.key >= 'A' && mapping.key <= 'Z') {
            check(state.press(mapping.key + 'a' - 'A', emit)); ++checks;
            check(events.size() == 5 && events.back().second); ++checks;
        }
    }
    std::cout << checks << " keyboard checks passed\n";
    std::cout << pairs() << " pairwise key order/release sequences passed\n";
}
