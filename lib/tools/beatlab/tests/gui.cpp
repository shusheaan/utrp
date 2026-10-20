#include "../plugin/editor.h"
#include "../plugin/ffi.h"
#include <juce_gui_extra/juce_gui_extra.h>
#include <chrono>
#include <iostream>
#include <thread>
#include <stdexcept>
void require(bool value,const char* message) { if (!value) throw std::runtime_error(message); }
void testDenseGrid(const juce::var& source) {
    BeatGrid grid; grid.setSize(968,312); grid.pattern=source.clone();
    auto* object=grid.pattern.getDynamicObject();
    object->setProperty("bars",4); object->setProperty("grid",0);
    juce::Array<juce::var> notes;
    for (int i=0;i<256;++i) {
        auto* event=new juce::DynamicObject();
        event->setProperty("beat",i/16.0); event->setProperty("class",0);
        event->setProperty("velocity",100); event->setProperty("confidence",1.0);
        event->setProperty("source_sample",0); notes.add(juce::var(event));
    }
    object->setProperty("events",notes);
    const auto original=juce::JSON::toString(grid.pattern);
    for (int divisions : {4,6,8,12,16}) for (int bars : {1,2,4}) {
        grid.divisions=divisions; grid.visibleBars=bars;
        grid.startBeat=16.0-bars*4.0;
        for (int i=0;i<bars*4*divisions;++i) {
            const double beat=grid.startBeat+static_cast<double>(i)/divisions;
            const float x=grid.xForBeat(beat);
            require(std::abs(grid.beatAtX(x)-beat)<0.00001,"Zoom/scroll beat coordinate roundtrip");
            require(std::abs(grid.insertionBeat(x)-beat)<0.00001,"Dense edit-grid insertion including bar four");
        }
    }
    grid.visibleBars=4; grid.startBeat=0; grid.divisions=16;
    for (int i=0;i<256;++i)
        require(grid.hitEvent(0,grid.xForBeat(i/16.0))==i,"All 256 onset markers individually addressable");
    require(juce::JSON::toString(grid.pattern)==original,"View/grid/zoom never changes pattern");
    auto event=notes[0].clone(); event.getDynamicObject()->setProperty("beat",0.113);
    require(std::abs(grid.displayBeat(event)-0.113)<1e-12,"Off retains microtiming");
    for (int division : {8,12,16}) {
        object->setProperty("grid",division); object->setProperty("strength",1.0);
        char* raw=beatlab_midi(juce::JSON::toString(grid.pattern).toRawUTF8());
        auto result=juce::JSON::parse(juce::String::fromUTF8(raw)); beatlab_free(raw);
        require(static_cast<bool>(result["ok"]),"Dense grid accepted by Rust MIDI export");
    }
}
void testFourBarInput(juce::AudioProcessorEditor& editor, BeatProcessor& processor, const juce::String& validWav) {
    juce::TemporaryFile temporary(".wav");
    auto stream=temporary.getFile().createOutputStream(); require(stream!=nullptr,"Short fixture stream");
    juce::WavAudioFormat format;
    std::unique_ptr<juce::AudioFormatWriter> writer(format.createWriterFor(stream.get(),48000,1,16,{},0));
    require(writer!=nullptr,"Short fixture writer"); stream.release();
    juce::AudioBuffer<float> silence(1,48000); silence.clear();
    require(writer->writeFromAudioSampleBuffer(silence,0,48000),"Short fixture write"); writer.reset();
    const auto before=juce::JSON::toString(processor.getPattern());
    auto& drop=dynamic_cast<juce::FileDragAndDropTarget&>(editor);
    drop.filesDropped({temporary.getFile().getFullPathName()},0,0);
    juce::Timer::callPendingTimersSynchronously();
    bool reported=false;
    for (auto* child:editor.getChildren()) if (auto* label=dynamic_cast<juce::Label*>(child))
        reported=reported || label->getText().contains("Expected exactly 4 bars");
    require(reported,"Wrong-length audio explicitly rejected");
    require(juce::JSON::toString(processor.getPattern())==before,"No trim/padding silently changes pattern");
    drop.filesDropped({validWav},0,0);
    for (int i=0;i<60;++i) { std::this_thread::sleep_for(std::chrono::milliseconds(20)); juce::Timer::callPendingTimersSynchronously(); }
    require(static_cast<int>(processor.getPattern()["bars"])==4,"Valid four-bar take still accepted");
}
class TestPlayHead final : public juce::AudioPlayHead {
public:
    juce::Optional<PositionInfo> getPosition() const override {
        PositionInfo info; info.setBpm(137.125); info.setTimeSignature(TimeSignature{4,4});
        info.setIsPlaying(false); return info;
    }
};
void testRecordingFlow() {
    BeatProcessor processor; TestPlayHead clock; processor.setPlayHead(&clock);
    processor.prepareToPlay(8000,257); processor.inputChannel.store(1);
    std::unique_ptr<juce::AudioProcessorEditor> editor(processor.createEditor());
    juce::TextButton* record=nullptr;
    for (auto* child:editor->getChildren()) if (auto* button=dynamic_cast<juce::TextButton*>(child))
        if (button->getButtonText()=="Record") record=button;
    require(record!=nullptr,"Record control exists"); record->onClick();
    juce::AudioBuffer<float> audio(2,257); juce::MidiBuffer midi;
    std::vector<float> expected;
    const int start=static_cast<int>(std::llround(4*60*8000/137.125));
    const int end=start+static_cast<int>(std::llround(16*60*8000/137.125));
    for (int block=0;block<(end+256)/257;++block) {
        for (int i=0;i<257;++i) {
            const int position=block*257+i;
            const double time=(position%2000)/8000.0;
            const float sample=static_cast<float>(0.7*std::sin(6.28318530718*100*time)*std::exp(-time*60));
            audio.setSample(0,i,0.5f); audio.setSample(1,i,sample);
            if (position>=start && position<end) expected.push_back(sample);
        }
        processor.processBlock(audio,midi);
    }
    require(!processor.recorder.active(),"Once finishes even when Bitwig transport is stopped");
    require(processor.hostBpm.load()==137.125,"Host BPM overrides manual BPM");
    juce::MemoryBlock immediateSave; processor.getStateInformation(immediateSave);
    require(processor.getSource().audio==expected,"Host save collects a completed take even before the UI timer");
    for (int i=0;i<80;++i) { std::this_thread::sleep_for(std::chrono::milliseconds(20)); juce::Timer::callPendingTimersSynchronously(); }
    const auto source=processor.getSource();
    require(source.audio==expected,"Selected R input, exact sample boundaries, click excluded");
    require(source.matched && source.bpm==137.125,"Capture automatically analyzed");
    require(processor.getPattern()["events"].getArray()!=nullptr
        && processor.getPattern()["events"].getArray()->size()>0,"Recording produces editable MIDI events");
    processor.analysisGateDb.store(-45);
    juce::MemoryBlock state; processor.getStateInformation(state);
    BeatProcessor restored; restored.setStateInformation(state.getData(),static_cast<int>(state.getSize()));
    require(restored.analysisGateDb.load()==-45,"Gate persists across host state reload");
    auto invalidGate=juce::JSON::parse(juce::String::fromUTF8(static_cast<const char*>(state.getData()),static_cast<int>(state.getSize())));
    invalidGate.getDynamicObject()->setProperty("gate_db",-100);
    auto invalidText=juce::JSON::toString(invalidGate);
    restored.setStateInformation(invalidText.toRawUTF8(),static_cast<int>(invalidText.getNumBytesAsUTF8()));
    require(restored.analysisGateDb.load()==-45,"Invalid Gate state rejected");
    require(restored.getSource().audio==expected,"Recorded audio persists in host state without WAV export");
    require(restored.getSource().matched,"Recorded pattern match persists");
    editor.reset(); processor.releaseResources();
}
int main(int argc,char** argv) {
    require(argc==3,"Usage: gui_test demo.json screenshot.png");
    juce::ScopedJuceInitialiser_GUI init;
    testRecordingFlow();
    BeatProcessor processor;
    processor.prepareToPlay(48000,256);
    const auto source=juce::File(argv[1]).loadFileAsString();
    processor.setStateInformation(source.toRawUTF8(),static_cast<int>(source.getNumBytesAsUTF8()));
    require(processor.getPattern().isObject(),"Restore valid Rust state");
    processor.setStateInformation("{}",2);
    require(processor.getPattern().isObject(),"Reject corrupt state without destroying existing state");
    std::unique_ptr<juce::AudioProcessorEditor> editor(processor.createEditor());
    juce::TextButton* demo=nullptr;
    for (auto* child:editor->getChildren()) if (auto* button=dynamic_cast<juce::TextButton*>(child))
        if (button->getButtonText()=="Example") demo=button;
    require(demo!=nullptr,"Example button exists");
    int mappingCount = 0;
    for (auto* child:editor->getChildren()) {
        if (auto* button=dynamic_cast<juce::TextButton*>(child))
            require(button->getButtonText()!="Save Take", "No manual WAV save needed");
        if (auto* combo=dynamic_cast<juce::ComboBox*>(child))
            if (combo->getNumItems()==128) ++mappingCount;
    }
    require(mappingCount==4,"Exactly four MIDI mappings");
    demo->onClick();
    for (int i=0;i<60;++i) { std::this_thread::sleep_for(std::chrono::milliseconds(20)); juce::Timer::callPendingTimersSynchronously(); }
    auto pattern=processor.getPattern();
    testDenseGrid(pattern);
    require(pattern["events"].getArray() && pattern["events"].getArray()->size()==64,"UI demo analyzed and committed");
    juce::MemoryBlock state; processor.getStateInformation(state);
    BeatProcessor restored; restored.setStateInformation(state.getData(),static_cast<int>(state.getSize()));
    require(restored.getSource().audio==processor.getSource().audio,"Source PCM roundtrip without external WAV");
    require(restored.getSource().matched,"Restored source matches MIDI");
    require(juce::JSON::toString(restored.getPattern())==juce::JSON::toString(pattern),"Plugin state roundtrip");
    juce::AudioBuffer<float> buffer(2,256); juce::MidiBuffer midi;
    for (int channel=0; channel<2; ++channel)
        for (int sample=0; sample<256; ++sample) buffer.setSample(channel,sample,0.5f);
    processor.processBlock(buffer,midi);
    require(buffer.getMagnitude(0,256)==0,"No unsolicited output");
    juce::AudioBuffer<float> empty;
    processor.processBlock(empty,midi);
    char* midiJson=beatlab_midi(juce::JSON::toString(pattern).toRawUTF8());
    const auto result=juce::JSON::parse(juce::String::fromUTF8(midiJson)); beatlab_free(midiJson);
    require(static_cast<bool>(result["ok"]),"Rust MIDI export");
    juce::MemoryBlock bytes;
    for (const auto& byte:*result["value"].getArray()) {
        const auto value=static_cast<unsigned char>(static_cast<int>(byte)); bytes.append(&value,1);
    }
    juce::MemoryInputStream input(bytes,false); juce::MidiFile file;
    require(file.readFrom(input),"Independent JUCE MIDI parser");
    require(file.getNumTracks()==1 && file.getTimeFormat()==960,"SMF track and PPQ");
    int notes=0;
    for (const auto* event:*file.getTrack(0))
        if (event->message.isNoteOn()) { ++notes; require(event->message.getChannel()==10,"Drum MIDI channel"); }
    require(notes==64,"Export contains all demo notes");
    require(file.getLastTimestamp()==15360,"Exact four-bar loop length");
    auto* drop = dynamic_cast<juce::FileDragAndDropTarget*>(editor.get());
    require(drop!=nullptr,"File drop target");
    require(!drop->isInterestedInFileDrag({"/tmp/unsupported.bwclip"}),"Reject private clip format");
    const auto wav=juce::File(argv[1]).withFileExtension("wav").getFullPathName();
    require(drop->isInterestedInFileDrag({wav}),"Accept single WAV");
    drop->filesDropped({wav},0,0);
    for (int i=0;i<60;++i) { std::this_thread::sleep_for(std::chrono::milliseconds(20)); juce::Timer::callPendingTimersSynchronously(); }
    require(processor.getPattern()["events"].getArray()->size()==64,"WAV auto-analyzed without Record or Analyze click");
    require(static_cast<int>(processor.getPattern()["version"])==2,"Four-category state version");
    auto legacy=pattern.clone();
    legacy.getDynamicObject()->setProperty("version",1);
    legacy.getDynamicObject()->setProperty("notes",juce::Array<juce::var>{36,38,42});
    legacy["events"].getArray()->getReference(0).getDynamicObject()->setProperty("class",3);
    const auto legacyText=juce::JSON::toString(legacy);
    BeatProcessor old; old.setStateInformation(legacyText.toRawUTF8(),static_cast<int>(legacyText.getNumBytesAsUTF8()));
    std::unique_ptr<juce::AudioProcessorEditor> oldEditor(old.createEditor());
    bool migrated=false;
    for (auto* child:oldEditor->getChildren()) if (auto* grid=dynamic_cast<BeatGrid*>(child))
        migrated=static_cast<int>(grid->pattern["events"][0]["class"])==4 && grid->pattern["notes"].getArray()->size()==4;
    require(migrated,"Legacy Review does not become audible D");
    oldEditor.reset();
    testFourBarInput(*editor,processor,wav);
    const auto screenshot=editor->createComponentSnapshot(editor->getLocalBounds(),true,1.5f);
    auto stream=juce::File(argv[2]).createOutputStream(); require(stream!=nullptr,"Screenshot writable");
    juce::PNGImageFormat png; require(png.writeImageToStream(screenshot,*stream),"Screenshot encoding");
    editor.reset(); processor.releaseResources();
    std::cout << "UI demo, Rust FFI, state validation, state roundtrip, no feedback, MIDI decoding, screenshot PASS\n";
}
