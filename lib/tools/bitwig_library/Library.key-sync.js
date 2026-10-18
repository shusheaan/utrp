// Bidirectional Library key sync via explicitly mapped native Project Remotes.
// Startup/conflicts: project wins. No MIDI transformation or unsupported-mode approximation.
function createLibraryKeySync(projectRoot, device, allowed, canApply, notify, pageId = 'Chord Lab Key Sync') {
    // Semitones from the parent major tonic to each diatonic mode's tonic.
    const modeOffsets = Object.freeze({Major: 0, Dorian: 2, Phrygian: 4, Lydian: 5,
        Mixolydian: 7, Minor: 9, Locrian: 11});
    const page = projectRoot.createCursorRemoteControlsPage(pageId, 8, '');
    const root = page.getParameter(0);
    const scale = page.getParameter(1);
    const values = new Map();
    const ids = new Map();
    let keyId = null, soundingId = null;
    let previous = null, expectedPlugin = [], expectedRoot = [], deferred = false;
    let warning = null;
    function reset() { previous = null; expectedPlugin = []; expectedRoot = []; deferred = false; }
    function parameterId(id) { return String(id).replace(/^CONTENTS\/ROOT_GENERIC_MODULE\//, 'CONTENTS/'); }
    function discrete(value, count) {
        if (!Number.isFinite(value) || value < 0 || value > 1 || !Number.isInteger(count) || count < 2) return null;
        const index = Math.round(value * (count - 1));
        return Math.abs(value * (count - 1) - index) < 0.00001 ? index : null;
    }
    for (const parameter of [root, scale]) {
        for (const value of [parameter.name(), parameter.value(),
            parameter.value().discreteValueCount(), parameter.value().discreteValueNames()]) value.markInterested();
    }
    device.addDirectParameterIdObserver(list => {
        ids.clear();
        for (const id of list) ids.set(parameterId(id), String(id));
        for (const id of values.keys()) if (!ids.has(id)) values.delete(id);
        if (!ids.has(keyId) || !ids.has(soundingId)) reset();
        if (!ids.has(keyId)) keyId = null;
        if (!ids.has(soundingId)) soundingId = null;
    });
    device.addDirectParameterNormalizedValueObserver((id, value) => { values.set(parameterId(id), value); });
    device.addDirectParameterNameObserver(128, (id, name) => {
        id = parameterId(id);
        if (name === 'Key') keyId = id;
        else if (keyId === id) { keyId = null; reset(); }
        if (name === 'Sounding (read only)') soundingId = id;
        else if (soundingId === id) { soundingId = null; reset(); }
    });
    function hostState() {
        if (!allowed() || root.name().get() !== 'Root Key' || scale.name().get() !== 'Scale' ||
            root.value().discreteValueCount().get() !== 12) return null;
        const tonic = discrete(root.value().get(), 12);
        const index = discrete(scale.value().get(), scale.value().discreteValueCount().get());
        const mode = index === null ? undefined : Array.from(scale.value().discreteValueNames().get())[index];
        if (tonic === null || mode === undefined) return null;
        if (!Object.prototype.hasOwnProperty.call(modeOffsets, mode)) {
            if (warning !== mode) notify('Chord Lab key sync paused: ' + mode + ' is outside the major-scale family. Sync is paused.');
            warning = mode;
            return null;
        }
        warning = null;
        const offset = modeOffsets[mode];
        return {tonic, mode, offset, major: (tonic - offset + 12) % 12};
    }
    function flush() {
        const current = hostState();
        const plugin = discrete(values.get(keyId), 12);
        if (current === null || plugin === null || !ids.has(keyId)) { reset(); return; }
        const hostChanged = previous === null || current.tonic !== previous.tonic || current.mode !== previous.mode;
        const pluginChanged = previous !== null && plugin !== previous.plugin;
        const rootAck = expectedRoot.indexOf(current.tonic);
        const pluginAck = expectedPlugin.indexOf(plugin);
        const hostEcho = rootAck >= 0 && previous !== null && current.mode === previous.mode;
        const pluginEcho = pluginAck >= 0;
        if (hostChanged) {
            if (hostEcho) expectedRoot.splice(0, rootAck + 1);
            else expectedRoot = [];
        }
        if (pluginChanged || pluginEcho) {
            if (pluginEcho) expectedPlugin.splice(0, pluginAck + 1);
            else expectedPlugin = [];
        }
        previous = {...current, plugin};
        if ((hostChanged && !hostEcho) || deferred) {
            // Preserve the engine's existing no-key-change-while-playing/sounding guard.
            deferred = !canApply() || discrete(values.get(soundingId), 2) !== 0;
            if (!deferred && plugin !== current.major) {
                expectedPlugin.push(current.major);
                device.setDirectParameterValueNormalized(ids.get(keyId), current.major, 12);
            }
        } else if (pluginChanged && !pluginEcho) {
            const tonic = (plugin + current.offset) % 12;
            if (tonic !== current.tonic) {
                expectedRoot.push(tonic);
                root.value().set(tonic, 12);
            }
        }
    }
    return {flush, reset};
}
