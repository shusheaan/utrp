// Library-only exclusive audition. No network listener or MIDI event re-emission.
loadAPI(25);
load('Library.config.js');
load('Library.key-sync.js');
host.defineController('UTRP', 'Library', '0.7', 'a64c109f-e3af-4e32-9f21-42f9721b2541', 'UTRP');
host.defineMidiPorts(0, 0);

const libraryController = (() => {
    const tracks = [];
    const devices = [];
    const keySyncs = [];
    let project;
    let enabled;
    let ready = false;
    let generation = 0;
    let lastSound = -1;
    let pendingSelection = -1;
    const editorSlots = 4;

    function interested(value) { value.markInterested(); return value; }
    function guitar(index) {
        return UTRP_LIBRARY_GUITAR_NAMES.indexOf(tracks[index].name().get()) >= 0;
    }
    function sound(index) {
        return tracks[index].exists().get() && (UTRP_LIBRARY_SOUND_NAMES.indexOf(tracks[index].name().get()) >= 0 ||
            guitar(index));
    }
    function sharedIndex() {
        const first = devices[0].getItemAt(0);
        if (first.exists().get() && first.name().get() === 'Chord Lab') return 0;
        const second = devices[0].getItemAt(1);
        return first.exists().get() && first.name().get() === 'Note Receiver' &&
            second.exists().get() && second.name().get() === 'Chord Lab' ? 1 : -1;
    }
    function sharedDevice() { return devices[0].getItemAt(sharedIndex()); }
    function allowed() {
        return ready && enabled.get() && /^(Library|Library-migration)$/.test(project.get()) &&
            tracks[0].name().get() === 'CHORD LAB - shared MIDI input' &&
            sharedIndex() >= 0;
    }
    function openEditors(index, run, projectName, attempt) {
        if (run !== generation || !allowed() || project.get() !== projectName) return;
        const editor = devices[index].getItemAt(0).isWindowOpen();
        editor.set(true);
        host.scheduleTask(() => {
            if (run !== generation || !allowed() || project.get() !== projectName) return;
            if (!editor.get() && attempt < 8) {
                host.scheduleTask(() => openEditors(index, run, projectName, attempt + 1), 500);
                return;
            }
            if (!editor.get()) host.showPopupNotification('Instrument editor unavailable; open it from the device panel.');
            sharedDevice().isWindowOpen().set(true);
        }, 250);
    }
    function selectSound(index) {
        if (!allowed() || !sound(index)) return;
        if (lastSound === index) {
            closeEditors();
            openEditors(index, ++generation, project.get(), 0);
            return;
        }
        const run = ++generation;
        const projectName = project.get();
        lastSound = index;
        // Close the shared editor as well: reopening it LAST gives computer keys a clear focus target.
        closeEditors();
        for (let i = 0; i < tracks.length; i++) {
            if (!sound(i)) continue;
            const current = i === index;
            tracks[i].arm().set(current);
            tracks[i].monitorMode().set(current ? 'ON' : 'OFF');
            tracks[i].isActivated().set(current);
        }
        tracks[0].isActivated().set(true);
        tracks[0].arm().set(false);
        tracks[0].monitorMode().set('ON');
        host.scheduleTask(() => {
            if (run !== generation || !allowed() || project.get() !== projectName) return;
            // Loading an inactive track restores its saved arm state. Re-apply AFTER activation.
            tracks[index].arm().set(true);
            tracks[index].monitorMode().set('ON');
            openEditors(index, run, projectName, 0);
        }, 650);
    }
    function localChord(index) {
        const count = index === 0 ? 2 : editorSlots;
        for (let slot = 0; slot < count; slot++) {
            const device = devices[index].getItemAt(slot);
            if (device.exists().get() && device.name().get() === 'Chord Lab') return device;
        }
        return null;
    }
    function closeEditors() {
        for (let i = 0; i < tracks.length; i++) {
            if (!tracks[i].exists().get() || (!sound(i) && !localChord(i))) continue;
            const count = i === 0 ? 2 : editorSlots;
            for (let slot = 0; slot < count; slot++) {
                const device = devices[i].getItemAt(slot);
                if (device.exists().get()) device.isWindowOpen().set(false);
            }
        }
    }
    function selectTrack(index) {
        if (!allowed()) return;
        if (sound(index)) { selectSound(index); return; }
        const chord = localChord(index);
        if (!chord) return; // Groups/empty tracks do not change routing or open unrelated editors.
        ++generation; // Cancel delayed editors belonging to the previous sound selection.
        closeEditors();
        chord.isWindowOpen().set(true);
    }
    function initController() {
        project = interested(host.createApplication().projectName());
        enabled = host.getPreferences().getBooleanSetting('Exclusive audition + editors', 'Library only', true);
        enabled.addValueObserver(() => { lastSound = -1; ++generation; });
        project.addValueObserver(() => {
            ready = false;
            lastSound = -1;
            const run = ++generation;
            host.scheduleTask(() => {
                if (run !== generation) return;
                ready = true;
                keySyncs.forEach(sync => sync.flush());
                if (pendingSelection >= 0) selectTrack(pendingSelection);
            }, 1500);
        });
        const bank = host.createTrackBank(128, 0, 0, true);
        bank.setContentFilter(Java.type('com.bitwig.extension.controller.api.TrackBankContentFilter').ALL_CHANNELS);
        bank.setSkipDisabledItems(false);
        for (let i = 0; i < 128; i++) {
            const track = bank.getItemAt(i);
            [track.name(), track.exists()].forEach(interested);
            tracks.push(track);
            const count = i === 0 ? 2 : editorSlots;
            const bankDevices = track.createDeviceBank(count);
            for (let j = 0; j < count; j++) {
                const device = bankDevices.getItemAt(j);
                [device.name(), device.exists(), device.isWindowOpen()].forEach(interested);
            }
            devices.push(bankDevices);
            track.addIsSelectedInEditorObserver(selected => {
                if (selected) { pendingSelection = i; selectTrack(i); }
            });
        }
        const playing = interested(host.createTransport().isPlaying());
        for (let i = 0; i < 2; i++) {
            keySyncs.push(createLibraryKeySync(host.getProject().getRootTrackGroup(), devices[0].getItemAt(i),
                () => allowed() && sharedIndex() === i, () => !playing.get(),
                message => host.showPopupNotification(message), 'Chord Lab Key Sync ' + i));
        }
    }
    return {init: initController, flush: () => { keySyncs.forEach(sync => sync.flush()); }, exit: () => { ready = false; ++generation; }};
})();
function init() { libraryController.init(); }
function flush() { libraryController.flush(); }
function exit() { libraryController.exit(); }
