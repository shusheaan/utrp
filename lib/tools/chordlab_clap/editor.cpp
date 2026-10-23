#include "editor.h"
#include "processor.h"
#include "game_settings.h"

YsfxEditor::YsfxEditor(YsfxProcessor& p) : AudioProcessorEditor(p), processor(p), gamePanel(p.gameControl())
{
    enabled = physical.available();
    setWantsKeyboardFocus(true);
    setResizable(true, false);
    using namespace chordlabStyle;
    setResizeLimits(700 + 2 * padding_x, 560 + 2 * padding_y,
                    1600 + 2 * padding_x, 1200 + 2 * padding_y);
    addAndMakeVisible(view);
    view.setEffect(p.getCurrentInfo()->effect.get());
    if (auto* reserve=ysfx_find_var(p.getCurrentInfo()->effect.get(),"game_button_reserve"))
        *reserve=chordlabStyle::size+chordlabStyle::gap;
    displayedEffect = p.getCurrentInfo()->effect.get();
    view.setWantsKeyboardFocus(true);
    view.addKeyListener(this);
    view.addMouseListener(this, true);
    capture.addMouseListener(this, false);
    addKeyListener(this);
    for (auto* button : {&game, &sustain, &capture}) {
        addAndMakeVisible(button);
        button->setWantsKeyboardFocus(false);
        button->setColour(juce::TextButton::buttonColourId, juce::Colour(chordlabStyle::off));
        button->setColour(juce::TextButton::buttonOnColourId, juce::Colour(chordlabStyle::on));
    }
    addChildComponent(gamePanel);
    gamePanel.returnFocus=[this]{focusInput();};
    game.setName("Game");
    game.setTooltip("Game: reveal played notes, race piano against guitar. Red = normal mode.");
    game.onClick=[this]{toggleGame();};
    addChildComponent(errorLabel);
    errorLabel.setInterceptsMouseClicks(false, false);
    errorLabel.setColour(juce::Label::backgroundColourId, juce::Colour(0xffedb5b5));
    errorLabel.setColour(juce::Label::textColourId, juce::Colours::black);
    sustain.setName("Sustain");
    capture.setName("Active");
    sustain.setTooltip("Sustain baseline (Space): green = pedal-up sustain, red = pedal-up release. "
                       "Hold the pedal to invert; release to restore. S shows the baseline, not the pedal.");
    capture.setTooltip("Active: green: computer keyboard enabled and focused. Red: inactive. Click to activate or disable. "
                       "Hardware MIDI is independent.");
    capture.onClick = [this] {
        if (ignoreCaptureClick) return;
        enabled = !captureWasActive && physical.available();
        initialFocusPending = false;
        if (!enabled) { releaseKeys(); processor.keyboardControl().release(); }
        else focusInput();
        updateLabel();
    };
    sustain.onClick = [this] {
        processor.keyboardControl().key(82, true); // Existing command 22: toggle Sustain.
        processor.keyboardControl().key(82, false);
        focusInput();
    };
    setSize(884 + 2 * padding_x, 683 + 2 * padding_y);
    startTimerHz(50);
    updateLabel();
}

YsfxEditor::~YsfxEditor()
{
    stopTimer();
    gamePanel.deactivate();
    gameLayout.restore();
    releaseKeys();
    processor.keyboardControl().release();
    view.removeMouseListener(this);
    capture.removeMouseListener(this);
    view.removeKeyListener(this);
    removeKeyListener(this);
}

void YsfxEditor::resized()
{
    using namespace chordlabStyle;
    auto canvas = getLocalBounds().reduced(padding_x, padding_y);
    if(gameOpen) {
        gamePanel.setBounds(gamePanelBounds(canvas.removeFromRight(gameSettings::panelWidth),getHeight(),getWidth()));
        canvas.removeFromRight(12);
    }
    view.setBounds(canvas);
    capture.setBounds(canvas.getRight() - margin - size, canvas.getY() + 10, size, size);
    sustain.setBounds(capture.getX() - gap - size, capture.getY(), size, size);
    game.setBounds(sustain.getX() - gap - size, sustain.getY(), size, size);
    errorLabel.setBounds(canvas.getX() + 18, canvas.getY() + 40, canvas.getWidth() - 36, 30);
}


