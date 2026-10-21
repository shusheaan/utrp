// Transport-only: retain the existing Generic keyboard input and Library routing.
loadAPI(25);
load('Keystation.config.js');
host.defineController('UTRP', 'Keystation Transport', '1.1',
    '8c626b8c-dd31-4cf0-a8b4-94f4c16321ee', 'UTRP');
host.defineMidiPorts(1, 0);
host.addDeviceNameBasedDiscoveryPair([KEYSTATION_TRANSPORT.port], []);

const keystationTransport = (() => {
    const pressed = new Set();
    let transport, cursor, parent, recording, playing;
    function interested(value) { value.markInterested(); return value; }
    function fold(expanded) {
        if (!cursor.exists().get()) return;
        const group = cursor.isGroup().get() ? cursor : parent;
        if (!group.exists().get() || group.trackType().get() !== 'Group') return;
        group.isGroupExpanded().set(expanded);
        // Keep the selection visible when collapsing a leaf's containing folder.
        if (!expanded && group === parent) parent.selectInEditor();
    }
    function toggleArm() {
        if (!cursor.exists().get() || cursor.isGroup().get() ||
            (!cursor.canHoldNoteData().get() && !cursor.canHoldAudioData().get())) {
            host.showPopupNotification('Select an instrument or audio track to arm.');
            return;
        }
        cursor.arm().toggle();
    }
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
                host.showPopupNotification('Stop recording before navigating or changing record arm.');
                return;
            }
            if (action === 'previousTrack') cursor.selectPrevious();
            else if (action === 'nextTrack') cursor.selectNext();
            else if (action === 'collapseGroup') fold(false);
            else if (action === 'expandGroup') fold(true);
            else if (action === 'toggleArm') toggleArm();
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
        cursor = host.createCursorTrack('keystation-navigation', 'Keystation Navigation', 0, 0, true);
        cursor.setCursorNavigationMode(Java.type('com.bitwig.extension.controller.api.CursorNavigationMode').GUI);
        parent = cursor.createParentTrack(0, 0);
        [cursor.exists(), cursor.isGroup(), cursor.trackType(), cursor.isGroupExpanded(),
            cursor.arm(), cursor.canHoldNoteData(), cursor.canHoldAudioData(),
            parent.exists(), parent.trackType(), parent.isGroupExpanded()].forEach(interested);
        host.getMidiInPort(0).setMidiCallback(midi);
        // Deliberately no createNoteInput: transport notes must never reach instruments.
        println('Keystation Transport 1.1 ready: folders + manual arm');
    }
    return {init: initialize, exit: () => pressed.clear()};
})();
function init() { keystationTransport.init(); }
function exit() { keystationTransport.exit(); }
