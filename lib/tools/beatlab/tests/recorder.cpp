#include "../plugin/recorder.h"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
void require(bool value,const char* message) { if (!value) throw std::runtime_error(message); }
void run(BeatRecorder& recorder,std::size_t samples,float value) {
    for (std::size_t i=0;i<samples;++i) recorder.process(value);
}
int main() {
    BeatRecorder recorder; std::vector<float> audio; double rate=0,bpm=0; std::uint64_t seen=0;
    recorder.start(false); recorder.beginBlock(240,8000,true);
    require(recorder.state.load()==BeatRecorder::State::countIn,"Four-beat count-in");
    run(recorder,8000,0.9f);
    require(recorder.state.load()==BeatRecorder::State::recording,"Exact count-in boundary");
    require(!recorder.copyCompleted(audio,rate,bpm,seen),"No read of active recording");
    run(recorder,31999,0.25f); require(recorder.active(),"Do not stop early");
    run(recorder,1,0.25f); require(!recorder.active(),"Once stops at exactly four bars");
    require(recorder.copyCompleted(audio,rate,bpm,seen),"Publish full take");
    require(audio.size()==32000 && rate==8000 && bpm==240,"Recorded timing metadata");
    for (auto sample:audio) require(sample==0.25f,"No count-in or generated click in recording");
    require(!recorder.copyCompleted(audio,rate,bpm,seen),"No duplicate delivery");
    recorder.start(true); recorder.beginBlock(240,8000,true); run(recorder,8000,0);
    run(recorder,32000,0.3f); run(recorder,32000,0.4f); run(recorder,900,0.8f);
    require(recorder.cycles.load()==2,"Two completed loop passes");
    recorder.stop(); recorder.beginBlock(240,8000,true);
    require(recorder.copyCompleted(audio,rate,bpm,seen),"Loop stop publishes full take");
    for (auto sample:audio) require(sample==0.4f,"Partial last pass cannot corrupt latest full take");
    recorder.start(false); recorder.beginBlock(240,8000,true); run(recorder,8000+50,0.6f);
    recorder.stop(); recorder.beginBlock(240,8000,true);
    require(!recorder.copyCompleted(audio,rate,bpm,seen),"Stopping early retains previous take");
    recorder.start(false); recorder.beginBlock(240,8000,true); run(recorder,8000,0);
    recorder.beginBlock(120,8000,true);
    require(!recorder.active() && recorder.error.load()==BeatRecorder::Error::clockChanged,"Tempo change safely cancels partial take");
    for (const auto tempo:{0.0,39.0,241.0,std::numeric_limits<double>::quiet_NaN()}) {
        recorder.start(false); recorder.beginBlock(tempo,48000,true);
        require(!recorder.active() && recorder.error.load()==BeatRecorder::Error::invalidClock,"Reject invalid tempo");
    }
    for (const auto rateValue:{7999.0,192001.0,std::numeric_limits<double>::quiet_NaN()}) {
        recorder.start(false); recorder.beginBlock(120,rateValue,true);
        require(!recorder.active(),"Reject unsupported sample rates");
    }
    recorder.start(false); recorder.beginBlock(120,48000,false);
    require(!recorder.active(),"Reject non-4/4");
    recorder.start(false); recorder.beginBlock(137,44100,true);
    run(recorder,static_cast<std::size_t>(std::llround(4*60*44100.0/137)),0);
    run(recorder,static_cast<std::size_t>(std::llround(16*60*44100.0/137)),0.1f);
    require(recorder.copyCompleted(audio,rate,bpm,seen),"Fractional samples per beat complete");
    require(std::abs(static_cast<double>(audio.size())-16*60*44100.0/137)<0.51,"Half-sample length tolerance");
    recorder.start(false); recorder.beginBlock(120,48000,true); recorder.interrupt();
    require(!recorder.active() && recorder.error.load()==BeatRecorder::Error::interrupted,"Host release aborts safely");
    recorder.start(false); recorder.beginBlock(240,8000,true); run(recorder,8000,0);
    recorder.clickDuringTake.store(false);
    require(recorder.process(std::numeric_limits<float>::infinity())==0,"Click toggle and nonfinite input");
    run(recorder,31999,0); require(recorder.copyCompleted(audio,rate,bpm,seen),"Silent take available");
    require(audio.front()==0,"Nonfinite audio sanitized");
    std::cout << "Recorder count-in, once, overwrite, cancellation, clock, sample boundaries PASS\n";
}
