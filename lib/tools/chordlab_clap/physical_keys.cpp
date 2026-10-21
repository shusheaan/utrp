#include "physical_keys.h"
#include <juce_gui_basics/juce_gui_basics.h>
#if JUCE_LINUX
#include <X11/Xlib.h>
#include <X11/keysym.h>
#include <X11/XKBlib.h>
#endif

PhysicalKeys::PhysicalKeys()
{
#if JUCE_LINUX
    display = XOpenDisplay(nullptr);
    if (!display) return;
    // This connection owns the ordered key stream. Auto-repeat must not invent
    // release/press pairs; a held key is released only by its real key-up.
    Bool detectable = False;
    if (!XkbSetDetectableAutoRepeat(static_cast<Display*>(display), True, &detectable) || !detectable) {
        XCloseDisplay(static_cast<Display*>(display));
        display = nullptr;
        return;
    }
    for (std::size_t i=0; i<chordlabKeys.size(); ++i) {
        const auto key = chordlabKeys[i].key;
        const auto symbol = key == 13 ? XK_Return : key == 9 ? XK_Tab : key == 27 ? XK_Escape : key;
        nativeCodes[i] = XKeysymToKeycode(static_cast<Display*>(display), symbol);
    }
#endif
}
PhysicalKeys::~PhysicalKeys()
{
#if JUCE_LINUX
    if (display) XCloseDisplay(static_cast<Display*>(display));
#endif
}
bool PhysicalKeys::available() const
{
#if JUCE_LINUX
    return display != nullptr;
#else
    return true;
#endif
}
void PhysicalKeys::refresh()
{
#if JUCE_LINUX
    if (!display) return;
    char bitmap[32]{};
    XQueryKeymap(static_cast<Display*>(display), bitmap);
    for (std::size_t i=0; i<down.size(); ++i) {
        const auto code = nativeCodes[i];
        down[i] = code != 0 && (static_cast<unsigned char>(bitmap[code / 8]) & (1u << (code % 8))) != 0;
    }
#else
    for (std::size_t i=0; i<down.size(); ++i)
        down[i] = juce::KeyPress::isKeyCurrentlyDown(chordlabKeys[i].key);
#endif
}
bool PhysicalKeys::grabFocus(void* nativeWindow)
{
#if JUCE_LINUX
    if (!display || !nativeWindow) return false;
    auto* connection = static_cast<Display*>(display);
    const auto window = reinterpret_cast<Window>(nativeWindow);
    XWindowAttributes attributes{};
    if (!XGetWindowAttributes(connection, window, &attributes) || attributes.map_state != IsViewable) return false;
    // Only called on opening or explicit editor activation. A cached JUCE timestamp
    // can predate the host's latest focus change and be rejected by X11.
    XSetInputFocus(connection, window, RevertToParent, CurrentTime);
    XFlush(connection);
#else
    juce::ignoreUnused(nativeWindow);
#endif
    return true;
}
bool PhysicalKeys::isDown(int code) const
{
    for (std::size_t i=0; i<down.size(); ++i)
        if (chordlabKeys[i].key == code) return down[i];
    return false;
}

std::vector<KeyboardCommand> PhysicalKeys::commands(void* nativeWindow, bool active)
{
#if JUCE_LINUX
    std::vector<KeyboardCommand> result;
    const auto emit = [&](int note, bool down) { result.push_back({note, down}); };
    const auto release = [&] { keyboard.releaseAll(emit); };
    if (!display || !nativeWindow) { release(); return result; }
    auto* connection = static_cast<Display*>(display);
    const auto window = reinterpret_cast<Window>(nativeWindow);
    const auto synchronize = [&] {
        char bitmap[32]{};
        XQueryKeymap(connection, bitmap);
        std::array<bool, 256> snapshot{};
        for (unsigned i = 0; i < snapshot.size(); ++i)
            snapshot[i] = (static_cast<unsigned char>(bitmap[i / 8]) & (1u << (i % 8))) != 0;
        nativeDown = snapshot;
        // Releases outside this peer have no local KeyRelease event. Clear the
        // focus-loss block for keys already up, while keeping pre-held keys blocked.
        keyboard.releaseMissing([&](int key) {
            for (std::size_t i = 0; i < nativeCodes.size(); ++i)
                if (chordlabKeys[i].key == key) return snapshot[nativeCodes[i]];
            return false;
        }, emit);
    };
    if (watchedWindow != nativeWindow) {
        // Key/Focus masks are non-exclusive. Observe only this plugin's peer,
        // never install a global shortcut or intercept the host's own events.
        XSelectInput(connection, window, KeyPressMask | KeyReleaseMask | FocusChangeMask);
        watchedWindow = nativeWindow;
        release();
        synchronize();
    }
    if (!active) release();
    bool eventActive = active;
    while (XPending(connection)) {
        XEvent event{};
        XNextEvent(connection, &event);
        if (event.xany.window != window) continue;
        if (event.type == FocusOut) {
            keyboard.releaseAll(emit); eventActive = false;
        }
        if (event.type == FocusIn) {
            keyboard.releaseAll(emit); synchronize(); eventActive = active;
        }
        if (event.type == KeyPress || event.type == KeyRelease) {
            const auto code = event.xkey.keycode;
            if (code >= nativeDown.size()) continue;
            const bool down = event.type == KeyPress;
            const bool firstPress = down && !nativeDown[code];
            nativeDown[code] = down;
            const bool modified = (event.xkey.state & (ShiftMask | ControlMask | Mod1Mask | Mod4Mask | Mod5Mask)) != 0;
            for (std::size_t i = 0; i < nativeCodes.size(); ++i) {
                if (nativeCodes[i] == code && firstPress && eventActive && !modified)
                    keyboard.press(chordlabKeys[i].key, emit);
            }
            if (!down) keyboard.releaseMissing([&](int key) {
                for (std::size_t i = 0; i < nativeCodes.size(); ++i)
                    if (chordlabKeys[i].key == key) return nativeDown[nativeCodes[i]];
                return false;
            }, emit);
        }
    }
    // Only synchronize outside active capture. A snapshot during capture could
    // race a queued key-down and erase a short tap; the event stream is authoritative.
    if (!active) synchronize();
    return result;
#else
    juce::ignoreUnused(nativeWindow, active);
    return {}; // This native left/right modifier implementation targets Linux.
#endif
}
