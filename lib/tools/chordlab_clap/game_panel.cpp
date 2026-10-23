#include "game_panel.h"
#include "game_settings.h"
#include "control_style.h"
#include "game_view.h"

GamePanel::GamePanel(GameControl& c) : control(c)
{
    setLookAndFeel(&controlsLook);
    for (auto* b:{&startButton,&pauseButton}) { addAndMakeVisible(b); b->setWantsKeyboardFocus(false); }
    for (auto* s:{&limit,&demo,&modulation}) {
        addAndMakeVisible(s);
        s->onValueChange=[this]{if(returnFocus) returnFocus();};
    }
    limit.setName("Play"); demo.setName("Demo"); modulation.setName("Mod");
    limit.setTextValueSuffix(" s"); demo.setTextValueSuffix(" s");
    limit.setTooltip("Hover and scroll: 1 second per step. Applies to the next chord.");
    demo.setTooltip("Hover and scroll: 1 second per step. Applies to the next chord.");
    limit.setRange(1,120,1); limit.setValue(gameSettings::answerSeconds);
    demo.setRange(1,10,1); demo.setValue(gameSettings::demoSeconds);
    modulation.setRange(0,100,5); modulation.setValue(gameSettings::modulationPercent);
    modulation.setTextValueSuffix(" %");
    direction.addItemList({"Register: Mixed", "Register: Hold", "Register: Rise", "Register: Fall"},1); direction.setSelectedId(1);
    direction.setWantsKeyboardFocus(false); addAndMakeVisible(direction);
    direction.onChange=[this]{if(returnFocus) returnFocus();};
    approaches.setToggleState(true,juce::dontSendNotification); approaches.setWantsKeyboardFocus(false);
    approaches.onClick=[this]{if(returnFocus) returnFocus();}; addAndMakeVisible(approaches);
    direction.setTooltip("Applied at Start/Restart. Rise/Fall turn around at the pitch boundary.");
    modulation.setTooltip("Hover and scroll: 5% per step. After all 7 degrees succeed; applies on Start/Restart.");
    approaches.setTooltip("Secondary, tritone-substitute and ii-V approaches. Applies on Start/Restart.");
    startButton.onClick=[this]{start(); if(returnFocus) returnFocus();};
    pauseButton.onClick=[this]{ if(running && !control.send({4})) error="Pause queue full"; if(returnFocus) returnFocus(); };
}
GamePanel::~GamePanel() { deactivate(); setLookAndFeel(nullptr); }
void GamePanel::setCapsuleStyle(GameCapsuleStyle style)
{
    capsuleStyle=style;
    if(controlsLook.fontHeight==style.fontHeight) return;
    controlsLook.fontHeight=style.fontHeight;
    for(auto* value:{&limit,&demo,&modulation}) value->fontHeight=style.fontHeight;
    sendLookAndFeelChange(); repaint();
}
bool GamePanel::activate()
{
    active=control.send({1}); running=false; pending=false; replaying=false; trail.clear(); status={}; error.clear();
    startButton.setButtonText("Start"); pauseButton.setEnabled(false);
    if(!active) error="Game command queue full";
    return active;
}
void GamePanel::deactivate()
{
    direction.hidePopup();
    if(active) control.off();
    active=false; running=false; pending=false; replaying=false; preview.clear(); trail.clear();
    if(planner) chordlab_game_free(planner);
    planner=nullptr;
}
bool GamePanel::plan()
{
    // Three harmonic groups: NOW and two backbone destinations, including every
    // committed approach/pivot. Never invent, omit or regenerate preview events.
    const int needed=current.count && current.backbone ? 2 : 3;
    int complete=int(std::count_if(preview.begin(),preview.end(),[](const auto& t){return t.backbone!=0;}));
    while(complete<needed) {
        GameTarget target;
        if(!chordlab_game_next(planner,&target)) { error="No valid target: stopped safely"; running=false; control.off(); return false; }
        preview.push_back(target);
        if(target.backbone) ++complete;
    }
    return true;
}
void GamePanel::start()
{
    if(!active) return;
    if(planner) chordlab_game_free(planner);
    seed=uint64_t(juce::Time::getHighResolutionTicks());
    planner=chordlab_game_new(seed); preview.clear(); trail.clear(); replaying=false;
    if(!planner) { error="Harmony planner could not start"; return; }
    const int motion[]{2,0,1,-1};
    if(!chordlab_game_configure(planner,modulation.getValue()/100.0,
        motion[direction.getSelectedId()-1],approaches.getToggleState())) {
        error="Invalid practice settings"; return;
    }
    coverage=0; presented=0; current={};
    error.clear();
    if(!plan() || !control.send({1})) { error="Cannot reset game"; return; }
    running=present();
    startButton.setButtonText("Restart"); pauseButton.setEnabled(running);
}
bool GamePanel::present()
{
    if(preview.empty()) return false;
    auto next=preview.front();
    const auto planned=next;
    next.id=++targetSerial;
    if(!control.send({3,next,limit.getValue(),demo.getValue()})) { error="Target queue full"; return false; }
    if(current.visit!=planned.visit) coverage=0;
    if(current.count && current.group==planned.group)
        trail.push_back({current,status.winner!=0});
    else trail.clear();
    practiceScroll=0;
    answerDuration=limit.getValue(); demoDuration=demo.getValue();
    replaying=false;
    current=planned; ++presented; preview.pop_front(); pending=true;
    return plan();
}
void GamePanel::tick()
{
    if(!active) return;
    if(control.read(status)) {
        if(status.id==int(targetSerial) && (status.phase==2 || status.phase==3 || status.phase==5)) pending=false;
        if(status.id==int(targetSerial)) {
            if(status.phase==3 || status.phase==4) replaying=true;
            else if(status.phase==2) replaying=false;
        }
        // A very short/full-chord first block may finish before the UI sees phase 2.
        if(status.phase==4 && status.id==int(targetSerial) && running) {
            const bool success=status.pianoHits==int(current.count) || status.guitarHits==int(current.count);
            if(!chordlab_game_complete(planner,current.id,success)) {
                error="Out-of-order result: stopped safely"; running=false; control.off();
            } else {
                if(success && current.backbone && current.degree>=0 && current.degree<7)
                    coverage|=1u<<current.degree;
                pending=false; running=present();
            }
        }
        if(status.phase==0 && running && !pending) {
            running=false; pauseButton.setEnabled(false); startButton.setButtonText("Start");
            error="Host reset: press Start to resume a new game";
        }
        pauseButton.setButtonText(status.phase==5 ? "Resume" : "Pause");
        repaint();
    }
}
double GamePanel::progress() const
{
    if(!running || pending) return 0;
    return std::clamp(status.remaining/(replaying ? demoDuration : answerDuration),0.0,1.0);
}
void GamePanel::resized()
{
    using namespace gameControls;
    const int width=getWidth()-2*margin, half=(width-gap)/2;
    int y=getHeight()-settingsHeight+2*gap;
    startButton.setBounds(margin,y,half,height);
    pauseButton.setBounds(margin+half+gap,y,width-half-gap,height);
    y+=height+gap;
    const int third=(width-2*gap)/3;
    limit.setBounds(margin,y,third,height);demo.setBounds(margin+third+gap,y,third,height);
    modulation.setBounds(margin+2*(third+gap),y,width-2*(third+gap),height);
    y+=height+gap; direction.setBounds(margin,y,width,height);
    y+=height+gap; approaches.setBounds(margin,y,width,height);
}
namespace {
void panelText(juce::Graphics& g,const juce::String& text,juce::Rectangle<int> bounds,
               float size,juce::Colour color,int lines=1)
{
    g.setColour(color); g.setFont(juce::Font(juce::FontOptions("DejaVu Sans",size,juce::Font::plain)));
    g.drawFittedText(text,bounds,juce::Justification::centredLeft,lines);
}
}

