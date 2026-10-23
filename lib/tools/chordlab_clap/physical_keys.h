#pragma once
#include "keyboard_map.h"
#include "keyboard.h"
#include <array>
#include <vector>

// Message-thread input. Linux uses one ordered X11 stream with detectable repeat;
// snapshots only initialize/resynchronize inactive capture, never active key-up.
struct KeyboardCommand { int note; bool down; };

class PhysicalKeys final {
public:
    PhysicalKeys();
    ~PhysicalKeys();
    PhysicalKeys(const PhysicalKeys&) = delete;
    PhysicalKeys& operator=(const PhysicalKeys&) = delete;
    bool available() const;
    bool grabFocus(void* nativeWindow);
    bool hostHasFocus(void* nativeWindow) const;
    void refresh();
    bool isDown(int code) const;
    std::vector<KeyboardCommand> commands(void* nativeWindow, bool active);
    void cancelKeys() { keyboard.releaseAll([](int, bool) {}); }
private:
    void* display{};
    std::array<unsigned, chordlabKeys.size()> nativeCodes{};
    std::array<bool, chordlabKeys.size()> down{};
    void* watchedWindow{};
    KeyboardState keyboard;
    std::array<bool, 256> nativeDown{};
};
