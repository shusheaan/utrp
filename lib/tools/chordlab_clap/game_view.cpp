#include "game_view.h"
#include "control_style.h"

GameRows gamePracticeRows(const GameTarget& current,const std::deque<GameTarget>& preview,
                         const std::deque<GameTrailStep>& trail,bool replaying,int winner)
{
    GameRows result;
    for(const auto& step:trail)
        if(step.target.group==current.group)
            result[0].push_back({step.target,step.success ? GameStepState::Complete : GameStepState::Missed});
    const auto state=!replaying ? GameStepState::Current :
        winner ? GameStepState::Complete : GameStepState::Missed;
    result[0].push_back({current,state});
    size_t row=0;
    for(const auto& target:preview) {
        if(target.group!=result[row].back().target.group && ++row==result.size()) break;
        result[row].push_back({target,GameStepState::Upcoming});
    }
    return result;
}

GameCapsuleStyle gameCapsuleStyle(int leftWidth,int panelWidth,float fontHeight)
{
    using namespace chordlabStyle;
    const int inset=2*selection_inset;
    const int reserve=2*margin+3*size+2*gap+key_gap;
    const int keyWidth=std::min((leftWidth-reserve)/12-inset,84);
    const int available=panelWidth-28-32;
    return {keyWidth,std::min((leftWidth-36)/7-inset,available),fontHeight};
}

namespace {
using namespace chordlabStyle;
void text(juce::Graphics& g,const juce::String& label,juce::Rectangle<int> area,
          float size,juce::Colour color,bool centered=false,bool pointSize=false)
{
    auto options=juce::FontOptions("DejaVu Sans",size,juce::Font::plain).withMetricsKind(juce::TypefaceMetricsKind::legacy);
    // JSFX theme typography is point-sized; LICE applies its own line-height correction.
    if(pointSize) options=options.withPointHeight(size);
    g.setFont(juce::Font(options));
    g.setColour(color);
    g.drawFittedText(label,area,centered ? juce::Justification::centred : juce::Justification::centredLeft,1,0.8f);
}
juce::Colour color(int role)
{
    const unsigned colors[]{capsule_root,capsule_third,capsule_fifth,capsule_seventh};
    return juce::Colour(colors[std::clamp(role,0,3)]);
}
juce::String key(const GameTarget& t)
{
    return juce::String::fromUTF8(t.keyLabel).replace("ionian","major").replace("aeolian","minor");
}
void badge(juce::Graphics& g,juce::Rectangle<int> area,const juce::String& label,bool future,float fontHeight)
{
    g.setColour(future ? juce::Colours::white : juce::Colour(choice_button_selected));
    g.fillRoundedRectangle(area.toFloat(),float(area.getHeight())/2);
    text(g,label,area.reduced(3,0),fontHeight,future ? juce::Colour(choice_button_selected) : juce::Colours::white,true,true);
}
void chord(juce::Graphics& g,const GameViewStep& step,juce::Rectangle<int> area,float fontHeight)
{
    const auto state=step.state;
    const bool active=state==GameStepState::Current, done=state==GameStepState::Complete;
    const bool missed=state==GameStepState::Missed;
    const int relativeRoles[]{0,1,1,2,2,3,3};
    const int rootDegree=(step.target.rootLetter-step.target.scaleLetters[0]+7)%7;
    const auto degreeColor=color(step.target.paletteRole);
    const bool chromatic=std::any_of(step.target.notes,step.target.notes+step.target.count,[&](int note) {
        return std::none_of(std::begin(step.target.scale),std::end(step.target.scale),[&](int pc){return note%12==pc;});
    });
    const bool neutral=step.target.kind==1 || chromatic;
    const auto fill=neutral ? juce::Colour(choice_button_selected) : degreeColor;
    const float radius=float(area.getHeight())/2;
    g.setColour(active ? fill : done || missed ? juce::Colours::black : fill.darker(0.8f));
    g.fillRoundedRectangle(area.toFloat(),radius);
    g.setColour(active ? juce::Colours::white : missed ? juce::Colour(game_error) : fill);
    g.drawRoundedRectangle(area.toFloat(),radius,1.0f);
    const auto ink=done || missed ? juce::Colour(game_muted) : juce::Colours::white;
    const auto label=juce::String::fromUTF8(step.target.capsule)+"/"+juce::String::fromUTF8(step.target.bass);
    text(g,label,area.reduced(3,0),fontHeight,ink,true,true);
    if(neutral) {
        g.setColour(step.target.kind==1 ? degreeColor : color(relativeRoles[rootDegree]));
        g.fillEllipse(float(area.getRight()+6),float(area.getCentreY()-3),6,6);
    }
    if(missed) {
        g.setColour(juce::Colour(game_error));
        g.drawLine(float(area.getRight()-8),float(area.getY()+3),float(area.getRight()-3),float(area.getY()+8),1);
        g.drawLine(float(area.getRight()-3),float(area.getY()+3),float(area.getRight()-8),float(area.getY()+8),1);
    }
}
juce::String modulationMethod(const std::vector<GameViewStep>& row)
{
    const auto tonic=juce::String(row.back().target.minor ? "i" : "I");
    for(const auto& step:row) {
        const auto& t=step.target;
        const auto action=juce::String::fromUTF8(t.action);
        if(action.contains("shared"))
            return juce::String::fromUTF8(t.reason).upToFirstOccurrenceOf(";",false,false)+juce::String::fromUTF8(" → V7 → ")+tonic;
        if(action.contains("diminished")) return juce::String::fromUTF8("Diminished 7th pivot → V7 → ")+tonic;
        if(action.contains("destination")) return juce::String::fromUTF8("Destination V7 → ")+tonic;
        if(action.contains("same tonic")) return juce::String::fromUTF8("Same tonic → new mode");
    }
    return {};
}
int progressionRow(juce::Graphics* graphics,const std::vector<GameViewStep>& row,
                   int y,int index,bool showKey,const GameCapsuleStyle& style)
{
    if(row.empty()) return y;
    constexpr int height=choice_height-2*selection_inset;
    if(showKey) {
        if(graphics) badge(*graphics,{14,y,style.keyWidth,height},key(row.front().target),index!=0,style.fontHeight);
        y+=height+4;
        const auto method=modulationMethod(row);
        if(method.isNotEmpty()) {
            if(graphics) text(*graphics,method,{14,y,260,18},11,juce::Colour(game_muted));
            y+=20;
        }
    }
    for(size_t i=0;i<row.size();++i) {
        const int x=24+int(i)*16;
        if(graphics) chord(*graphics,row[i],{x,y,style.chordWidth,height},style.fontHeight);
        y+=height+4;
    }
    return y+8;
}
void scoreboard(juce::Graphics& g,juce::Rectangle<int> area,const GameStatus& s,bool replaying)
{
    const int width=(area.getWidth()-10)/2;
    for(int instrument=1;instrument<=2;++instrument) {
        auto box=juce::Rectangle<int>(area.getX()+(instrument-1)*(width+10),area.getY(),width,44);
        g.setColour(juce::Colour(game_border).withAlpha(0.3f));g.fillRoundedRectangle(box.toFloat(),10);
        const bool won=replaying && s.winner==instrument;
        if(won) {g.setColour(juce::Colour(game_reason));g.drawRoundedRectangle(box.toFloat(),10,1);}
        text(g,instrument==1 ? "PIANO" : "GUITAR",{box.getX()+10,box.getY()+5,width-20,16},10,juce::Colour(game_muted));
        text(g,juce::String(instrument==1 ? s.pianoScore : s.guitarScore),
             {box.getX()+10,box.getY()+22,width-72,20},20,juce::Colour(game_text));
        text(g,won ? juce::String::fromUTF8("✓ +")+juce::String(s.award) : "",
             {box.getRight()-58,box.getY()+22,48,24},14,juce::Colour(won ? game_reason : game_muted),true);
    }
}
}

