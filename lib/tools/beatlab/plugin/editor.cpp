#include "editor.h"
#include "ffi.h"
#include "style.h"
#include <random>

BeatLook::BeatLook() {
    setColour(juce::TextButton::buttonColourId, juce::Colour(beatstyle::button));
    setColour(juce::TextButton::textColourOffId, juce::Colours::white);
    setColour(juce::ComboBox::backgroundColourId, juce::Colour(beatstyle::panel));
    setColour(juce::ComboBox::textColourId, juce::Colours::white);
    setColour(juce::PopupMenu::backgroundColourId, juce::Colour(beatstyle::panel));
    setColour(juce::PopupMenu::textColourId, juce::Colours::white);
    setColour(juce::Slider::textBoxTextColourId, juce::Colours::white);
    setColour(juce::Slider::textBoxOutlineColourId, juce::Colours::transparentBlack);
    setColour(juce::Slider::thumbColourId, juce::Colour(beatstyle::hat));
    setColour(juce::Slider::trackColourId, juce::Colour(beatstyle::muted));
}
void BeatLook::drawButtonBackground(juce::Graphics& g, juce::Button& b, const juce::Colour& c, bool over, bool down) {
    g.setColour((down ? c.brighter(0.2f) : over ? c.brighter(0.1f) : c).withAlpha(b.isEnabled() ? 1.0f : 0.4f));
    g.fillRoundedRectangle(b.getLocalBounds().toFloat().reduced(2), (b.getHeight() - 4) / 2.0f);
}
void BeatLook::drawComboBox(juce::Graphics& g,int w,int h,bool,int,int,int,int,juce::ComboBox&) {
    g.setColour(juce::Colour(beatstyle::panel)); g.fillRoundedRectangle(1,1,static_cast<float>(w-2),static_cast<float>(h-2),(h-2)/2.0f);
    g.setColour(juce::Colour(beatstyle::muted));
    juce::Path arrow; arrow.addTriangle(static_cast<float>(w-18),h*0.43f,static_cast<float>(w-10),h*0.43f,static_cast<float>(w-14),h*0.58f); g.fillPath(arrow);
}
BeatEditor::BeatEditor(BeatProcessor& p) : AudioProcessorEditor(p), processor(p), waveform(p.recorder) {
    setLookAndFeel(&look); setSize(1020, 870);
    for (auto* button : {&import,&analyze,&demo,&exportMidi}) addAndMakeVisible(button);
    for (auto* combo : {&quantize,&displayGrid,&zoom,&channel}) addAndMakeVisible(combo);
    for (auto* slider : {&bpm,&gate,&strength}) {
        addAndMakeVisible(slider); slider->setSliderStyle(juce::Slider::LinearHorizontal);
        slider->setTextBoxStyle(juce::Slider::TextBoxRight, false, 55, 24);
    }
    for (auto* label : {&title,&subtitle,&status,&bpmLabel,&barLabel,&gateLabel,&gridLabel,&strengthLabel,&mappingLabel}) {
        addAndMakeVisible(label); label->setColour(juce::Label::textColourId, juce::Colours::white);
    }
    title.setText("BEAT LAB",juce::dontSendNotification); title.setFont(juce::FontOptions(23.0f));
    subtitle.setText("Record 4 bars  >  A / B / C / D  >  MIDI file    |    Host BPM / local recording clock",juce::dontSendNotification);
    subtitle.setColour(juce::Label::textColourId,juce::Colour(beatstyle::muted));
    bpmLabel.setText("BPM",juce::dontSendNotification); barLabel.setText("Bars",juce::dontSendNotification);
    gateLabel.setText("Gate dB",juce::dontSendNotification); gridLabel.setText("Quantize",juce::dontSendNotification);
    strengthLabel.setText("Quantize %",juce::dontSendNotification); mappingLabel.setText("MIDI mapping",juce::dontSendNotification);
    bpm.setRange(40,240,0); bpm.setNumDecimalPlacesToDisplay(3); bpm.setValue(120); gate.setRange(-60,-12,1); gate.setValue(processor.analysisGateDb.load());
    gate.setTooltip("Detection threshold after DC removal. More negative = quieter hits, but potentially more noise. Click Reanalyze.");
    strength.setRange(0,100,1); strength.setValue(100);
    quantize.addItem("Off",1); quantize.addItem("1/8",2); quantize.addItem("1/8 triplet",3);
    quantize.addItem("1/16",4); quantize.addItem("1/16 triplet",6); quantize.addItem("1/32",8); quantize.addItem("1/32 triplet",12); quantize.addItem("1/64",16); quantize.setSelectedId(1);
    channel.addItem("Input L / mono",1); channel.addItem("Input R",2); channel.setSelectedId(1);
    channel.onChange = [this] { processor.inputChannel.store(channel.getSelectedId()-1); };
    const char* prefixes[] = {"A", "B", "C", "D"};
    for (int lane = 0; lane < 4; ++lane) {
        auto& combo = mappings[static_cast<std::size_t>(lane)]; addAndMakeVisible(combo);
        for (int note = 0; note <= 127; ++note) {
            juce::String label = juce::String(prefixes[lane]) + "  /  " + juce::String(note);
            if (note == 36) label += "  Kick"; if (note == 38) label += "  Snare";
            if (note == 39) label += "  Clap"; if (note == 42) label += "  Closed Hat"; if (note == 46) label += "  Open Hat";
            combo.addItem(label,note+1);
        }
        combo.setSelectedId((lane == 0 ? 36 : lane == 1 ? 38 : lane == 2 ? 42 : 39)+1);
        combo.onChange = [this] { storePattern(); };
        auto& button=hear[static_cast<std::size_t>(lane)];
        addAndMakeVisible(button); button.setButtonText("Hear");
        button.onClick=[this,lane] {
            if (!sourceMatchesPattern) return;
            if (auto* events=grid.pattern["events"].getArray()) for (const auto& event:*events) {
                if (static_cast<int>(event["class"])==lane) {
                    const auto source=static_cast<std::size_t>(static_cast<juce::int64>(event["source_sample"]));
                    processor.audition(take,takeRate,source); break;
                }
            }
        };
    }
    addAndMakeVisible(grid); grid.changed = [this] { storePattern(); };
    configureGridControls();
    quantize.onChange = [this] { storePattern(); }; strength.onValueChange = [this] { storePattern(); };
    import.onClick = [this] { importWav(); }; analyze.onClick = [this] { startAnalysis(); };
    demo.onClick = [this] { loadDemo(); }; exportMidi.onClick = [this] { exportFile(); };
    configureRecording();
    loadPattern(processor.getPattern());
    processor.collectRecording();
    const auto restored=processor.getSource();
    if (!restored.audio.empty()) {
        take=restored.audio; takeRate=restored.rate; takeBpm=restored.bpm;
        bpm.setValue(takeBpm,juce::dontSendNotification);
        sourceMatchesPattern=restored.matched; waveform.setAudio(take);
    }
    bpm.onValueChange = [this] {
        if (take.empty() && grid.pattern.isObject()) { bpm.setValue(static_cast<double>(grid.pattern["bpm"]),juce::dontSendNotification); setStatus("Load source audio to change analysis BPM."); return; }
        if (!take.empty()) { sourceMatchesPattern = false; setStatus("BPM changed. Click Reanalyze to replace the current pattern."); }
    };
    gate.onValueChange = [this] {
        processor.analysisGateDb.store(gate.getValue());
        if (!take.empty()) { sourceMatchesPattern = false; setStatus("Gate changed. Click Reanalyze to replace the current pattern."); }
    };
    setStatus("Select microphone input on this track and enable monitoring. Record: 4-beat count-in, then 4 bars.");
    seenRecording=processor.recordingRevision.load();
    if (!take.empty() && !sourceMatchesPattern) startAnalysis();
    startTimerHz(15);
}
void BeatEditor::configureGridControls() {
    displayGrid.addItem("View grid: 1/16",4); displayGrid.addItem("View grid: 1/32",8);
    displayGrid.addItem("View grid: 1/16 triplet",6); displayGrid.addItem("View grid: 1/32 triplet",12);
    displayGrid.addItem("View grid: 1/64",16); displayGrid.setSelectedId(4);
    displayGrid.onChange=[this] { grid.divisions=displayGrid.getSelectedId(); grid.repaint(); };
    zoom.addItem("Zoom: 4 bars",4); zoom.addItem("Zoom: 2 bars",2); zoom.addItem("Zoom: 1 bar",1);
    addAndMakeVisible(pan); pan.setSliderStyle(juce::Slider::LinearHorizontal);
    pan.setTextBoxStyle(juce::Slider::NoTextBox,false,0,0);
    pan.setTooltip("Scroll through the four-bar phrase when zoomed in. Does not change notes.");
    pan.onValueChange=[this] { grid.startBeat=pan.getValue(); grid.repaint(); };
    zoom.onChange=[this] {
        grid.visibleBars=zoom.getSelectedId();
        const double maximum=std::max(16.0,static_cast<double>(grid.pattern["bars"])*4.0)-grid.visibleBars*4.0;
        pan.setRange(0.0,std::max(0.25,maximum),0.25); pan.setEnabled(maximum>0.0);
        pan.setValue(std::min(pan.getValue(),maximum),juce::dontSendNotification);
        grid.startBeat=pan.getValue(); grid.repaint();
    };
    zoom.setSelectedId(4,juce::sendNotificationSync);
}
BeatEditor::~BeatEditor() {
    stopTimer(); if (pending.valid()) { pending.wait(); finishAnalysis(); }
    setLookAndFeel(nullptr);
}
void BeatEditor::paint(juce::Graphics& g) {
    g.fillAll(juce::Colour(beatstyle::background));

}
void BeatEditor::resized() {
    title.setBounds(26,16,180,35); subtitle.setBounds(26,51,950,25);
    import.setBounds(26,90,140,34); analyze.setBounds(172,90,130,34);
    exportMidi.setBounds(804,90,190,34); demo.setBounds(884,815,110,30);
    bpmLabel.setBounds(26,136,42,30); bpm.setBounds(66,136,145,30);
    barLabel.setBounds(222,136,120,30);
    gateLabel.setBounds(344,136,65,30); gate.setBounds(408,136,170,30); channel.setBounds(615,136,175,30);
    record.setBounds(310,90,92,34); stop.setBounds(408,90,76,34);
    recordMode.setBounds(492,90,188,34); click.setBounds(690,90,100,34);
    clockStatus.setBounds(26,174,968,24); waveform.setBounds(26,202,968,115);
    mappingLabel.setBounds(26,324,968,20);
    for (int i=0;i<4;++i) {
        mappings[static_cast<std::size_t>(i)].setBounds(26+i*242,349,178,30);
        hear[static_cast<std::size_t>(i)].setBounds(208+i*242,349,52,30);
    }
    displayGrid.setBounds(26,428,200,30); zoom.setBounds(240,428,170,30); pan.setBounds(425,428,565,30);
    gridLabel.setBounds(26,390,75,30); quantize.setBounds(104,390,155,30);
    strengthLabel.setBounds(280,390,95,30); strength.setBounds(380,390,220,30);
    grid.setBounds(26,470,968,312); status.setBounds(26,795,840,54);
}
void BeatEditor::setStatus(const juce::String& text) { status.setText(text,juce::dontSendNotification); }
void BeatEditor::loadPattern(const juce::var& pattern) {
    auto current = pattern.clone();
    if (current.isObject() && static_cast<int>(current["version"]) == 1) {
        auto* object = current.getDynamicObject();
        auto notes = *current["notes"].getArray(); notes.add(39);
        object->setProperty("notes", notes); object->setProperty("version", 2);
        if (auto* events = current["events"].getArray()) for (auto& event : *events)
            if (static_cast<int>(event["class"]) == 3) event.getDynamicObject()->setProperty("class", 4);
    }
    grid.pattern = current;
    const int count = current.isObject() ? static_cast<int>(current["bars"]) : 4;
    zoom.setSelectedId(4,juce::sendNotificationSync);
    if (current.isObject()) {
        bpm.setValue(static_cast<double>(current["bpm"]),juce::dontSendNotification);
        takeBars = count;
        quantize.setSelectedId(static_cast<int>(current["grid"]) == 0 ? 1 : static_cast<int>(current["grid"]),juce::dontSendNotification);
        strength.setValue(static_cast<double>(current["strength"])*100,juce::dontSendNotification);
        for (int i=0;i<4;++i) mappings[static_cast<std::size_t>(i)].setSelectedId(static_cast<int>(current["notes"][i])+1,juce::dontSendNotification);
    }
    barLabel.setText(juce::String(count) + " bars", juce::dontSendNotification);
    grid.repaint();
}
void BeatEditor::storePattern() {
    auto* object = grid.pattern.getDynamicObject(); if (!object) return;
    juce::Array<juce::var> notes;
    for (auto& combo : mappings) notes.add(combo.getSelectedId()-1);
    object->setProperty("notes",notes); object->setProperty("grid",quantize.getSelectedId()==1 ? 0 : quantize.getSelectedId());
    object->setProperty("strength",strength.getValue()/100.0);
    processor.setPattern(grid.pattern); grid.repaint();
}
void BeatEditor::timerCallback() {
    if (pending.valid() && pending.wait_for(std::chrono::milliseconds(0)) == std::future_status::ready) finishAnalysis();
    updateRecording();
    const bool idle = !busy && !processor.auditioning.load() && !processor.recorder.active() && !awaitingCapture;
    for (auto* button : {&import,&demo}) button->setEnabled(idle);
    analyze.setEnabled(idle && !take.empty());
    bpm.setEnabled(idle && processor.hostBpm.load()<=0); gate.setEnabled(idle); channel.setEnabled(idle);
    exportMidi.setEnabled(idle && grid.pattern.isObject() && (take.empty() || sourceMatchesPattern));
    for (auto& button:hear) button.setEnabled(idle && sourceMatchesPattern);

}
void BeatEditor::startAnalysis() {
    if (busy || take.empty() || processor.recorder.active()) return;
    if (!updateTiming()) return;
    sourceMatchesPattern = false;
    processor.setSource(take,takeRate,takeBpm,false); waveform.setAudio(take);
    busy = true; setStatus("Analyzing offline... A/B/C/D are suggested groups, not trained drum recognition.");
    auto* settings = new juce::DynamicObject(); settings->setProperty("bpm",takeBpm);
    settings->setProperty("bars",takeBars); settings->setProperty("gate_db",gate.getValue());
    const juce::String json = juce::JSON::toString(juce::var(settings));
    pending = std::async(std::launch::async,[audio=take,rate=static_cast<std::uint32_t>(takeRate),json] {
        char* result = beatlab_analyze(audio.data(),audio.size(),rate,json.toRawUTF8());
        const juce::var value = juce::JSON::parse(juce::String::fromUTF8(result)); beatlab_free(result); return value;
    });
}
void BeatEditor::finishAnalysis() {
    const juce::var result = pending.get(); busy = false;
    if (!static_cast<bool>(result["ok"])) { setStatus("Analysis failed: " + result["error"].toString()); return; }
    // Keep the user's mapping and quantize controls when re-analyzing a take.
    auto value=result["value"];
    juce::Array<juce::var> notes;
    for (auto& combo:mappings) notes.add(combo.getSelectedId()-1);
    value.getDynamicObject()->setProperty("notes",notes);
    value.getDynamicObject()->setProperty("grid",quantize.getSelectedId()==1 ? 0 : quantize.getSelectedId());
    value.getDynamicObject()->setProperty("strength",strength.getValue()/100.0);
    loadPattern(value); storePattern(); sourceMatchesPattern=true;
    processor.setSource(take,takeRate,takeBpm,true);
    const int count = grid.pattern["events"].getArray()->size();
    if (count==0) { setStatus("No hits detected. Check microphone input/monitoring and Gate. Source audio retained for Reanalyze."); return; }
    setStatus(juce::String(count) + " events. Click empty grid to add; click an event to reclassify/delete/change velocity. Review row is not exported.");
}
void BeatEditor::chooseFile(bool save,const juce::String& name,const juce::String& filter,std::function<void(juce::File)> action) {
    chooser = std::make_unique<juce::FileChooser>(name,juce::File::getSpecialLocation(juce::File::userHomeDirectory),filter);
    const int flags = (save ? juce::FileBrowserComponent::saveMode | juce::FileBrowserComponent::warnAboutOverwriting
                           : juce::FileBrowserComponent::openMode) | juce::FileBrowserComponent::canSelectFiles;
    juce::Component::SafePointer<BeatEditor> safe(this);
    chooser->launchAsync(flags,[safe,action=std::move(action)](const juce::FileChooser& dialog) {
        if (!safe) return; const auto file = dialog.getResult(); if (file != juce::File()) action(file);
    });
}
bool BeatEditor::isInterestedInFileDrag(const juce::StringArray& files) {
    return !busy && !processor.recorder.active() && !awaitingCapture && !processor.auditioning.load() && files.size() == 1
        && juce::File(files[0]).hasFileExtension("wav");
}
void BeatEditor::filesDropped(const juce::StringArray& files, int, int) {
    if (isInterestedInFileDrag(files)) loadWav(juce::File(files[0]));
    else setStatus("Drop one WAV. Internal Bitwig clip objects are not supported yet.");
}
bool BeatEditor::updateTiming() {
    takeBpm = bpm.getValue();
    const double expected = 16.0*60.0/takeBpm*takeRate;
    if (std::abs(static_cast<double>(take.size())-expected)>1.01) {
        setStatus("Expected exactly 4 bars in 4/4 at this BPM (" + juce::String(expected/takeRate,3) + " s). No trimming or stretching applied.");
        return false;
    }
    takeBars = 4;
    barLabel.setText("4 bars / 16 beats",juce::dontSendNotification);
    return true;
}
void BeatEditor::importWav() {
    chooseFile(false,"Import WAV (first sample = beat 1)","*.wav",[this](juce::File file) { loadWav(file); });
}
void BeatEditor::loadWav(const juce::File& file) {
    juce::WavAudioFormat format;
    auto stream = file.createInputStream();
    if (!stream) { setStatus("Cannot open WAV file."); return; }
    std::unique_ptr<juce::AudioFormatReader> reader(format.createReaderFor(stream.release(),true));
    if (!reader || reader->sampleRate<8000 || reader->sampleRate>192000 || reader->lengthInSamples<=0
        || reader->lengthInSamples>reader->sampleRate*60 || reader->numChannels>2 || reader->numChannels<1) {
        setStatus("Expected mono/stereo WAV, 8..192 kHz, at most 60 seconds."); return;
    }
    juce::AudioBuffer<float> audio(static_cast<int>(reader->numChannels),static_cast<int>(reader->lengthInSamples));
    if (!reader->read(&audio,0,audio.getNumSamples(),0,true,true)) { setStatus("WAV decoding failed."); return; }
    const auto* input = audio.getReadPointer(std::min(processor.inputChannel.load(),audio.getNumChannels()-1));
    if (!std::all_of(input,input+audio.getNumSamples(),[](float value) { return std::isfinite(value); })) {
        setStatus("WAV contains non-finite samples; previous take retained."); return;
    }
    take.assign(input,input+audio.getNumSamples()); takeRate=reader->sampleRate; sourceMatchesPattern=false;
    startAnalysis();
}
void BeatEditor::exportFile() {
    storePattern(); const juce::String json = juce::JSON::toString(grid.pattern);
    char* raw = beatlab_midi(json.toRawUTF8()); const auto result = juce::JSON::parse(juce::String::fromUTF8(raw)); beatlab_free(raw);
    if (!static_cast<bool>(result["ok"])) { setStatus("Export failed: " + result["error"].toString()); return; }
    juce::MemoryBlock bytes;
    if (auto* array = result["value"].getArray()) for (const auto& value : *array) {
        const auto byte = static_cast<std::uint8_t>(static_cast<int>(value)); bytes.append(&byte,1);
    }
    chooseFile(true,"Export MIDI - use a .mid filename","*.mid",[this,bytes](juce::File file) {
        if (!file.replaceWithData(bytes.getData(),bytes.getSize())) setStatus("Could not write MIDI file.");
        else setStatus("MIDI exported. Import into a Bitwig instrument clip with Drum Machine. MIDI contains no audio.");
    });
}
void BeatEditor::loadDemo() {
    sourceMatchesPattern=false;
    takeRate=48000; takeBpm=bpm.getValue(); takeBars=4;
    take.assign(static_cast<std::size_t>(takeBars*4*60.0/takeBpm*takeRate),0.0f);
    std::mt19937 generator(42); std::uniform_real_distribution<float> noise(-1,1);
    for (int step=0;step<takeBars*16;++step) {
        const int type=step%4==0 ? 0 : step%4==2 ? 1 : 2;
        const auto begin=static_cast<std::size_t>(step*0.25*60/takeBpm*takeRate);
        float previous=0;
        for (std::size_t i=0;i<4800 && begin+i<take.size();++i) {
            const double time=i/takeRate; const float n=noise(generator);
            const float sample= type==0 ? static_cast<float>(std::sin(2*juce::MathConstants<double>::pi*85*time)*std::exp(-time*45))
                : type==1 ? n*static_cast<float>(std::exp(-time*60))
                : (n-previous)*static_cast<float>(std::exp(-time*140))*0.5f;
            take[begin+i]+=sample*0.7f; previous=n;
        }
    }
    startAnalysis();
}

