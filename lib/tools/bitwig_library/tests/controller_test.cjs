const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function value(initial) {
    let current = initial;
    const observers = [];
    return {get: () => current, markInterested: () => {},
        set: next => {current = next; observers.forEach(callback => callback(next));},
        addValueObserver: callback => {observers.push(callback); callback(current);}};
}
function fixture(name = 'Library', prefix = null) {
    const project = value(name), preference = value(true), tasks = [];
    const tracks = Array.from({length:128}, (_, i) => {
        const names = ['CHORD LAB - shared MIDI input', 'Basic Keys', '01 Acoustic Piano', '03 Suitcase EP', 'AG - 01 Glass Air', 'AG - 02 Soft Prism', 'AG - 03 Echo Bloom', 'AG - 04 Cloud Halo', 'GUITAR - raw detection', 'Custom instrument'];
        const v = {name:value(names[i] || ''), exists:value(i < 10), arm:value(false),
            isActivated:value(i < 3 || i === 8), monitorMode:value('OFF')};
        const d = {name:value(i === 0 ? 'Chord Lab' : i === 2 ? 'sfizz' : i === 3 ? 'Surge XT' : i >= 4 && i <= 7 ? 'Dragonfly Hall Reverb' : i === 8 ? 'Guitar Frontend' : ''),
            exists:value(i !== 1 && i < 9), isWindowOpen:value(false)};
        const empty = () => ({name:value(''), exists:value(false), isWindowOpen:value(false)});
        const prefixDevice = {name:value(prefix || ''), exists:value(prefix !== null), isWindowOpen:value(false)};
        const chain = i === 0 && prefix !== null ? [prefixDevice, d, empty(), empty()] : [d, empty(), empty(), empty()];
        if (i === 8 || i === 9) chain[1] = {name:value('Chord Lab'), exists:value(true), isWindowOpen:value(false)};
        if (i >= 4 && i <= 7) chain[1] = {name:value('Surge XT Effects'), exists:value(true), isWindowOpen:value(false)};
        let callback = () => {};
        return {...Object.fromEntries(Object.entries(v).map(([k, x]) => [k, () => x])),
            createDeviceBank: () => ({getItemAt: index => Object.fromEntries(Object.entries(chain[index]).map(([k,x]) => [k, () => x]))}),
            addIsSelectedInEditorObserver: cb => {callback = cb; cb(i === 2);},
            select: () => callback(true), v, d, chain};
    });
    const host = {defineController: () => {}, defineMidiPorts: () => {},
        createApplication: () => ({projectName: () => project}),
        getPreferences: () => ({getBooleanSetting: () => preference}),
        createTrackBank: () => ({getItemAt: i => tracks[i], setContentFilter: () => {}, setSkipDisabledItems: () => {}}),
        scheduleTask: (callback, delay) => tasks.push({callback, delay})};
    const root = path.resolve(__dirname, '..');
    const context = vm.createContext({host, loadAPI: () => {}, Java:{type: () => ({ALL_CHANNELS: 1})}});
    context.load = file => vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), context);
    vm.runInContext(fs.readFileSync(path.join(root, 'Library.control.js'), 'utf8'), context);
    const syncBindings = [];
    context.createLibraryKeySync = (root, device, allowed) => {
        syncBindings.push({device, allowed});
        return {flush: () => {}};
    };
    host.createTransport = () => ({isPlaying: () => value(false)});
    host.getProject = () => ({getRootTrackGroup: () => ({})});
    context.init();
    return {project, preference, tracks, tasks, syncBindings,
        drain: () => {while (tasks.length) tasks.shift().callback();}};
}
{
    const f = fixture(); f.drain();
    assert.equal(f.tracks[2].v.arm.get(), false);
    assert.equal(f.tracks[0].v.arm.get(), false);
    assert.equal(f.tracks[0].v.monitorMode.get(), 'ON');
    assert.equal(f.tracks[2].d.isWindowOpen.get(), true);
    assert.equal(f.tracks[0].d.isWindowOpen.get(), true);
    f.tracks[3].select(); f.drain();
    assert.equal(f.tracks[2].v.isActivated.get(), false);
    assert.equal(f.tracks[3].v.isActivated.get(), true);
    assert.equal(f.tracks[3].d.isWindowOpen.get(), true);
    f.tracks[1].select(); f.drain();
    assert.equal(f.tracks[3].v.isActivated.get(), true);
}
{
    const f = fixture('Other project'); f.drain(); f.tracks[3].select(); f.drain();
    assert.equal(f.tracks[3].v.isActivated.get(), false);
    assert.equal(f.tracks[0].d.isWindowOpen.get(), false);
}
{
    const f = fixture(); f.drain();
    f.tracks[3].select(); f.tracks[2].select(); f.drain();
    assert.equal(f.tracks[2].d.isWindowOpen.get(), true);
    assert.equal(f.tracks[3].d.isWindowOpen.get(), false);
    f.preference.set(false); f.tracks[3].select(); f.drain();
    assert.equal(f.tracks[3].v.isActivated.get(), false);
}
{
    const f = fixture(); f.drain(); f.tracks[3].select(); f.project.set('Other project'); f.drain();
    assert.equal(f.tracks[3].d.isWindowOpen.get(), false);
}
{
    const f = fixture(); f.drain();
    const editor = f.tracks[3].d.isWindowOpen;
    const set = editor.set;
    let attempts = 0;
    editor.set = next => { if (!next || ++attempts >= 3) set(next); };
    f.tracks[3].select();
    // Simulate activation restoring an old armed state before the delayed handler.
    f.tracks[3].v.arm.set(true);
    f.drain();
    assert.equal(attempts, 3);
    assert.equal(editor.get(), true);
    assert.equal(f.tracks[3].v.arm.get(), false);
    assert.equal(f.tracks[0].d.isWindowOpen.get(), true);
}
{
    const f = fixture('Library', 'Note Receiver'); f.drain();
    assert.equal(f.tracks[0].chain[0].isWindowOpen.get(), false);
    assert.equal(f.syncBindings[0].allowed(), false);
    assert.equal(f.syncBindings[1].allowed(), true);
    assert.equal(f.tracks[0].d.isWindowOpen.get(), true);
    f.tracks[3].select(); f.drain();
    assert.equal(f.tracks[3].v.arm.get(), false);
    assert.equal(f.tracks[0].d.isWindowOpen.get(), true);
    assert.equal(f.tracks[0].chain[0].isWindowOpen.get(), false);
}
{
    const f = fixture('Library', 'Unexpected effect'); f.drain();
    assert.equal(f.tracks[2].v.arm.get(), false);
    assert.equal(f.tracks[0].d.isWindowOpen.get(), false);
}
console.log('PASS: receiver prefix, unsupported prefix rejected,  startup, exclusive audition, scope, group selection, rapid switching, disabled setting, project-switch cancellation, slow editor, restored arm');

