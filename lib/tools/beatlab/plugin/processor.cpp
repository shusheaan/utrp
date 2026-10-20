#include "processor.h"
#include "editor.h"
#include "ffi.h"

BeatProcessor::BeatProcessor() : AudioProcessor(BusesProperties()
    .withInput("Microphone", juce::AudioChannelSet::stereo(), true)
    .withOutput("Muted output", juce::AudioChannelSet::stereo(), true)) {}
bool BeatProcessor::isBusesLayoutSupported(const BusesLayout& l) const {
    return (l.getMainInputChannelSet() == juce::AudioChannelSet::mono()
        || l.getMainInputChannelSet() == juce::AudioChannelSet::stereo())
        && l.getMainInputChannelSet() == l.getMainOutputChannelSet();
}
void BeatProcessor::processBlock(juce::AudioBuffer<float>& audio, juce::MidiBuffer& midi) {
    juce::ScopedNoDenormals noDenormals;
    if (audio.getNumChannels() == 0 || audio.getNumSamples() == 0) {
        midi.clear();
        return;
    }
    double tempo=0; bool fourFour=true;
    if (auto* playhead=getPlayHead()) if (const auto position=playhead->getPosition()) {
        if (const auto value=position->getBpm()) tempo=*value;
        if (const auto signature=position->getTimeSignature())
            fourFour=signature->numerator==4 && signature->denominator==4;
    }
    hostBpm.store(tempo); hostFourFour.store(fourFour); audioHeartbeat.fetch_add(1);
    recorder.beginBlock(tempo>0 ? tempo : manualBpm.load(),sampleRate.load(),fourFour);
    const int input=std::clamp(inputChannel.load(),0,audio.getNumChannels()-1);
    for (int i=0;i<audio.getNumSamples();++i) {
        const float click=recorder.process(audio.getSample(input,i));
        for (int channel=0;channel<audio.getNumChannels();++channel) audio.setSample(channel,i,click);
    } // Click only: microphone monitoring stays muted to prevent feedback.
    if (auditioning.load()) {
        const int count = std::min(audio.getNumSamples(),static_cast<int>(auditionSize-auditionPosition));
        for (int channelIndex=0;channelIndex<audio.getNumChannels();++channelIndex)
            audio.copyFrom(channelIndex,0,auditionSamples.data()+auditionPosition,count);
        auditionPosition += static_cast<std::size_t>(count);
        if (auditionPosition == auditionSize) auditioning.store(false);
    }
    midi.clear();
}
bool BeatProcessor::audition(const std::vector<float>& audio, double sourceRate, std::size_t start) {
    if (auditioning.load() || start>=audio.size()
        || sourceRate<8000 || sourceRate>192000) return false;
    const double targetRate=sampleRate.load();
    auditionSize=std::min(auditionSamples.size(),static_cast<std::size_t>(
        std::min(0.25,static_cast<double>(audio.size()-start)/sourceRate)*targetRate));
    for (std::size_t i=0;i<auditionSize;++i) {
        const double at=start+i*sourceRate/targetRate;
        const auto a=std::min(audio.size()-1,static_cast<std::size_t>(at));
        const auto b=std::min(audio.size()-1,a+1);
        const float mix=static_cast<float>(at-std::floor(at));
        const float fade=std::min(1.0f,static_cast<float>(auditionSize-i)/static_cast<float>(targetRate*0.005));
        auditionSamples[i]=std::clamp((audio[a]*(1-mix)+audio[b]*mix)*fade,-0.8f,0.8f);
    }
    auditionPosition=0; auditioning.store(auditionSize>0); return auditionSize>0;
}
juce::var BeatProcessor::getPattern() const {
    const juce::ScopedLock lock(stateLock);
    return juce::JSON::parse(patternJson);
}
void BeatProcessor::setPattern(const juce::var& value) {
    const juce::ScopedLock lock(stateLock);
    patternJson = juce::JSON::toString(value);
    updateHostDisplay(juce::AudioProcessorListener::ChangeDetails().withNonParameterStateChanged(true));
}
bool BeatProcessor::collectRecording() {
    const juce::ScopedLock lock(stateLock);
    if (!recorder.copyCompleted(source.audio,source.rate,source.bpm,collectedTake)) return false;
    source.matched=false; recordingRevision.fetch_add(1);
    return true;
}
BeatProcessor::Source BeatProcessor::getSource() const {
    const juce::ScopedLock lock(stateLock); return source;
}
void BeatProcessor::setSource(const std::vector<float>& audio,double rate,double bpm,bool matched) {
    { const juce::ScopedLock lock(stateLock); source={audio,rate,bpm,matched}; }
    updateHostDisplay(juce::AudioProcessorListener::ChangeDetails().withNonParameterStateChanged(true));
}
void BeatProcessor::getStateInformation(juce::MemoryBlock& output) {
    collectRecording();
    const juce::ScopedLock lock(stateLock);
    auto* root=new juce::DynamicObject(); root->setProperty("beatlab_state",3);
    root->setProperty("gate_db",analysisGateDb.load());
    root->setProperty("pattern",juce::JSON::parse(patternJson));
    if (!source.audio.empty()) {
        juce::MemoryOutputStream pcm;
        for (float sample:source.audio) pcm.writeFloat(sample);
        root->setProperty("pcm",pcm.getMemoryBlock().toBase64Encoding());
        root->setProperty("rate",source.rate); root->setProperty("bpm",source.bpm);
        root->setProperty("matched",source.matched);
    }
    const auto json=juce::JSON::toString(juce::var(root));
    output.replaceAll(json.toRawUTF8(),json.getNumBytesAsUTF8());
}
void BeatProcessor::setStateInformation(const void* data,int size) {
    if (!data || size<=0 || size>64*1024*1024) return;
    const auto root=juce::JSON::parse(juce::String::fromUTF8(static_cast<const char*>(data),size));
    const bool envelope=static_cast<int>(root["beatlab_state"])==3;
    const auto gateValue=root["gate_db"];
    const double restoredGate=envelope && root.hasProperty("gate_db") ? static_cast<double>(gateValue) : -36.0;
    if (envelope && root.hasProperty("gate_db") && !gateValue.isDouble() && !gateValue.isInt() && !gateValue.isInt64()) return;
    if (!std::isfinite(restoredGate) || restoredGate < -60 || restoredGate > -12) return;
    const auto pattern=envelope ? root["pattern"] : root;
    if (envelope && !pattern.isVoid() && !pattern.isObject()) return;
    if (!envelope || pattern.isObject()) {
        char* raw=beatlab_midi(juce::JSON::toString(pattern).toRawUTF8());
        const auto result=juce::JSON::parse(juce::String::fromUTF8(raw)); beatlab_free(raw);
        if (!static_cast<bool>(result["ok"])) return;
    }
    Source restored;
    if (envelope && root.hasProperty("pcm")) {
        restored.rate=static_cast<double>(root["rate"]); restored.bpm=static_cast<double>(root["bpm"]);
        if (!std::isfinite(restored.rate) || restored.rate<8000 || restored.rate>192000
            || !std::isfinite(restored.bpm) || restored.bpm<40 || restored.bpm>240) return;
        juce::MemoryBlock pcm;
        if (!pcm.fromBase64Encoding(root["pcm"].toString()) || pcm.getSize()%4!=0) return;
        const auto count=pcm.getSize()/4;
        if (std::abs(static_cast<double>(count)-16*60*restored.rate/restored.bpm)>1.01) return;
        juce::MemoryInputStream stream(pcm,false); restored.audio.resize(count);
        for (auto& sample:restored.audio) { sample=stream.readFloat(); if (!std::isfinite(sample)) return; }
        restored.matched=static_cast<bool>(root["matched"]) && pattern.isObject();
    }
    const juce::ScopedLock lock(stateLock);
    patternJson=pattern.isObject() ? juce::JSON::toString(pattern) : juce::String{};
    source=std::move(restored);
    analysisGateDb.store(restoredGate);
}
juce::AudioProcessorEditor* BeatProcessor::createEditor() { return new BeatEditor(*this); }
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new BeatProcessor(); }
