const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function value(initial) {
    let current = initial;
    return {get: () => current, set: v => { current = v; }, toggle: () => { current = !current; }, markInterested: () => {}};
}
function fixture() {
    const actions = [], notices = [], definitions = [];
    const recording = value(false), playing = value(false), position = value(0);
    const makeTrack = (type) => {
        const v = {exists: value(true), isGroup: value(type === 'Group'), trackType: value(type),
            isGroupExpanded: value(true), arm: value(false), canHoldNoteData: value(type === 'Instrument'),
            canHoldAudioData: value(type === 'Audio')};
        return {v, ...Object.fromEntries(Object.entries(v).map(([key, item]) => [key, () => item])),
            selectInEditor: () => actions.push('parent')};
    };
    const cursor = makeTrack('Instrument'), parent = makeTrack('Group');
    cursor.selectPrevious = () => actions.push('up');
    cursor.selectNext = () => actions.push('down');
    cursor.createParentTrack = () => parent;
    cursor.setCursorNavigationMode = mode => assert.equal(mode, 'GUI');
    let midi;
    const transport = {isArrangerRecordEnabled: () => recording, isPlaying: () => playing,
        play: () => {actions.push('play'); playing.set(true);},
        stop: () => {actions.push('stop'); playing.set(false);},
        record: () => {actions.push('record'); playing.set(true); recording.set(true);},
        rewind: () => {actions.push('home'); position.set(0);},
        setPosition: v => {actions.push(v); position.set(v);}};
    const host = {defineController: (...args) => definitions.push(args),
        defineMidiPorts: (a,b) => assert.deepEqual([a,b],[1,0]),
        addDeviceNameBasedDiscoveryPair: (a,b) => assert.equal(JSON.stringify([a,b]),
            JSON.stringify([['Keystation 61 MK3(Transport)'],[]])),
        createTransport: () => transport,
        createCursorTrack: (id,name,sends,scenes,follow) => {
            assert.equal(follow,true);
            return cursor;
        },
        getMidiInPort: i => {assert.equal(i,0); return {setMidiCallback: cb => {midi=cb;}};},
        showPopupNotification: s => notices.push(s)};
    const root = path.resolve(__dirname,'..');
    const context = vm.createContext({host,loadAPI: () => {},println: () => {}, Java: {type: name => {
        assert.equal(name, 'com.bitwig.extension.controller.api.CursorNavigationMode');
        return {GUI: 'GUI'};
    }}});
    context.load = name => vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),context);
    context.load('Keystation.control.js'); context.init();
    const tap = note => {midi(0x90,note,127); midi(0x80,note,0);};
    return {midi,tap,actions,notices,recording,playing,position,cursor,parent,context};
}
{
    const f=fixture();
    f.tap(94); f.tap(94); assert.deepEqual(f.actions,['play']);
    f.tap(93); f.tap(95); assert.equal(f.recording.get(),true);
    f.tap(95); assert.equal(f.recording.get(),false); assert.equal(f.playing.get(),true);
    f.tap(95); f.tap(93); assert.equal(f.recording.get(),false); assert.equal(f.playing.get(),false);
    f.tap(96); f.tap(97); assert.deepEqual(f.actions.slice(-2),['up','down']);
    // A leaf folds its immediate parent and selects it on collapse.
    f.position.set(12);
    f.tap(98); assert.equal(f.parent.v.isGroupExpanded.get(),false);
    assert.equal(f.actions.at(-1),'parent');
    f.tap(99); assert.equal(f.parent.v.isGroupExpanded.get(),true);
    f.tap(100); assert.equal(f.cursor.v.arm.get(),true);
    assert.equal(f.recording.get(),false); assert.equal(f.playing.get(),false);
    f.tap(100); assert.equal(f.cursor.v.arm.get(),false);
    assert.equal(f.position.get(),12); // No transport seeking remains.

}
{
    const f=fixture();
    f.midi(0x90,97,127); f.midi(0x90,97,127); assert.deepEqual(f.actions,['down']);
    f.midi(0x90,97,0); f.midi(0x90,97,1); assert.deepEqual(f.actions,['down','down']);
    f.context.exit(); f.midi(0x90,97,1); assert.equal(f.actions.length,3);
}
{
    const f=fixture(); f.tap(95); f.actions.length=0;
    for(let n=96;n<=100;n++) f.tap(n);
    assert.deepEqual(f.actions,[]); assert.equal(f.notices.length,5);
}
{
    const f=fixture();
    for(let ch=1;ch<16;ch++) for(let n=93;n<=100;n++) f.midi(0x90+ch,n,127);
    for(let n=0;n<128;n++) if(n<93 || n>100) f.tap(n);
    for(const s of [0x80,0xb0,0xe0,0xf8,0xff,-1,NaN]) f.midi(s,94,127);
    for(const n of [-1,128,94.5,NaN]) f.midi(0x90,n,127);
    for(const v of [-1,128,NaN]) f.midi(0x90,94,v);
    assert.deepEqual(f.actions,[]);
}
{
    const f=fixture();
    f.cursor.v.isGroup.set(true); f.cursor.v.trackType.set('Group');
    f.tap(98); assert.equal(f.cursor.v.isGroupExpanded.get(),false);
    assert.equal(f.parent.v.isGroupExpanded.get(),true);
    f.tap(99); assert.equal(f.cursor.v.isGroupExpanded.get(),true);
    f.tap(100); assert.equal(f.cursor.v.arm.get(),false);
    assert.deepEqual(f.actions,[]); assert.equal(f.notices.length,1);
}
{
    const f=fixture();
    f.parent.v.trackType.set('Master'); // Top-level leaf must not fold the project root.
    f.tap(98); f.tap(99); assert.deepEqual(f.actions,[]);
    assert.equal(f.parent.v.isGroupExpanded.get(),true);
    f.parent.v.trackType.set('Group'); f.parent.v.exists.set(false);
    f.tap(98); f.tap(99); assert.deepEqual(f.actions,[]);
    f.cursor.v.exists.set(false);
    f.tap(98); f.tap(99); f.tap(100);
    assert.equal(f.cursor.v.arm.get(),false);
}
for (const type of ['Audio','Instrument','Hybrid','Master','Effect']) {
    const f=fixture();
    f.cursor.v.trackType.set(type);
    f.cursor.v.canHoldNoteData.set(type==='Instrument' || type==='Hybrid');
    f.cursor.v.canHoldAudioData.set(type==='Audio' || type==='Hybrid');
    f.midi(0x90,100,127); f.midi(0x90,100,127); f.midi(0x90,100,0);
    assert.equal(f.cursor.v.arm.get(),['Audio','Instrument','Hybrid'].includes(type));
    f.tap(100); assert.equal(f.cursor.v.arm.get(),false);
    assert.deepEqual(f.actions,[]);
}
{
    const f=fixture();
    f.tap(100); f.tap(95); // Manual arm followed by actual recording.
    for(let n=96;n<=100;n++) f.tap(n);
    assert.equal(f.cursor.v.arm.get(),true);
    assert.equal(f.parent.v.isGroupExpanded.get(),true);
    f.tap(95); // Punch out without clearing manual arm or stopping playback.
    assert.equal(f.recording.get(),false); assert.equal(f.playing.get(),true);
    f.tap(100); assert.equal(f.cursor.v.arm.get(),false);
    f.tap(93); assert.equal(f.playing.get(),false);
}
console.log('PASS: Keystation folders, manual arm, recording, edge gating, isolation, GUI navigation, safety');