{
    const f = fixture('Library', 'Note Receiver'); f.drain();
    const selected = [2, -1];
    for (const index of [4, 5, 6, 7, 2, 6, 3, 3, 7, 2]) {
        selected[index >= 4 ? 1 : 0] = index;
        f.tracks[index].select(); f.drain();
        for (let i = 2; i <= 7; i++) {
            const active = selected.includes(i);
            assert.equal(f.tracks[i].v.isActivated.get(), active);
            assert.equal(f.tracks[i].v.arm.get(), false);
            assert.equal(f.tracks[i].v.monitorMode.get(), active ? 'ON' : 'OFF');
        }
        assert.equal(f.tracks[8].v.isActivated.get(), true, 'Raw detector must stay active');
        assert.equal(f.tracks[0].d.isWindowOpen.get(), true, 'Shared display stays available');
        if (index >= 4) assert.equal(f.tracks[index].d.isWindowOpen.get(), true, 'Primary guitar FX editor opens with shared Chord Lab');
    }
}
console.log('PASS: MIDI and guitar groups audition independently without disabling raw detection');

{
    const f = fixture('Library', 'Note Receiver'); f.drain();
    f.tracks[0].d.isWindowOpen.set(false);
    f.tracks[2].d.isWindowOpen.set(false);
    f.tracks[2].select(); f.drain();
    assert.equal(f.tracks[0].d.isWindowOpen.get(), true);
    assert.equal(f.tracks[2].d.isWindowOpen.get(), true);
    f.tracks[5].select(); f.drain();
    f.tracks[5].chain[1].isWindowOpen.set(true);
    f.tracks[2].select(); f.drain();
    assert.equal(f.tracks[5].chain[1].isWindowOpen.get(), false);
    for (const index of [8, 9, 0]) {
        f.tracks[index].select(); f.drain();
        const device = index === 0 ? f.tracks[0].d : f.tracks[index].chain[1];
        assert.equal(device.isWindowOpen.get(), true);
        assert.equal(f.tracks[2].v.isActivated.get(), true, 'Display selection must not change audition');
        assert.equal(f.tracks[8].v.isActivated.get(), true, 'Raw detection stays active');
        assert.equal(f.tracks[8].v.arm.get(), false);
    }
    f.tracks[2].select(); f.drain();
    assert.equal(f.tracks[2].d.isWindowOpen.get(), true);
    assert.equal(f.tracks[8].chain[1].isWindowOpen.get(), false);
    assert.equal(f.tracks[9].chain[1].isWindowOpen.get(), false);
    f.tracks[3].select(); f.tracks[8].select(); f.drain();
    assert.equal(f.tracks[3].d.isWindowOpen.get(), false, 'Auxiliary selection cancels pending editor');
    assert.equal(f.tracks[8].chain[1].isWindowOpen.get(), true);
}
console.log('PASS: reselect, all FX editors closed, shared/raw/custom Chord Lab tracks, delayed editor cancellation');

