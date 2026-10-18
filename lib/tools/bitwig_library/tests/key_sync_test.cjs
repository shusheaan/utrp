const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../Library.key-sync.js'), 'utf8'), context);
function value(initial) { return {current:initial, get(){return this.current;}, markInterested(){}}; }
function parameter(name, count, names, initial) {
    const n=value(name), c=value(count), ns=value(names), v=value(initial), writes=[];
    Object.assign(v, {discreteValueCount:()=>c, discreteValueNames:()=>ns,
        set:(index,resolution)=>writes.push([index,resolution])});
    return {name:()=>n, value:()=>v, n,c,ns,v,writes};
}
const modes = ['Chromatic','Major','Minor','Dorian','Phrygian','Lydian','Mixolydian','Locrian',
    'Harmonic Minor','Double Harmonic Minor','Melodic Minor','Major Pentatonic','Minor Triad'];
const offsets = [null,0,9,2,4,5,7,11];
function setMode(f, index) { f.scale.v.current=index/(modes.length-1); }
function fixture(tonic=1, mode=2, plugin=0) {
    const root=parameter('Root Key',12,[],tonic/11), scale=parameter('Scale',modes.length,modes,mode/(modes.length-1));
    const callbacks={}, writes=[], warnings=[]; let allowed=true, playing=false;
    const key='CONTENTS/PID81aea370', sounding='CONTENTS/sounding';
    const device={addDirectParameterIdObserver:cb=>callbacks.ids=cb,
        addDirectParameterNameObserver:(size,cb)=>callbacks.name=cb,
        addDirectParameterNormalizedValueObserver:cb=>{assert.ok(callbacks.ids);callbacks.value=cb;},
        setDirectParameterValueNormalized:(id,index,resolution)=>writes.push([id,index,resolution])};
    const sync=context.createLibraryKeySync({createCursorRemoteControlsPage:()=>({getParameter:i=>[root,scale][i]})},
        device,()=>allowed,()=>!playing,m=>warnings.push(m));
    callbacks.ids([key,sounding]); callbacks.name(key,'Key'); callbacks.name(sounding,'Sounding (read only)');
    callbacks.value(key,plugin/11); callbacks.value(sounding,0);
    return {root,scale,sync,callbacks,writes,warnings,key,sounding,allow:v=>allowed=v,playing:v=>playing=v,
        plugin:v=>callbacks.value('CONTENTS/ROOT_GENERIC_MODULE/PID81aea370',v/11),
        settle:()=>{if(writes.length) callbacks.value(key,writes.at(-1)[1]/11);
            if(root.writes.length) root.v.current=root.writes.at(-1)[0]/11; sync.flush();}};
}
for (const mode of [1,2,3,4,5,6,7]) for(let tonic=0;tonic<12;tonic++) {
    const f=fixture(tonic,mode); f.sync.flush(); f.settle();
    const major=(tonic-offsets[mode]+12)%12;
    assert.deepEqual(f.writes,major===0?[]:[[f.key,major,12]]);
    assert.equal(f.root.writes.length,0); assert.equal(f.scale.writes.length,0);
    for(let key=0;key<12;key++) {
        f.plugin(key); f.sync.flush(); f.settle();
        assert.equal(Math.round(f.root.v.current*11),(key+offsets[mode])%12);
    }
    const counts=[f.writes.length,f.root.writes.length];
    for(let i=0;i<100;i++)f.sync.flush();
    assert.deepEqual([f.writes.length,f.root.writes.length],counts);
}
console.log('PASS: 84 startup keys, host priority, seven modes, 1008 plugin selections, no echo loop');
{
    const f=fixture();f.sync.flush();f.settle();
    for(let key=0;key<12;key++) {f.root.v.current=key/11;f.sync.flush();f.settle();
        assert.equal(f.writes.at(-1)[1],(key+3)%12);}
    setMode(f,1); f.sync.flush(); f.settle(); assert.equal(f.writes.at(-1)[1],11);
    f.root.v.current=4/11; f.plugin(7); f.sync.flush();assert.equal(f.writes.at(-1)[1],4);
    assert.equal(f.root.writes.length,0);
}
{
    const f=fixture(); f.playing(true); f.sync.flush();assert.equal(f.writes.length,0);
    f.root.v.current=6/11; f.sync.flush(); f.playing(false); f.callbacks.value(f.sounding,1);f.sync.flush();
    assert.equal(f.writes.length,0); f.callbacks.value(f.sounding,0); f.sync.flush();assert.equal(f.writes[0][1],9);
    f.settle();f.root.v.current=3/11; f.playing(true);f.sync.flush();f.sync.reset();f.playing(false);f.sync.flush();
    assert.equal(f.writes.at(-1)[1],6);
}
{
    const f=fixture();f.allow(false);f.sync.flush();assert.equal(f.writes.length,0);
    f.allow(true);f.root.n.current='Volume';f.sync.flush();assert.equal(f.writes.length,0);
    f.root.n.current='Root Key';f.root.c.current=13;f.sync.flush();assert.equal(f.writes.length,0);
    f.root.c.current=12;f.scale.v.current=1;f.sync.flush();f.sync.flush();assert.equal(f.warnings.length,1);
    f.plugin(7);f.sync.flush();assert.equal(f.writes.length,0);assert.equal(f.root.writes.length,0);
    setMode(f,2);f.sync.flush();assert.equal(f.writes[0][1],4);
}
for(const bad of [NaN,Infinity,-1,1.1,undefined,0.5,'','C Minor']) {
    const f=fixture();f.callbacks.value(f.key,bad);f.sync.flush();assert.equal(f.writes.length,0);
    const g=fixture();g.root.v.current=bad;g.sync.flush();assert.equal(g.writes.length,0);
}
{
    const f=fixture();f.sync.flush();f.settle();
    f.callbacks.value('OTHER/ROOT_GENERIC_MODULE/PID81aea370',0);f.sync.flush();assert.equal(f.root.writes.length,0);
    f.callbacks.ids([]);f.sync.flush();assert.equal(f.writes.length,1);
    f.callbacks.ids(['CONTENTS/ROOT_GENERIC_MODULE/PID81aea370',f.sounding]);
    f.callbacks.name(f.key,'Key');f.callbacks.name(f.sounding,'Sounding (read only)');
    f.callbacks.value(f.sounding,0);f.plugin(0);f.sync.flush();
    assert.equal(f.writes.at(-1)[0],'CONTENTS/ROOT_GENERIC_MODULE/PID81aea370');
    f.callbacks.name(f.key,'Other');f.plugin(0);f.sync.flush();assert.equal(f.writes.length,2);
}
console.log('PASS: host edits, conflict priority, delayed echoes, playback/held-note deferral, invalid values, unsupported modes, scope/mapping guards, device aliases/replacement');
{
    const f=fixture(9,2,0);f.sync.flush();
    f.plugin(1);f.sync.flush();f.plugin(2);f.sync.flush();
    assert.deepEqual(f.root.writes,[[10,12],[11,12]]);
    f.root.v.current=10/11;f.sync.flush();f.root.v.current=11/11;f.sync.flush();
    assert.equal(f.writes.length,0);
    f.root.v.current=1/11;f.sync.flush();f.root.v.current=2/11;f.sync.flush();
    f.plugin(4);f.sync.flush();f.plugin(5);f.sync.flush();
    assert.equal(f.root.writes.length,2);
}
console.log('PASS: multiple in-flight writes acknowledge in order without reversing user edits');

