#include "grid.h"
#include "style.h"
#include <cmath>
namespace {
const unsigned colours[] = {beatstyle::kick, beatstyle::snare, beatstyle::hat, beatstyle::clap, beatstyle::uncertain};
const char* names[] = {"A", "B", "C", "D", "Review"};
}
double BeatGrid::displayBeat(const juce::var& e) const {
    const double raw = static_cast<double>(e["beat"]), grid = static_cast<double>(pattern["grid"]);
    if (grid <= 0) return raw;
    const double last = static_cast<double>(pattern["bars"]) * 4.0;
    const double target = std::min(std::round(raw * grid), last * grid - 1.0) / grid;
    return raw + (target - raw) * static_cast<double>(pattern["strength"]);
}
double BeatGrid::beatAtX(float x) const {
    return startBeat + (x-left) / std::max(1.0, static_cast<double>(getWidth()-left-22)) * visibleBars * 4.0;
}
float BeatGrid::xForBeat(double beat) const {
    return left + static_cast<float>((beat-startBeat) / (visibleBars*4.0) * (getWidth()-left-22));
}
double BeatGrid::insertionBeat(float x) const {
    const double end = static_cast<double>(pattern["bars"]) * 4.0;
    if (end <= 0.0) return 0.0;
    return std::clamp(std::round(beatAtX(x)*divisions)/divisions, 0.0, end-1.0/divisions);
}
int BeatGrid::hitEvent(int lane, float x) const {
    int found = -1;
    const double cellWidth = (getWidth()-left-22) / (visibleBars*4.0*divisions);
    double nearest = std::clamp(cellWidth*0.45, 1.0, 7.0);
    if (auto* events = pattern["events"].getArray()) for (int i=0;i<events->size();++i) {
        const auto& event = events->getReference(i);
        const double beat = displayBeat(event);
        if (static_cast<int>(event["class"])!=lane || beat<startBeat || beat>=startBeat+visibleBars*4.0) continue;
        const double distance = std::abs(xForBeat(beat)-x);
        if (distance < nearest) { nearest=distance; found=i; }
    }
    return found;
}
void BeatGrid::paintRuler(juce::Graphics& g) const {
    const int begin=static_cast<int>(std::ceil(startBeat*divisions));
    const int end=static_cast<int>(std::floor((startBeat+visibleBars*4.0)*divisions));
    for (int i=begin;i<=end;++i) {
        const double beat=static_cast<double>(i)/divisions;
        const float x=xForBeat(beat);
        const bool barLine=i%(4*divisions)==0, beatLine=i%divisions==0;
        g.setColour(juce::Colours::white.withAlpha(barLine ? 0.65f : beatLine ? 0.32f : 0.10f));
        g.fillRect(x,static_cast<float>(top),barLine ? 2.0f : 1.0f,static_cast<float>(rowHeight*5-8));
        if (beat>=startBeat+visibleBars*4.0) continue;
        if (barLine) {
            g.setColour(juce::Colours::white); g.setFont(14.0f);
            g.drawText("Bar "+juce::String(i/(4*divisions)+1),static_cast<int>(x)+4,4,80,20,juce::Justification::centredLeft);
        }
        if (beatLine) {
            g.setColour(juce::Colour(beatstyle::muted)); g.setFont(11.0f);
            g.drawText(juce::String((i/divisions)%4+1),static_cast<int>(x)+4,25,24,18,juce::Justification::centredLeft);
        }
    }
}
void BeatGrid::paintEvents(juce::Graphics& g) const {
    juce::Graphics::ScopedSaveState saved(g);
    g.reduceClipRegion(left,top,getWidth()-left-22,rowHeight*5);
    // Small onset markers do not obscure adjacent sixteenth/thirty-second hits.
    const float cell=(getWidth()-left-22)/static_cast<float>(visibleBars*4*divisions);
    const float width=std::clamp(cell*0.65f,2.0f,12.0f);
    if (auto* events=pattern["events"].getArray()) for (const auto& event:*events) {
        const double beat=displayBeat(event);
        const int lane=static_cast<int>(event["class"]);
        if (beat<startBeat || beat>=startBeat+visibleBars*4.0 || lane<0 || lane>4) continue;
        const float height=12.0f+18.0f*static_cast<float>(static_cast<int>(event["velocity"]))/127.0f;
        const float x=xForBeat(beat), y=static_cast<float>(top+lane*rowHeight+24)-height/2;
        g.setColour(juce::Colour(colours[lane])); g.fillRoundedRectangle(x,y,width,height,1.0f);
        g.setColour(juce::Colours::white.withAlpha(0.9f)); g.drawRoundedRectangle(x,y,width,height,1.0f,0.8f);
    }
}
void BeatGrid::paint(juce::Graphics& g) {
    g.setColour(juce::Colour(beatstyle::panel)); g.fillRoundedRectangle(getLocalBounds().toFloat(),16);
    for (int lane=0;lane<5;++lane) {
        const int y=top+lane*rowHeight;
        g.setColour(juce::Colour(colours[lane])); g.fillEllipse(18,static_cast<float>(y+22),10,10);
        g.setColour(juce::Colours::white); g.setFont(14.0f);
        g.drawText(names[lane],38,y,65,rowHeight-8,juce::Justification::centredLeft);
        g.setColour(juce::Colours::white.withAlpha(0.07f)); g.drawHorizontalLine(y+rowHeight-8,left,static_cast<float>(getWidth()-22));
    }
    paintRuler(g); paintEvents(g);
}
void BeatGrid::mouseDown(const juce::MouseEvent& event) {
    if (pattern.isVoid() || event.x < left || event.x > getWidth() - 22 || event.y < top) return;
    const int lane = (event.y - top) / rowHeight;
    if (lane > 4) return;
    const double raw = beatAtX(static_cast<float>(event.x));
    if (raw >= static_cast<double>(pattern["bars"])*4.0) return;
    const double beat = insertionBeat(static_cast<float>(event.x));
    auto* events = pattern.getDynamicObject()->getProperty("events").getArray();
    if (!events) return;
    const int found = hitEvent(lane,static_cast<float>(event.x));
    if (found < 0) {
        if (event.mods.isPopupMenu() || events->size() >= 2048) return;
        auto* item = new juce::DynamicObject();
        item->setProperty("beat", beat); item->setProperty("source_sample", 0);
        item->setProperty("class", lane); item->setProperty("velocity", 100); item->setProperty("confidence", 1.0);
        events->add(juce::var(item)); if (changed) changed(); repaint(); return;
    }
    juce::PopupMenu menu;
    menu.addSectionHeader("Event: " + juce::String(static_cast<double>((*events)[found]["beat"]), 3) + " beats");
    menu.addItem(1,"Move to A"); menu.addItem(2,"Move to B"); menu.addItem(3,"Move to C");
    menu.addItem(4,"Move to D"); menu.addItem(9,"Mark for review (no export)"); menu.addSeparator();
    menu.addItem(5,"Velocity 60"); menu.addItem(6,"Velocity 100"); menu.addItem(7,"Velocity 127");
    menu.addItem(8,"Delete event");
    juce::Component::SafePointer<BeatGrid> safe(this);
    // Capture the exact object, not an index that could refer to a later analysis result.
    const juce::var selected = (*events)[found];
    menu.showMenuAsync(juce::PopupMenu::Options().withTargetComponent(this), [safe, selected](int choice) {
        if (!safe || choice == 0) return;
        auto* list = safe->pattern["events"].getArray(); if (!list) return;
        const int index = list->indexOf(selected); if (index < 0) return;
        if (choice == 8) list->remove(index);
        else if (auto* item = selected.getDynamicObject()) {
            if (choice == 9) item->setProperty("class", 4);
            else if (choice <= 4) item->setProperty("class", choice - 1);
            else item->setProperty("velocity", choice == 5 ? 60 : choice == 6 ? 100 : 127);
        }
        if (safe->changed) safe->changed(); safe->repaint();
    });
}
