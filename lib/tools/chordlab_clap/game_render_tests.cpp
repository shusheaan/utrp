// Run in an isolated X11/Sway session. Optional directory exports UI fixtures.
#include "game_panel.h"
#include "game_view.h"
#include "game_settings.h"
#include "control_style.h"
#include <cstdio>
#include <iostream>

namespace {
GameTarget target(unsigned id,unsigned group,unsigned visit,int role,const char* key,
                  const char* capsule,const char* bass)
{
    GameTarget t{};t.id=id;t.group=group;t.visit=visit;t.paletteRole=role;t.count=4;
    std::snprintf(t.keyLabel,sizeof t.keyLabel,"%s",key);
    std::snprintf(t.capsule,sizeof t.capsule,"%s",capsule);
    std::snprintf(t.bass,sizeof t.bass,"%s",bass);
    return t;
}
bool writeImage(const juce::Image& image,const juce::File& directory,const juce::String& name)
{
    if(directory.createDirectory().failed()) return false;
    auto stream=directory.getChildFile(name).createOutputStream();
    if(!stream) return false;
    stream->setPosition(0); stream->truncate();
    return juce::PNGImageFormat().writeImageToStream(image,*stream);
}
bool wheelControls(GamePanel& panel)
{
    int count=0;
    for(auto* child:panel.getChildren()) {
        auto* value=dynamic_cast<GameWheelValue*>(child);
        if(!value) continue;
        ++count;
        const auto initial=value->getValue(), step=value->getInterval();
        juce::MouseEvent event(juce::Desktop::getInstance().getMainMouseSource(),{}, {},
            0,0,0,0,0,value,value,juce::Time::getCurrentTime(),{}, {},0,false);
        juce::MouseWheelDetails wheel{};wheel.deltaY=0.1f;
        value->mouseWheelMove(event,wheel);
        if(value->getValue()!=initial+step) return false;
        wheel.isReversed=true;value->mouseWheelMove(event,wheel);
        if(value->getValue()!=initial) return false;
        value->setValue(value->getMinimum());value->mouseWheelMove(event,wheel);
        if(value->getValue()!=value->getMinimum()) return false;
        value->setValue(value->getMaximum());wheel.isReversed=false;value->mouseWheelMove(event,wheel);
        if(value->getValue()!=value->getMaximum()) return false;
        value->setValue(initial);
        for(auto* widget:value->getChildren()) if(dynamic_cast<juce::Button*>(widget)) return false;
    }
    return count==3;
}

}
int main(int argc,char** argv)
{
    juce::ScopedJuceInitialiser_GUI gui;
    const int width=gameSettings::panelWidth;
    GameControl control;
    GamePanel panel(control);
    if(!panel.activate() || !wheelControls(panel) || panel.progress()!=0) return 1;
    const auto style=gameCapsuleStyle(884,width,10);
    panel.setCapsuleStyle(style);
    if(style.keyWidth!=57 || style.chordWidth!=115) return 9;
    auto previous=target(1,3,1,1,"C ionian","ii Am7","C4(b3)");
    auto current=target(2,3,1,2,"C ionian","V D7","C4(b7)");
    previous.kind=1;current.kind=1;
    const std::deque<GameTrailStep> trail{{previous,true}};
    std::deque<GameTarget> preview{
        target(3,3,1,2,"C ionian","V G7","B3(3)"),
        target(4,4,1,1,"C ionian","iii Em7","B3(5)"),
        target(5,7,2,1,"F ionian","ii Gm7","Bb3(b3)"),
        target(6,7,2,2,"F ionian","V C7","Bb3(b7)"),
        target(7,7,2,0,"F ionian","I Fmaj7","A3(3)")};
    std::snprintf(preview[2].action,sizeof preview[2].action,"Modulate: destination V7");
    const auto rows=gamePracticeRows(current,preview,trail,false,0);
    if(rows[0].size()!=3 || rows[1].size()!=1 || rows[2].size()!=3 ||
       rows[0][0].state!=GameStepState::Complete || rows[0][1].state!=GameStepState::Current ||
       rows[0][2].state!=GameStepState::Upcoming) return 2;
    auto nextGroup=preview[1];
    if(gamePracticeRows(nextGroup,{},trail,false,0)[0].size()!=1) return 3;
    for(int height:{540,683,1180}) {
        panel.setSize(width,height);
        const auto idle=panel.createComponentSnapshot(panel.getLocalBounds());
        if(!idle.isValid()) return 4;
        if(idle.getPixelAt(width/2,1)!=juce::Colour(chordlabStyle::game_border) ||
           idle.getPixelAt(width/2,4)!=juce::Colour(chordlabStyle::game_background)) return 10;
        for(int outcome:{0,1,2}) {
            GameStatus s{};s.phase=outcome ? 3 : 2;s.remaining=outcome ? 1.8 : 8.6;
            s.winner=outcome==1 ? 1 : 0;s.award=86;s.pianoScore=240;s.guitarScore=180;
            const bool replaying=outcome!=0;
            juce::Image image=panel.createComponentSnapshot(panel.getLocalBounds());
            juce::Graphics g(image);g.setColour(juce::Colours::black);g.fillRect(0,0,width,height-178);
            paintGamePractice(g,{0,0,width,height-178},current,preview,trail,s,replaying,style);
            const int start=24;
            if(image.getPixelAt(20,75)!=juce::Colour(chordlabStyle::choice_button_selected) ||
               image.getPixelAt(20,226)!=juce::Colours::white ||
               image.getPixelAt(start+6,102)!=juce::Colours::black) return 5;
            const bool hollow=image.getPixelAt(start+16+6,129)==juce::Colours::black;
            if(hollow!=replaying) return 6;
            if(!replaying && image.getPixelAt(start+16+6,129)!=juce::Colour(chordlabStyle::choice_button_selected)) return 10;
            if(image.getPixelAt(start+16+style.chordWidth+9,129)!=juce::Colour(chordlabStyle::capsule_fifth)) return 11;
            const auto result=gamePracticeRows(current,preview,trail,replaying,s.winner);
            if(outcome==2 && result[0][1].state!=GameStepState::Missed) return 7;
            if(argc==2 && height==683 && !writeImage(image,juce::File(argv[1]),
                "stairs-"+juce::String(outcome)+".png")) return 8;
        }
        // UTF-8 notation, pause during replay, and maximum nine-capsule layout.
        auto unicode=current;std::snprintf(unicode.capsule,sizeof unicode.capsule,"viiø Bm7b5");
        std::deque<GameTarget> full;
        for(unsigned group:{3,3,4,4,4,5,5,5}) {
            auto t=unicode;t.group=group;t.visit=group;full.push_back(t);
        }
        GameStatus paused{};paused.phase=5;paused.winner=1;
        juce::Image image(juce::Image::ARGB,width,height,true);juce::Graphics g(image);
        for(const char* method:{"Modulate: shared 7th","Modulate: diminished 7th",
                               "Modulate: destination V7","Arrival: same tonic, new mode"}) {
            std::snprintf(unicode.action,sizeof unicode.action,"%s",method);
            std::snprintf(unicode.reason,sizeof unicode.reason,"Shared chord: old 2 = new 6; then V7 -> tonic");
            paintGamePractice(g,{0,0,width,height-178},unicode,full,{},paused,true,style);
        }
    }
    std::cout<<"Single-column stairs, shared capsule metrics, gray approaches, gray/white keys, retained trail, wheel controls/bounds, UTF-8, 3 heights: PASS\n";
}