// Every host root and mode change must map the exact pitch-class set, not only a label.
const majorIntervals=[0,2,4,5,7,9,11];
const modeIntervals={
    1:[0,2,4,5,7,9,11], 2:[0,2,3,5,7,8,10], 3:[0,2,3,5,7,9,10],
    4:[0,1,3,5,7,8,10], 5:[0,2,4,6,7,9,11], 6:[0,2,4,5,7,9,10],
    7:[0,1,3,5,6,8,10]
};
for(let from=1;from<=7;from++) for(let to=1;to<=7;to++) for(let tonic=0;tonic<12;tonic++) {
    const f=fixture(tonic,from);f.sync.flush();f.settle();
    setMode(f,to);f.root.v.current=tonic/11;f.sync.flush();f.settle();
    const key=f.writes.length ? f.writes.at(-1)[1] : 0;
    assert.equal(key,(tonic-offsets[to]+12)%12);
    const parentNotes=majorIntervals.map(n=>(n+key)%12).sort((a,b)=>a-b);
    const modeNotes=modeIntervals[to].map(n=>(n+tonic)%12).sort((a,b)=>a-b);
    assert.deepEqual(parentNotes,modeNotes);
    assert.equal(f.scale.writes.length,0);
}
for(const mode of [0,8,9,10,11,12]) {
    const f=fixture(2,mode,0);f.sync.flush();f.plugin(7);f.sync.flush();
    assert.equal(f.writes.length,0);assert.equal(f.root.writes.length,0);assert.equal(f.scale.writes.length,0);
    assert.equal(f.warnings.length,1);
    setMode(f,3);f.sync.flush();f.settle();
    assert.equal(f.writes.at(-1)[1],0); // D Dorian -> C major pitch set
    f.plugin(2);f.sync.flush();assert.deepEqual(f.root.writes.at(-1),[4,12]); // E Dorian
}
console.log('PASS: 588 host mode/root transitions, exact pitch sets, unsupported scales pause and resume');