void YsfxEditor::toggleGame()
{
    if(!gameOpen) {
        if(!gamePanel.activate()) return;
        if(arrangeDelay<0) gameLayout.restore();
        gameLayout.remember();
        releaseKeys();
        normalWidth=getWidth(); normalHeight=getHeight();
        gameOpen=true; gamePanel.setVisible(true);
        setResizeLimits(700+2*chordlabStyle::padding_x+gameSettings::panelWidth+12,
                        560+2*chordlabStyle::padding_y,
                        1600+2*chordlabStyle::padding_x+gameSettings::panelWidth+12,
                        1200+2*chordlabStyle::padding_y);
        setSize(normalWidth+gameSettings::panelWidth+12,normalHeight);
        arrangeDelay=8;
    } else {
        gameLayout.prepareRestore();
        gamePanel.deactivate(); gameOpen=false; gamePanel.setVisible(false);
        setResizeLimits(700+2*chordlabStyle::padding_x,560+2*chordlabStyle::padding_y,
                        1600+2*chordlabStyle::padding_x,1200+2*chordlabStyle::padding_y);
        setSize(normalWidth,normalHeight);
        arrangeDelay=-8;
    }
    game.setToggleState(gameOpen,juce::dontSendNotification);
    if(isShowing()) focusInput();
}

void YsfxEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour(chordlabStyle::background));
}


void YsfxEditor::mouseDown(const juce::MouseEvent& event)
{
    if (event.eventComponent == &view && event.mods.isPopupMenu()) {
        showAppearanceMenu();
        return;
    }
    if (event.eventComponent == &capture) {
        ignoreCaptureClick = event.mods.isPopupMenu();
        // Snapshot the displayed state before focusing this window. A red button
        // caused by focus loss must activate, not disable, keyboard capture.
        captureWasActive = capture.getToggleState();
    }
    if (event.eventComponent == &view) focusInput();
}

void YsfxEditor::showAppearanceMenu()
{
    if (appearanceMenuOpen) return;
    appearanceMenuOpen = true;
    releaseKeys();
    updateLabel();
    const bool bright = processor.getParameters()[18]->getValue() >= 0.5f;
    juce::PopupMenu menu;
    menu.addSectionHeader("Appearance");
    menu.addItem(1, "Dark", true, !bright);
    menu.addItem(2, "Bright", true, bright);
    juce::Component::SafePointer<YsfxEditor> safeThis(this);
    menu.showMenuAsync(juce::PopupMenu::Options().withMousePosition(), [safeThis](int choice) {
        if (!safeThis) return;
        if (choice == 1 || choice == 2) {
            auto* parameter = safeThis->processor.getParameters()[18];
            parameter->beginChangeGesture();
            parameter->setValueNotifyingHost(choice == 2 ? 1.0f : 0.0f);
            parameter->endChangeGesture();
        }
        safeThis->appearanceMenuOpen = false;
        if (safeThis->enabled) safeThis->focusInput();
        safeThis->updateLabel();
    });
}

bool YsfxEditor::focusInput()
{
    if (!isShowing()) return false;
    // JUCE may still consider the component focused after the host moved native
    // focus to its container. Reassert the peer even when the component call is a no-op.
    if (auto* peer = getPeer()) {
#if JUCE_LINUX
        if (!physical.grabFocus(peer->getNativeHandle())) return false;
#else
        peer->grabFocus();
#endif
        view.grabKeyboardFocus();
        return true;
    }
    return false;
}

void YsfxEditor::mouseUp(const juce::MouseEvent& event)
{
    if (event.eventComponent == &view && !appearanceMenuOpen) focusInput();
}

void YsfxEditor::releaseKeys()
{
#if JUCE_LINUX
    physical.cancelKeys();
    processor.keyboardControl().release();
#else
    keyboard.releaseAll([this](int note, bool down) { processor.keyboardControl().key(note, down); });
#endif
}

bool YsfxEditor::hasInputFocus() const
{
    // Embedded hosts can move native focus without updating JUCE's component
    // focus cache in either direction. This editor has no text-entry children;
    // the peer's actual OS focus (including child windows) is authoritative.
    const auto* peer = getPeer();
    return !appearanceMenuOpen && isShowing() && peer != nullptr && peer->isFocused();
}

bool YsfxEditor::keyPressed(const juce::KeyPress& key, juce::Component*)
{
    if (!enabled || !hasInputFocus()) return false;
    const auto mods = key.getModifiers();
    if (mods.isCtrlDown() || mods.isAltDown() || mods.isCommandDown() || mods.isShiftDown()) return false;
#if JUCE_LINUX
    dispatchNativeKeys();
#else
    keyboard.press(key.getKeyCode(), [this](int note, bool down) { processor.keyboardControl().key(note, down); });
#endif
    return true; // Reserve unmodified keys while this editor owns focus.
}

