const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function value(initial) {
    let current = initial;
    return {get:()=>current,set:v=>{current=v;},markInterested:()=>{}};
}
function fixture({projectName='Library',record=false,full=false,apply=true,bankMaster=false}={}) {
    const tasks=[],logs=[],writes=[];
    const config={project:'Library',signature:'CHORD LAB - shared MIDI input',capacity:8,
        sound_db:-2,bus_db:0,preserve:['GUITAR - raw detection'],unity:['CHORD LAB - shared MIDI input'],
        raw_db_scale:60,verify_tolerance_db:0.06};
    const makeTrack=(name,type,exists=true)=>{
        const state={name:value(name),trackType:value(type),exists:value(exists),arm:value(false),
            monitorMode:value('OFF'),isActivated:value(false),mute:value(false),pan:value(.5)};
        let raw=name==='GUITAR - raw detection'?0:Math.pow(10,-10/60);
        const track=Object.fromEntries(Object.entries(state).map(([k,v])=>[k,()=>v]));
        track.volume=()=>({getRaw:()=>raw,setRaw:v=>{raw=v;writes.push(name);},markInterested:()=>{},
            displayedValue:()=>({get:()=>raw===0?'-inf dB':(60*Math.log10(raw)).toFixed(1)+' dB',markInterested:()=>{}})});
        return track;
    };
    const tracks=[makeTrack(config.signature,'Instrument'),makeTrack('Keys','Group'),
        makeTrack('Piano','Instrument'),makeTrack('GUITAR - raw detection','Audio'),
        makeTrack('Guitar','Audio'),...Array.from({length:3},()=>makeTrack('','Audio',full))];
    const master=makeTrack('Master','Master');
    if(bankMaster) tracks[5]=master;
    const host={createApplication:()=>({projectName:()=>value(projectName),getAction:()=>({invoke:()=>{}})}),
        createTransport:()=>({isArrangerRecordEnabled:()=>value(record)}),
        createTrackBank:()=>({setContentFilter:()=>{},setSkipDisabledItems: v=>assert.equal(v,false),getItemAt:i=>tracks[i]}),
        createMasterTrack:()=>master,scheduleTask:fn=>tasks.push(fn)};
    const context=vm.createContext({host,config,apply,println:s=>logs.push(s),Java:{type:()=>({ALL_CHANNELS:'all'})}});
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../levels.js'),'utf8'),context);
    vm.runInContext('scheduleLibraryLevels(host,config,apply)',context);
    while(tasks.length)tasks.shift()();
    return {tracks,master,writes,logs};
}
{
 const f=fixture();assert.equal(f.writes.length,5);assert.ok(f.logs.some(s=>s.includes('LEVELS PASS')));
 assert.equal(f.tracks[3].volume().getRaw(),0);assert.equal(f.master.volume().getRaw(),1);
 assert.equal(f.tracks[2].volume().displayedValue().get(),'-2.0 dB');
}
{
 const f=fixture({bankMaster:true});assert.equal(f.writes.length,5);
 assert.equal(f.writes.filter(n=>n==='Master').length,1);
 assert.ok(f.logs.some(s=>s.includes('LEVELS PASS')));
}
for(const args of [{projectName:'Song'},{record:true},{full:true},{apply:false}]) {
 const f=fixture(args);assert.deepEqual(f.writes,[]);
}
console.log('PASS: one-shot levels, scope, recording guard, capacity, protected raw track, state preservation, read-only verification');
