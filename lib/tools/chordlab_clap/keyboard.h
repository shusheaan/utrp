#pragma once
#include "keyboard_map.h"
#include <array>
#include <cstddef>

// Message-thread state only. Repeated key-down does not retrigger commands.
class KeyboardState final {
public:
    template<class Emit> bool press(int code, Emit emit)
    {
        if (code >= 'a' && code <= 'z') code -= 'a' - 'A';
        for (std::size_t i = 0; i < chordlabKeys.size(); ++i) {
            if (chordlabKeys[i].key != code) continue;
            if (!held[i] && !blocked[i]) { held[i] = true; emit(chordlabKeys[i].note, true); }
            return true;
        }
        return false;
    }
    template<class IsDown, class Emit> void releaseMissing(IsDown isDown, Emit emit)
    {
        for (std::size_t i = 0; i < chordlabKeys.size(); ++i) {
            if (isDown(chordlabKeys[i].key)) continue;
            if (held[i]) emit(chordlabKeys[i].note, false);
            held[i] = blocked[i] = false;
        }
    }
    template<class Emit> void releaseAll(Emit emit)
    {
        for (std::size_t i = 0; i < chordlabKeys.size(); ++i) {
            if (held[i]) { emit(chordlabKeys[i].note, false); blocked[i] = true; }
            held[i] = false;
        }
    }
private:
    std::array<bool, chordlabKeys.size()> held{};
    std::array<bool, chordlabKeys.size()> blocked{};
};
