-- Pure host mock: selection-driven editors, exclusive routing and lifecycle.
local tracks={
 {input='1',patch='',solo=0,offline=true,guid='input'},
 {input='',patch='one',solo=2,offline=false,guid='one'},
 {input='',patch='two',solo=0,offline=false,guid='two'},
 {input='',patch='',solo=0,offline=true,guid='folder'},
}
local sends={{target=tracks[2],mute=0},{target=tracks[3],mute=0}}
local ext,events,shown={},{},{}
local now,project,vkb=0,1,0
local selected,deferred,cleanup
local params={[6]=0,[7]=23}
local function key(section,name) return section..'/'..name end
reaper={
 GetExtState=function(s,k) return ext[key(s,k)] or '' end,
 SetExtState=function(s,k,v) ext[key(s,k)]=v end,
 DeleteExtState=function(s,k) ext[key(s,k)]=nil end,
 EnumProjects=function() return project end,
 CountTracks=function() return #tracks end,
 GetTrack=function(_,i) return tracks[i+1] end,
 GetSelectedTrack=function() return selected end,
 GetSetMediaTrackInfo_String=function(t,k) return true,k=='P_EXT:utrp_library_input' and t.input or t.patch end,
 -- Mixed library: the first sound is Surge, the second can be sfizz.
 TrackFX_GetFXName=function(t) return true,t==tracks[3] and 'LV2i: sfizz (SFZTools)' or 'CLAPi: Surge XT' end,
 TrackFX_GetInstrument=function() error('Offline FX cannot be identified by GetInstrument') end,
 TrackFX_GetFXGUID=function(t) return t.guid end,
 TrackFX_GetRecCount=function(t) assert(t==tracks[1]);return 1 end,
 TrackFX_GetParam=function(_,_,i) return assert(params[i]) end,
 TrackFX_SetParam=function(_,_,i,v) params[i]=v end,
 TrackFX_GetNamedConfigParm=function(t,fx,k)
  assert(t==tracks[1] and fx==0x1000000 and k=='fx_ident')
  return true,'ChordLab/chordlab.jsfx'
 end,
 genGuid=function() return 'session' end,
 GetTrackNumSends=function() return #sends end,
 SetTrackSendInfo_Value=function(_,_,i,_,v) sends[i+1].mute=v;events[#events+1]='mute'..i..':'..v end,
 GetTrackSendInfo_Value=function(_,_,i) return sends[i+1].target end,
 TrackFX_GetOffline=function(t) return t.offline end,
 TrackFX_GetFloatingWindow=function(t) return t.floating or nil end,
 TrackFX_Show=function(t,fx,mode)
  assert(fx==(t==tracks[1] and 0x1000000 or 0))
  assert(mode==2 or mode==3)
  if mode==3 and t~=tracks[1] then assert(not t.offline,'Show only after loading synth') end
  t.floating=mode==3
  shown[#shown+1]=t.guid..':'..mode
 end,
 TrackFX_SetOffline=function(t,_,v) t.offline=v;events[#events+1]=t.guid..':'..tostring(v) end,
 SetMediaTrackInfo_Value=function(t,k,v) assert(k=='I_SOLO');t.solo=v end,
 GetMediaTrackInfo_Value=function(t) return t.solo end,
 ValidatePtr2=function(_,t) return t.valid~=false end,
 time_precise=function() return now end,
 defer=function(f) deferred=f end,
 atexit=function(f) cleanup=f end,
 SetOnlyTrackSelected=function(t) assert(t==tracks[1]);selected=t end,
 GetResourcePath=function() return '/mock' end,
 AddRemoveReaScript=function(_,_,path)
  assert(path=='/mock/Scripts/ChordLab/Chord Lab mode.lua');return 1
 end,
 GetToggleCommandState=function(id) assert(id==40377);return vkb end,
 Main_OnCommand=function(id)
  if id==40377 then vkb=1-vkb
  else assert(id==1);ext['utrp.chordlab/running']='chord-session' end
 end,
}
local checks=0
local function check(value) assert(value);checks=checks+1 end
local function tick()
 now=now+1;local f=deferred;deferred=nil;assert(f);f()
end
dofile('lib/tools/library/Library mode.lua')
check(table.concat(events,',')=='mute0:1,mute1:1,two:true,mute0:0')
check(not tracks[2].offline and tracks[3].offline)
check(#shown==0 and vkb==0)
check(params[7]==27 and params[6]==1)
-- Selection loads the sound, then opens Surge and the shared Chord Lab.
selected=tracks[3];events={};shown={};tick()
check(table.concat(events,',')=='mute0:1,mute1:1,one:true,two:false,mute1:0')
check(tracks[2].solo==0 and tracks[3].solo==2)
check(sends[1].mute==1 and sends[2].mute==0)
check(table.concat(shown,',')=='two:3,input:3')
check(tracks[3].floating and tracks[1].floating)
-- A new selection includes VKB, even if the shared editor was already open.
check(vkb==1)
check(params[7]==27 and params[6]==2)
-- Polling must not reload synths, reopen a closed window or steal focus.
tracks[3].floating=false;tracks[1].floating=false
events={};shown={};vkb=0;tick()
check(#events==0 and #shown==0 and vkb==0)
check(not tracks[3].floating and not tracks[1].floating)
check(params[6]==2)
-- Album folders and the shared input do not change the sound.
selected=tracks[4];tick();selected=tracks[1];tick()
check(#events==0 and #shown==0 and tracks[3].solo==2)
-- Returning to the same active sound reopens editors without reloading the synth.
selected=tracks[3];tick()
check(#events==0 and table.concat(shown,',')=='two:3,input:3' and vkb==1)
-- Solo buttons remain an alternative to selection, without reopening VKB.
vkb=0;tracks[2].solo=2;events={};shown={};tick()
check(table.concat(events,',')=='mute0:1,mute1:1,two:true,one:false,mute0:0')
check(tracks[2].solo==2 and tracks[3].solo==0)
check(table.concat(shown,',')=='two:2' and vkb==0)
check(not tracks[3].floating)
-- Switching synths closes the old floating editor and opens only the chosen one.
selected=tracks[4];tick()
vkb=1;selected=tracks[3];shown={};tick()
check(table.concat(shown,',')=='two:3,input:3' and vkb==1)
selected=tracks[2];shown={};tick()
check(table.concat(shown,',')=='two:2,one:3,input:3' and vkb==1)
check(tracks[2].floating and not tracks[3].floating)
shown={};events={};tick();check(#shown==0 and #events==0)
-- A new selection restores a manually closed VKB while Chord Lab stays open.
vkb=0;selected=tracks[4];tick();selected=tracks[2];tick()
check(tracks[1].floating and vkb==1)
-- No Solo means silence, even while a synth track remains selected.
tracks[2].solo=0;tick()
check(tracks[2].offline and tracks[3].offline)
check(sends[1].mute==1 and sends[2].mute==1)
check(not tracks[2].floating and not tracks[3].floating)
events={};shown={};tick();check(#events==0 and #shown==0)
-- A simultaneous new selection wins over a manually changed Solo.
selected=tracks[4];tick()
tracks[3].solo=2;selected=tracks[2];tick()
check(tracks[2].solo==2 and tracks[3].solo==0)
check(not tracks[2].offline and tracks[3].offline)
project=2;tick();check(deferred==nil)
cleanup();check(ext['utrp.library/running']==nil)
check(ext['utrp.chordlab/stop']=='chord-session')
print('Library lifecycle: '..checks..' assertions passed')