void GamePanel::paint(juce::Graphics& g)
{
    using namespace chordlabStyle;
    // Same outer radius as the two embedded choice strips (height / 2).
    // Clip the countdown too, so full progress never paints square corners.
    juce::Graphics::ScopedSaveState saved(g);
    juce::Path outline;
    outline.addRoundedRectangle(getLocalBounds().toFloat(),float(choice_height)/2);
    g.reduceClipRegion(outline);
    g.fillAll(juce::Colour(game_background));
    const int settings=getHeight()-gameControls::settingsHeight;
    paintGamePractice(g,{0,0,getWidth(),settings},running ? current : GameTarget{},
        preview,trail,status,replaying,capsuleStyle,practiceScroll);
    // Countdown belongs to this panel, never to the normal keyboard canvas.
    // The unfilled countdown track is the panel itself, not a separate stripe.
    g.setColour(juce::Colour(game_reason));
    g.fillRect(0,0,int(std::round(getWidth()*progress())),4);
    g.setColour(juce::Colour(game_border)); g.drawHorizontalLine(settings-3,14,float(getWidth()-14));
    if(error.isNotEmpty()) panelText(g,error,{14,230,getWidth()-28,70},14,juce::Colour(game_error),4);
}

void GamePanel::mouseWheelMove(const juce::MouseEvent& event,const juce::MouseWheelDetails& wheel)
{
    if(event.y>=getHeight()-gameControls::settingsHeight || wheel.deltaY==0) return;
    const auto rows=gamePracticeRows(current,preview,trail,replaying,status.winner);
    const int available=getHeight()-gameControls::settingsHeight;
    const int maximum=std::max(0,gamePracticeHeight(rows,capsuleStyle,available)-available);
    practiceScroll=std::clamp(practiceScroll+(wheel.deltaY>0 ? -27 : 27),0,maximum);
    repaint();
}
