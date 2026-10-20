#include "recorder.h"
#include <algorithm>
#include <cmath>

BeatRecorder::BeatRecorder() {
    for (auto& buffer:buffers) buffer.resize(capacity);
    clearPeaks();
}
bool BeatRecorder::active() const noexcept {
    const auto current=state.load();
    return current==State::countIn || current==State::recording;
}
void BeatRecorder::start(bool loop) noexcept { command.store(loop ? Command::loop : Command::once); }
void BeatRecorder::stop() noexcept { command.store(Command::stop); }
void BeatRecorder::interrupt() noexcept { command.store(Command::none); if (active()) halt(Error::interrupted); }
void BeatRecorder::clearPeaks() noexcept { for (auto& peak:peaks) peak.store(0); }
void BeatRecorder::halt(Error why) noexcept {
    error.store(why); countdown.store(0);
    state.store(haveCompleted ? State::ready : State::idle);
}
void BeatRecorder::begin(double bpm, double rate, bool loop) noexcept {
    clockBpm=bpm; clockRate=rate; looping=loop;
    length=static_cast<std::size_t>(std::llround(16*60*rate/bpm));
    countLength=static_cast<std::size_t>(std::llround(4*60*rate/bpm));
    writing=1-completed; cursor=0; countCursor=0;
    cycles.store(0); progress.store(0); countdown.store(4); error.store(Error::none);
    clearPeaks(); state.store(State::countIn);
}
void BeatRecorder::beginBlock(double bpm, double rate, bool fourFour) noexcept {
    // A reader may copy the last full take only while idle/ready. Defer starts until it finishes.
    if (reading.load()) return;
    const auto request=command.exchange(Command::none);
    const bool valid=std::isfinite(bpm) && bpm>=40 && bpm<=240
        && std::isfinite(rate) && rate>=8000 && rate<=192000 && fourFour;
    if (request==Command::stop) { halt(Error::none); return; }
    if (request==Command::once || request==Command::loop) {
        if (!valid) { halt(Error::invalidClock); return; }
        // Publish active before checking reader again: the reader checks state after claiming its guard.
        state.store(State::countIn);
        if (reading.load()) { command.store(request); halt(Error::none); return; }
        begin(bpm,rate,request==Command::loop);
    }
    if (active() && (!valid || std::abs(bpm-clockBpm)>0.00001 || rate!=clockRate))
        halt(Error::clockChanged);
}
float BeatRecorder::click(std::size_t position, bool enabled) const noexcept {
    if (!enabled) return 0;
    const double beatSamples=60*clockRate/clockBpm;
    const auto beat=static_cast<std::size_t>(std::floor(position/beatSamples));
    const double offset=position-std::round(beat*beatSamples);
    const double duration=clockRate*0.015;
    if (offset<0 || offset>=duration) return 0;
    const double frequency=beat%4==0 ? 1400.0 : 1000.0;
    return static_cast<float>(0.12*std::sin(6.283185307179586*frequency*offset/clockRate)*(1-offset/duration));
}
float BeatRecorder::process(float input) noexcept {
    if (!std::isfinite(input)) input=0;
    inputPeak.store(std::max(inputPeak.load(),std::abs(input)));
    const auto current=state.load();
    if (current==State::countIn) {
        const auto sound=click(countCursor,true);
        countdown.store(std::max(1,4-static_cast<int>(countCursor*4/countLength)));
        if (++countCursor==countLength) { countdown.store(0); state.store(State::recording); }
        return sound;
    }
    if (current!=State::recording) return 0;
    const auto sound=click(cursor,clickDuringTake.load());
    buffers[static_cast<std::size_t>(writing)][cursor]=input;
    const auto bin=std::min(bins-1,cursor*bins/length);
    peaks[bin].store(std::max(peaks[bin].load(),std::abs(input)));
    ++cursor; progress.store(static_cast<float>(cursor)/static_cast<float>(length));
    if (cursor==length) {
        completed=writing; completedLength=length; completedRate=clockRate; completedBpm=clockBpm;
        haveCompleted=true; ++generation; cycles.fetch_add(1);
        if (looping) { writing=1-completed; cursor=0; clearPeaks(); }
        else halt(Error::none);
    }
    return sound;
}
bool BeatRecorder::copyCompleted(std::vector<float>& audio,double& rate,double& bpm,std::uint64_t& seen) {
    if (reading.exchange(true)) return false;
    struct Guard { std::atomic<bool>& flag; ~Guard() { flag.store(false); } } guard{reading};
    if (active() || !haveCompleted || seen==generation) return false;
    const auto& source=buffers[static_cast<std::size_t>(completed)];
    audio.assign(source.begin(),source.begin()+static_cast<std::ptrdiff_t>(completedLength));
    rate=completedRate; bpm=completedBpm; seen=generation;
    return true;
}
