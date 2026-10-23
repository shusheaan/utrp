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

bool densePreview(const juce::File& output,const GameCapsuleStyle& style,bool exportImages)
{
    constexpr int width=278, height=663, practice=height-178;
    for(int keyCount:{2,3}) {
        std::deque<GameTarget> events;
        for(unsigned group=1;group<=3;++group) for(unsigned step=0;step<3;++step) {
            const unsigned visit=keyCount==3 ? group : group==3 ? 2 : 1;
            const char* key=visit==1 ? "C ionian" : visit==2 ? "F ionian" : "Bb ionian";
            const char* names[][3]={{"ii Dm7","V G7","I Cmaj7"},
                                    {"ii Gm7","V C7","I Fmaj7"},
                                    {"ii Cm7","V F7","I Bbmaj7"}};
            auto t=target(group*3+step,group,visit,step==0 ? 1 : step==1 ? 2 : 0,
                          key,names[visit-1][step],
                          step==0 ? (visit==1 ? "D4(1)" : visit==2 ? "G3(1)" : "C4(1)") :
                          step==1 ? (visit==1 ? "G3(1)" : visit==2 ? "C4(1)" : "F3(1)") :
                                    (visit==1 ? "C4(1)" : visit==2 ? "F3(1)" : "Bb3(1)"));
            t.kind=step==0 ? 1 : step==1 ? 2 : 3;
            if(step==1) std::snprintf(t.action,sizeof t.action,"Modulate: destination V7");
            events.push_back(t);
        }
        const auto current=events.front();events.pop_front();
        const auto rows=gamePracticeRows(current,events,{},false,0);
        for(const auto& row:rows) if(row.size()!=3) return false;
        if(gamePracticeHeight(rows,style,practice)>practice) return false;
        GameStatus status{};status.pianoScore=420;status.guitarScore=360;
        GameControl control;GamePanel panel(control);panel.setSize(width,height);
        juce::Image image=panel.createComponentSnapshot(panel.getLocalBounds());juce::Graphics g(image);
        juce::Path outline;outline.addRoundedRectangle(image.getBounds().toFloat(),float(chordlabStyle::choice_height)/2);
        g.reduceClipRegion(outline);g.setColour(juce::Colour(chordlabStyle::game_background));
        g.fillRect(0,4,width,practice-4);
        paintGamePractice(g,{0,0,width,practice},current,events,{},status,false,style);
        // The renderer must never paint into the settings region.
        if(image.getPixelAt(40,practice)!=juce::Colour(chordlabStyle::game_background)) return false;
        if(exportImages && !writeImage(image,output,"dense-"+juce::String(keyCount)+"-keys.png")) return false;
    }
    // In-key transitions are still neutral, unlike real arrivals.
    for(unsigned kind:{1,2,3}) {
        auto current=target(1,1,1,2,"C ionian","V G7","B3(3)");current.kind=kind;
        juce::Image image(juce::Image::ARGB,width,height,true);juce::Graphics g(image);
        paintGamePractice(g,{0,0,width,practice},current,{}, {},{},false,style);
        const auto expected=juce::Colour(kind<3 ? chordlabStyle::choice_button_selected : chordlabStyle::capsule_fifth);
        if(image.getPixelAt(30,138)!=expected) return false;
        if(kind<3 && image.getPixelAt(24+style.chordWidth+9,138)!=juce::Colour(chordlabStyle::capsule_fifth)) return false;
    }
    return true;
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
    if(!densePreview(argc==2 ? juce::File(argv[1]) : juce::File{},style,argc==2)) return 17;
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
    preview[2].kind=1;preview[3].kind=2;
    std::snprintf(preview[2].action,sizeof preview[2].action,"Modulate: destination V7");
    const auto rows=gamePracticeRows(current,preview,trail,false,0);
    if(rows[0].size()!=3 || rows[1].size()!=1 || rows[2].size()!=3 ||
       rows[0][0].state!=GameStepState::Complete || rows[0][1].state!=GameStepState::Current ||
       rows[0][2].state!=GameStepState::Upcoming) return 2;
    auto nextGroup=preview[1];
    if(gamePracticeRows(nextGroup,{},trail,false,0)[0].size()!=1) return 3;
    for(int editorHeight:{560,703,1220}) {
        const auto bounds=gamePanelBounds({914,10,width,editorHeight-20},editorHeight,1212);
        if(bounds.getY()!=20 || editorHeight-bounds.getBottom()!=20 ||
           1212-bounds.getRight()!=20 || bounds.getX()!=914) return 12;
    }
    for(int winner:{0,1,2}) {
        GameStatus status{};status.winner=winner;status.award=86;
        for(bool replaying:{false,true}) for(int instrument:{1,2})
            if(gameAwardText(status,instrument,replaying) !=
                (replaying && winner==instrument ? "+86" : "")) return 13;
        status.award=0;
        if(gameAwardText(status,winner,true).isNotEmpty()) return 14;
    }
    for(int height:{520,663,1180}) {
        panel.setSize(width,height);
        const auto idle=panel.createComponentSnapshot(panel.getLocalBounds());
        if(!idle.isValid()) return 4;
        for(auto point:{juce::Point<int>{0,0},{width-1,0},{0,height-1},{width-1,height-1}})
            if(idle.getPixelAt(point.x,point.y).getAlpha()!=0) return 15;
        if(idle.getPixelAt(0,height/2)!=juce::Colour(chordlabStyle::game_background)) return 16;
        if(idle.getPixelAt(width/2,1)!=juce::Colour(chordlabStyle::game_border) ||
           idle.getPixelAt(width/2,4)!=juce::Colour(chordlabStyle::game_background)) return 10;
        for(int outcome:{0,1,2,3}) {
            GameStatus s{};s.phase=outcome ? 3 : 2;s.remaining=outcome ? 1.8 : 8.6;
            s.winner=outcome==1 ? 1 : outcome==3 ? 2 : 0;s.award=86;s.pianoScore=240;s.guitarScore=180;
            const bool replaying=outcome!=0;
            juce::Image image=panel.createComponentSnapshot(panel.getLocalBounds());
            juce::Graphics g(image);
            juce::Path panelOutline;panelOutline.addRoundedRectangle(image.getBounds().toFloat(),float(chordlabStyle::choice_height)/2);
            g.reduceClipRegion(panelOutline);g.setColour(juce::Colour(chordlabStyle::game_background));g.fillRect(0,4,width,height-182);
            paintGamePractice(g,{0,0,width,height-178},current,preview,trail,s,replaying,style);
            const int start=24;
            if(height>=663 && (image.getPixelAt(20,103)!=juce::Colour(chordlabStyle::choice_button_selected) ||
               image.getPixelAt(20,278)!=juce::Colours::white ||
               image.getPixelAt(start+6,138)!=juce::Colours::black)) return 5;
            const bool hollow=image.getPixelAt(start+16+6,167)==juce::Colours::black;
            if(height>=663 && hollow!=replaying) return 6;
            if(height>=663 && !replaying && image.getPixelAt(start+16+6,167)!=juce::Colour(chordlabStyle::choice_button_selected)) return 10;
            if(height>=663 && image.getPixelAt(start+16+style.chordWidth+9,167)!=juce::Colour(chordlabStyle::capsule_fifth)) return 11;
            const auto result=gamePracticeRows(current,preview,trail,replaying,s.winner);
            if(outcome==2 && result[0][1].state!=GameStepState::Missed) return 7;
            if(argc==2 && height==663 && !writeImage(image,juce::File(argv[1]),
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
