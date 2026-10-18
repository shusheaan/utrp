const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function value(initial) {
    let current = initial;
    return {get: () => current, set: v => { current = v; }, markInterested: () => {}};
}
function fixture() {
    const actions = [], notices = [], definitions = [];
    const recording = value(false), playing = value(false), position = value(0);
    const numerator = value(4), denominator = value(4);
    let midi;
    const transport = {isArrangerRecordEnabled: () => recording, isPlaying: () => playing,
        getPosition: () => position, timeSignature: () => ({numerator: () => numerator, denominator: () => denominator}),
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
            return {selectPrevious: () => actions.push('up'), selectNext: () => actions.push('down')};
        },
        getMidiInPort: i => {assert.equal(i,0); return {setMidiCallback: cb => {midi=cb;}};},
        showPopupNotification: s => notices.push(s)};
    const root = path.resolve(__dirname,'..');
    const context = vm.createContext({host,loadAPI: () => {},println: () => {}});
    context.load = name => vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),context);
    context.load('Keystation.control.js'); context.init();
    const tap = note => {midi(0x90,note,127); midi(0x80,note,0);};
    return {midi,tap,actions,notices,recording,playing,position,numerator,denominator,context};
}
{
    const f=fixture();
    f.tap(94); f.tap(94); assert.deepEqual(f.actions,['play']);
    f.tap(93); f.tap(95); assert.equal(f.recording.get(),true);
    f.tap(95); assert.equal(f.recording.get(),false); assert.equal(f.playing.get(),true);
    f.tap(95); f.tap(93); assert.equal(f.recording.get(),false); assert.equal(f.playing.get(),false);
    f.tap(96); f.tap(97); assert.deepEqual(f.actions.slice(-2),['up','down']);
    f.tap(98); assert.equal(f.position.get(),0);
    f.tap(99); assert.equal(f.position.get(),4);
    f.numerator.set(6); f.denominator.set(8); f.tap(99); assert.equal(f.position.get(),7);
    f.tap(98); assert.equal(f.position.get(),4);
    f.tap(100); assert.equal(f.position.get(),0);
    f.denominator.set(0); f.tap(99); assert.equal(f.position.get(),0);
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
console.log('PASS: Keystation captured mapping, edge gating, isolation, navigation, record safety');
