#pragma once
#include <algorithm>
#include <array>

// Event-driven, not timer-based: even a short chord cancels a pending modifier tap.
// Native key codes are boundary-checked; held modifiers at focus entry are seeded.
class ModifierTap final {
public:
    explicit ModifierTap(unsigned controlCode) : control(controlCode) {}
    void cancel() { candidate = false; }
    void synchronize(const std::array<bool, 256>& snapshot)
    {
        held = snapshot;
        if (control >= held.size() || !held[control] || otherHeld()) cancel();
    }
    bool key(unsigned code, bool down, bool active)
    {
        if (code >= held.size() || control == 0 || control >= held.size()) {
            cancel(); return false;
        }
        if (!active) cancel();
        if (down) {
            if (held[code]) return false;
            held[code] = true;
            if (code == control) candidate = active && !otherHeld();
            else cancel();
            return false;
        }
        const bool fire = code == control && held[code] && candidate && active;
        held[code] = false;
        if (code == control) cancel();
        return fire;
    }
private:
    bool otherHeld() const
    {
        for (unsigned i = 0; i < held.size(); ++i)
            if (i != control && held[i]) return true;
        return false;
    }
    unsigned control;
    std::array<bool, 256> held{};
    bool candidate{false};
};