// Recording projects must retain user arm/monitor/activation/editor states.
function trackSnapshot(f) {
    return f.tracks.map(t => ({active:t.v.isActivated.get(), arm:t.v.arm.get(),
        monitor:t.v.monitorMode.get(), editors:t.chain.map(d => d.isWindowOpen.get())}));
}
for (const name of ['Song', 'Loop Practice', 'Library Recording', 'library', 'My Library']) {
    const f = fixture(name);
    for (const i of [2,3,4]) {
        f.tracks[i].v.isActivated.set(true);
        f.tracks[i].v.arm.set(true);
        f.tracks[i].v.monitorMode.set('ON');
        f.tracks[i].d.isWindowOpen.set(true);
    }
    const before = trackSnapshot(f);
    f.drain();
    for (const track of f.tracks.slice(0, 10)) {track.select(); f.drain();}
    assert.deepEqual(trackSnapshot(f), before, `No Library automation in ${name}`);
    assert.ok(f.syncBindings.every(binding => !binding.allowed()));
}
{
    const f = fixture(); f.drain();
    f.tracks[3].select(); // Pending editor/arm writes must not leak into the next project.
    f.project.set('Recording');
    for (const i of [2,3,4]) {
        f.tracks[i].v.isActivated.set(true);
        f.tracks[i].v.arm.set(true);
        f.tracks[i].v.monitorMode.set('ON');
    }
    const before = trackSnapshot(f);
    f.drain(); f.tracks[4].select(); f.drain();
    assert.deepEqual(trackSnapshot(f), before);
}
console.log('PASS: recording projects preserve all track states; queued Library work cannot leak');

// Cross-group selections cancel old windows, not the other group's pending arm restore.
for (const auxiliary of [false, true]) {
    const f = fixture(); f.drain();
    f.tracks[3].select();
    f.tracks[3].v.arm.set(false);
    f.tracks[4].select();
    f.tracks[4].v.arm.set(false);
    f.tracks[5].select();
    f.tracks[5].v.arm.set(false);
    if (auxiliary) f.tracks[8].select();
    f.drain();
    for (let i = 2; i <= 7; i++) {
        const active = i === 3 || i === 5;
        assert.equal(f.tracks[i].v.isActivated.get(), active);
        assert.equal(f.tracks[i].v.arm.get(), false);
        assert.equal(f.tracks[i].v.monitorMode.get(), active ? 'ON' : 'OFF');
    }
    assert.equal(f.tracks[3].d.isWindowOpen.get(), false);
    assert.equal(f.tracks[5].d.isWindowOpen.get(), !auxiliary);
}
{
    const f = fixture(); f.drain();
    f.tracks[4].select(); f.drain();
    const before = trackSnapshot(f).slice(4, 8);
    f.tracks[3].select(); f.drain();
    const after = trackSnapshot(f).slice(4, 8);
    // Window focus follows selection, but the other group's routing is untouched.
    before.forEach(t => delete t.editors); after.forEach(t => delete t.editors);
    assert.deepEqual(after, before);
    f.tracks[3].v.arm.set(false);
    f.tracks[3].select(); f.drain();
    assert.equal(f.tracks[3].v.arm.get(), false, 'Reselect restores audition state');
}
for (const cancel of ['preference', 'project']) {
    const f = fixture(); f.drain();
    f.tracks[3].select(); f.tracks[4].select();
    if (cancel === 'preference') f.preference.set(false);
    else f.project.set('Recording');
    f.tracks[3].v.arm.set(false); f.tracks[4].v.arm.set(false);
    const before = trackSnapshot(f); f.drain();
    assert.deepEqual(trackSnapshot(f), before, 'Cancel both groups on ' + cancel);
}
console.log('PASS: cross-group deferred activation, auxiliary selection, reselect, both-group cancellation');

// Both groups use explicit monitoring, never record arm, including activation restore.
{
    const f = fixture(); f.drain();
    for (const index of [2, 3, 2, 4, 5, 6, 7, 4]) {
        f.tracks[index].select();
        f.tracks[index].v.arm.set(true); // Host restores an old armed state on activation.
        f.drain();
        assert.equal(f.tracks[index].v.isActivated.get(), true);
        assert.equal(f.tracks[index].v.monitorMode.get(), 'ON');
        assert.equal(f.tracks[index].v.arm.get(), false);
        if (index >= 4) assert.equal(f.tracks[2].v.isActivated.get(), true);
        assert.equal(f.tracks[2].v.arm.get(), false);
    }
}
console.log('PASS: MIDI and guitar monitoring without record arm');

// Never even transiently request record arm during startup or sound selection.
{
    const f = fixture();
    for (const track of f.tracks) {
        const original = track.v.arm.set;
        track.v.arm.set = next => {
            assert.equal(next, false, 'Audition must never request record arm');
            original(next);
        };
    }
    f.drain();
    for (const index of [2, 4, 3, 5, 6, 2, 7, 0, 8]) {
        f.tracks[index].select();
    }
    f.drain();
    assert.equal(f.tracks[2].v.monitorMode.get(), 'ON');
    assert.equal(f.tracks[7].v.monitorMode.get(), 'ON');
}
console.log('PASS: no transient auto-arm writes on startup or cross-group selection');