void BeatEditor::configureRecording() {
    for (auto* button:{&record,&stop}) addAndMakeVisible(button);
    addAndMakeVisible(recordMode); addAndMakeVisible(click);
    addAndMakeVisible(clockStatus); addAndMakeVisible(waveform);
    recordMode.addItem("Once / 4 bars",1); recordMode.addItem("Loop / overwrite",2);
    recordMode.setSelectedId(1); click.setToggleState(true,juce::dontSendNotification);
    click.onClick=[this] { processor.recorder.clickDuringTake.store(click.getToggleState()); };
    record.onClick=[this] {
        if (busy || processor.recorder.active()) return;
        processor.manualBpm.store(bpm.getValue());
        processor.recorder.start(recordMode.getSelectedId()==2); awaitingCapture=true;
        setStatus("Waiting for microphone audio processing. The track must be active and monitored.");
    };
    stop.onClick=[this] { processor.recorder.stop(); awaitingCapture=false; };
    recordMode.setTooltip("Loop replaces the previous full take. Stop discards an incomplete final pass.");
    click.setTooltip("Click during recording. Count-in always clicks. Use headphones to avoid microphone bleed.");
}
void BeatEditor::updateRecording() {
    auto& recorder=processor.recorder;
    const bool active=recorder.active();
    const auto heartbeat=processor.audioHeartbeat.load();
    silentTicks=heartbeat==lastHeartbeat ? silentTicks+1 : 0; lastHeartbeat=heartbeat;
    if (active) awaitingCapture=false;
    if (awaitingCapture && !recorder.pending() && !active) {
        awaitingCapture=false;
        setStatus("Cannot record: use 4/4, 40-240 BPM and 8-192 kHz.");
    }
    const double hostTempo=processor.hostBpm.load();
    if (hostTempo>0 && take.empty() && !active) bpm.setValue(hostTempo,juce::dontSendNotification);
    const auto peak=recorder.inputPeak.exchange(0);
    clockStatus.setText((hostTempo>0 ? "Host: "+juce::String(hostTempo,1)+" BPM" : "Manual BPM (host tempo unavailable)")
        + (processor.hostFourFour.load() ? "   |   4/4   |   Input: " : "   |   Use 4/4   |   Input: ") + (peak>0 ? juce::String(juce::Decibels::gainToDecibels(peak),1)+" dBFS" : "silent")
        + "   |   Complete takes: "+juce::String(recorder.cycles.load()),juce::dontSendNotification);
    record.setEnabled(!busy && !active && !awaitingCapture && !processor.auditioning.load() && processor.hostFourFour.load());
    stop.setEnabled(active || awaitingCapture); recordMode.setEnabled(!active && !awaitingCapture);
    if (active) {
        setStatus(recorder.state.load()==BeatRecorder::State::countIn
            ? "Count-in: "+juce::String(recorder.countdown.load())+"  —  start on the next downbeat."
            : "Recording 4 bars. Stop keeps the last COMPLETE take; partial takes are discarded.");
    }
    if (silentTicks>15 && (active || awaitingCapture))
        setStatus("No audio callbacks. Enable track monitoring / audio engine, then press Record. No microphone sound is passed through.");
    if (!busy) processor.collectRecording();
    if (!busy && seenRecording!=processor.recordingRevision.load()) {
        seenRecording=processor.recordingRevision.load();
        const auto captured=processor.getSource();
        take=captured.audio; takeRate=captured.rate; takeBpm=captured.bpm;
        bpm.setValue(takeBpm,juce::dontSendNotification); sourceMatchesPattern=false;
        waveform.setAudio(take); startAnalysis();
    } else if (wasRecording && !active) {
        setStatus(recorder.error.load()==BeatRecorder::Error::clockChanged
            ? "Recording stopped: tempo, sample rate or meter changed. Last complete take retained."
            : "Stopped. No new complete four-bar take; previous audio and MIDI retained.");
    }
    wasRecording=active; waveform.repaint();
}
