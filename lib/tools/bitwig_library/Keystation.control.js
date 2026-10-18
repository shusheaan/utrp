// Transport-only: retain the existing Generic keyboard input and Library routing.
loadAPI(25);
load('Keystation.config.js');
host.defineController('UTRP', 'Keystation Transport', '1.0',
    '8c626b8c-dd31-4cf0-a8b4-94f4c16321ee', 'UTRP');
host.defineMidiPorts(1, 0);
host.addDeviceNameBasedDiscoveryPair([KEYSTATION_TRANSPORT.port], []);

const keystationTransport = (() => {
    const pressed = new Set();
    let transport, cursor, recording, playing, position, numerator, denominator;
    function interested(value) { value.markInterested(); return value; }
    function perform(action) {
        if (action === 'stop') {
            transport.stop();
            recording.set(false);
        } else if (action === 'play') {
            if (!playing.get()) transport.play();
        } else if (action === 'record') {
            if (recording.get()) recording.set(false);
            else transport.record();
        } else {
            if (recording.get()) {
                host.showPopupNotification('Stop recording before navigating.');
                return;
            }
            if (action === 'previousTrack') cursor.selectPrevious();
            else if (action === 'nextTrack') cursor.selectNext();
            else if (action === 'home') transport.rewind();
            else {
                const step = numerator.get() * 4 / denominator.get() * KEYSTATION_TRANSPORT.barsPerStep;
                const next = position.get() + (action === 'nextBar' ? step : -step);
                if (Number.isFinite(next) && step > 0) transport.setPosition(Math.max(0, next));
            }
        }
        println('Keystation Transport: ' + action);
    }
    function midi(status, note, velocity) {
        if (!Number.isInteger(status) || !Number.isInteger(note) || !Number.isInteger(velocity) ||
            status < 0x80 || status > 0xef || note < 0 || note > 127 || velocity < 0 || velocity > 127 ||
            (status & 15) !== KEYSTATION_TRANSPORT.channel) return;
        const type = status & 0xf0;
        if (type !== 0x80 && type !== 0x90) return;
        const action = KEYSTATION_TRANSPORT.notes[note];
        if (!action) return;
        if (type === 0x80 || velocity === 0) { pressed.delete(note); return; }
        if (pressed.has(note)) return;
        pressed.add(note);
        perform(action);
    }
    function initialize() {
        transport = host.createTransport();
        recording = interested(transport.isArrangerRecordEnabled());
        playing = interested(transport.isPlaying());
        position = interested(transport.getPosition());
        numerator = interested(transport.timeSignature().numerator());
        denominator = interested(transport.timeSignature().denominator());
        cursor = host.createCursorTrack('keystation-navigation', 'Keystation Navigation', 0, 0, true);
        host.getMidiInPort(0).setMidiCallback(midi);
        // Deliberately no createNoteInput: transport notes must never reach instruments.
    }
    return {init: initialize, exit: () => pressed.clear()};
})();
function init() { keystationTransport.init(); }
function exit() { keystationTransport.exit(); }