bool YsfxEditor::keyStateChanged(bool, juce::Component*)
{
    const bool focused = hasInputFocus();
#if JUCE_LINUX
    dispatchNativeKeys();
#else
    physical.refresh();
    keyboard.releaseMissing([this](int code) {
        return physical.isDown(code);
    },
        [this](int note, bool down) { processor.keyboardControl().key(note, down); });
#endif
    return enabled && focused;
}

void YsfxEditor::dispatchNativeKeys()
{
    const auto* peer = getPeer();
    for (const auto command : physical.commands(peer ? peer->getNativeHandle() : nullptr, enabled && hasInputFocus()))
        processor.keyboardControl().key(command.note, command.down);
}

void YsfxEditor::timerCallback()
{
    // The host may show the editor before mapping its native parent. Retry only
    // until the first viewable activation, never after the user moves focus away.
    if (!isShowing()) initialFocusPending = enabled;
    else if (initialFocusPending && enabled && juce::Time::getMillisecondCounterHiRes() >= focusAfterMs)
        initialFocusPending = !focusInput();
    // A host can focus its editor container rather than the keyboard peer.
    // Hand focus inward only inside our own active window; never from another app.
    if (enabled && isShowing())
        if (auto* peer = getPeer(); peer && physical.hostHasFocus(peer->getNativeHandle()))
            focusInput();
    auto info = processor.getCurrentInfo();
    if (displayedEffect != info->effect.get()) {
        displayedEffect = info->effect.get();
        view.setEffect(displayedEffect);
        if(auto* reserve=ysfx_find_var(displayedEffect,"game_button_reserve"))
            *reserve=chordlabStyle::size+chordlabStyle::gap;
        if(gameOpen) toggleGame();
        releaseKeys();
    }
    const bool focused = hasInputFocus();
    if (hadFocus && !focused) releaseKeys();
    hadFocus = focused;
    // Use one ordered native stream for both mapped keys and modifier taps.
    // Key callbacks drain it immediately; the timer also handles host misses.
    dispatchNativeKeys();
    updateLabel();
    const auto resetSerial=processor.gameControl().resets();
    if(resetSerial!=gameResetSerial) {
        gameResetSerial=resetSerial;
        if(gameOpen) toggleGame();
    }
    gamePanel.tick();
    if(gameOpen) {
        const auto* size=ysfx_find_var(displayedEffect,"choices_text_size");
        // font_scale compensates the LICE/SWELL font backend, not JUCE text.
        // Share the fitted theme size without applying that backend correction twice.
        if(size && *size>0)
            gamePanel.setCapsuleStyle(gameCapsuleStyle(view.getWidth(),gamePanel.getWidth(),float(*size)));
        repaint(0,0,getWidth(),4);
    }
    if(arrangeDelay>0 && --arrangeDelay==0) {
        gameLayout.arrange();
        if(gameLayout.noSpace && gameOpen) toggleGame();
    }
    if(arrangeDelay<0 && ++arrangeDelay==0) gameLayout.restore();
    if(gameLayout.error.isNotEmpty()) game.setTooltip(gameLayout.error);
#if !JUCE_LINUX
    keyStateChanged(false, this);
#endif
}

void YsfxEditor::visibilityChanged()
{
    initialFocusPending = enabled;
    focusAfterMs = juce::Time::getMillisecondCounterHiRes() + chordlabStyle::focus_settle_ms;
    // The host may still be attaching/reparenting its native wrapper here.
    // Let the timer acquire focus after those X11 requests have been dispatched.
    if (!isShowing()) { if(gameOpen) toggleGame(); releaseKeys(); processor.keyboardControl().release(); }
}

void YsfxEditor::updateLabel()
{
    capture.setToggleState(enabled && hasInputFocus(),
                           juce::dontSendNotification);
    sustain.setToggleState(processor.getParameters()[17]->getValue() >= 0.5f,
                           juce::dontSendNotification);
    auto error = processor.embeddedSource().error();
    if (!physical.available()) error = "Keyboard unavailable: X11 with detectable auto-repeat required";
    if (error.isEmpty()) error = processor.getCurrentInfo()->errors.joinIntoString("; ");
    errorLabel.setText(error, juce::dontSendNotification);
    errorLabel.setVisible(error.isNotEmpty());
}