int gamePracticeHeight(const GameRows& groups,const GameCapsuleStyle& style)
{
    int y=64; uint32_t lastVisit=groups[0].empty() ? 0 : groups[0].front().target.visit;
    for(int i=0;i<3;++i) {
        if(groups[size_t(i)].empty()) continue;
        const auto visit=groups[size_t(i)].front().target.visit;
        y=progressionRow(nullptr,groups[size_t(i)],y,i,i==0 || visit!=lastVisit,style);
        lastVisit=visit;
    }
    return y;
}
void paintGamePractice(juce::Graphics& g,juce::Rectangle<int> bounds,const GameTarget& current,
    const std::deque<GameTarget>& preview,const std::deque<GameTrailStep>& trail,
    const GameStatus& status,bool replaying,const GameCapsuleStyle& style,int scroll)
{
    scoreboard(g,{14,8,bounds.getWidth()-28,44},status,replaying);
    if(!current.count) return;
    const auto groups=gamePracticeRows(current,preview,trail,replaying,status.winner);
    juce::Graphics::ScopedSaveState saved(g);
    g.reduceClipRegion(bounds.withTrimmedTop(60));
    g.addTransform(juce::AffineTransform::translation(0,float(-scroll)));
    int y=64; uint32_t lastVisit=current.visit;
    for(int i=0;i<3;++i) {
        if(groups[size_t(i)].empty()) continue;
        const auto visit=groups[size_t(i)].front().target.visit;
        y=progressionRow(&g,groups[size_t(i)],y,i,i==0 || visit!=lastVisit,style);
        lastVisit=visit;
    }
}
