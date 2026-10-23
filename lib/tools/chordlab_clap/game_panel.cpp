#include "game_panel.h"
#include "game_settings.h"
#include "control_style.h"

GamePanel::GamePanel(GameControl& c) : control(c)
{
    for (auto* b:{&startButton,&pauseButton}) { addAndMakeVisible(b); b->setWantsKeyboardFocus(false); }
    for (auto* s:{&limit,&demo}) {
        addAndMakeVisible(s); s->setSliderStyle(juce::Slider::IncDecButtons);
        s->setTextBoxStyle(juce::Slider::TextBoxLeft,true,48,24); s->setWantsKeyboardFocus(false);
        s->onValueChange=[this]{if(returnFocus) returnFocus();};
    }
    limit.setRange(1,120,1); limit.setValue(gameSettings::answerSeconds);
    demo.setRange(1,10,1); demo.setValue(gameSettings::demoSeconds);
    startButton.onClick=[this]{start(); if(returnFocus) returnFocus();};
    pauseButton.onClick=[this]{ if(running && !control.send({4})) error="Pause queue full"; if(returnFocus) returnFocus(); };
}
GamePanel::~GamePanel() { deactivate(); }
bool GamePanel::activate()
{
    active=control.send({1}); running=false; pending=false; status={}; error.clear();
    startButton.setButtonText("Start"); pauseButton.setEnabled(false);
    if(!active) error="Game command queue full";
    return active;
}
void GamePanel::deactivate()
{
    if(active) control.off();
    active=false; running=false; pending=false; preview.clear();
    if(planner) chordlab_game_free(planner);
    planner=nullptr;
}
bool GamePanel::plan()
{
    while(preview.size()<4) {
        GameTarget target;
        if(!chordlab_game_next(planner,&target)) { error="No valid target: stopped safely"; running=false; control.off(); return false; }
        preview.push_back(target);
    }
    return true;
}
void GamePanel::start()
{
    if(!active) return;
    if(planner) chordlab_game_free(planner);
    seed=uint64_t(juce::Time::getHighResolutionTicks());
    planner=chordlab_game_new(seed); preview.clear();
    if(!planner) { error="Harmony planner could not start"; return; }
    error.clear();
    if(!plan() || !control.send({1})) { error="Cannot reset game"; return; }
    running=present();
    startButton.setButtonText("Restart"); pauseButton.setEnabled(running);
}
bool GamePanel::present()
{
    if(preview.empty()) return false;
    auto next=preview.front();
    next.id=++targetSerial;
    if(!control.send({3,next,limit.getValue(),demo.getValue()})) { error="Target queue full"; return false; }
    current=next; preview.pop_front(); pending=true;
    return plan();
}
void GamePanel::tick()
{
    if(!active) return;
    if(control.read(status)) {
        if(status.id==int(current.id) && status.phase==2) pending=false;
        // A very short/full-chord first block may finish before the UI sees phase 2.
        if(status.phase==4 && status.id==int(current.id) && running) { pending=false; running=present(); }
        if(status.phase==0 && running && !pending) {
            running=false; pauseButton.setEnabled(false); startButton.setButtonText("Start");
            error="Host reset: press Start to resume a new game";
        }
        pauseButton.setButtonText(status.phase==5 ? "Resume" : "Pause");
        repaint();
    }
}
void GamePanel::resized()
{
    startButton.setBounds(18,48,128,30); pauseButton.setBounds(156,48,128,30);
    limit.setBounds(170,getHeight()-110,114,26); demo.setBounds(170,getHeight()-74,114,26);
}
void GamePanel::paint(juce::Graphics& g)
{
    using namespace chordlabStyle;
    g.fillAll(juce::Colour(game_background));
    g.setColour(juce::Colour(game_border)); g.drawVerticalLine(0,0,float(getHeight()));
    const auto text=[&](juce::String s,int y,int h,float size,juce::Colour colour){
        g.setColour(colour); g.setFont(juce::Font(juce::FontOptions("DejaVu Sans",size,juce::Font::plain)));
        g.drawFittedText(s,18,y,getWidth()-36,h,juce::Justification::centredLeft,3);
    };
    const auto white=juce::Colour(game_text), muted=juce::Colour(game_muted), green=juce::Colour(game_reason);
    const auto key=juce::Colour(game_key), chord=juce::Colour(game_chord), warning=juce::Colour(game_error);
    const bool compact=getHeight()<650;
    text("CHORD RACE",10,30,20,white);
    if(!running) {
        text("Same pitches. Two instruments.\nFirst to finish wins the chord.",100,60,16,white);
        text("Read the chord / bass capsule.\nPlay every exact pitch once.\nGuitar: any string or fret.",180,100,15,muted);
    } else {
        text(juce::String(current.keyLabel),90,28,19,key);
        text(juce::String(current.label),122,38,26,chord);
        const juce::String phase=status.phase==3 ? "ANSWER / DEMO" : status.phase==5 ? "PAUSED" : pending ? "LOADING" : "PLAY";
        text(phase+"   "+juce::String(status.remaining,1)+" s",168,30,20,status.phase==3 ? juce::Colour(game_demo) : green);
        text("Piano   "+juce::String(status.pianoHits)+" / "+juce::String(current.count)+"       "+juce::String(status.pianoScore)+" pts",208,26,17,white);
        text("Guitar   "+juce::String(status.guitarHits)+" / "+juce::String(current.count)+"       "+juce::String(status.guitarScore)+" pts",236,26,17,white);
        text("Timed out: "+juce::String(status.timeouts),264,20,13,muted);
        text(juce::String("REGISTER: ")+(current.movement>0 ? "RISING" : current.movement<0 ? "FALLING" : "HOLD"),288,24,14,green);
        // Keep explanations readable: wrap at a fixed font size, never squeeze
        // a whole modulation sentence into one horizontally compressed line.
        juce::AttributedString explanation;
        explanation.append(error.isEmpty() ? juce::String(current.reason) : error,
            juce::Font(juce::FontOptions("DejaVu Sans",compact ? 13.0f : 15.0f,juce::Font::plain)),
            error.isEmpty() ? green : warning);
        explanation.draw(g,{18.0f,316.0f,float(getWidth()-36),float(compact ? 60 : 78)});
        text("NEXT",compact ? 380 : 406,18,13,muted);
        for(size_t i=0;i<std::min(size_t(2),preview.size());++i) {
            juce::AttributedString row;
            const auto font=juce::Font(juce::FontOptions("DejaVu Sans",compact ? 13.0f : 15.0f,juce::Font::plain));
            row.append(juce::String(preview[i].label),font,white);
            row.append("  /  "+juce::String(preview[i].keyLabel),font,key);
            row.draw(g,{18.0f,float((compact ? 400 : 430)+int(i)*(compact ? 24 : 36)),
                        float(getWidth()-36),float(compact ? 24 : 34)});
        }
    }
    text("Answer seconds",getHeight()-110,26,14,muted);
    text("Demo seconds",getHeight()-74,26,14,muted);
    text("Demo MIDI ch16 -> piano instrument",getHeight()-38,26,11,muted);
    if(error.isNotEmpty() && !running) text(error,350,60,13,warning);
}
