-- REAPER-only audition manager. No keyboard hooks; Chord Lab owns all MIDI logic.
local section='utrp.library'
local existing=reaper.GetExtState(section,'running')
if existing~='' then reaper.SetExtState(section,'stop',existing,false);return end
local project=reaper.EnumProjects(-1,'')
local input,entries=nil,{}
for i=0,reaper.CountTracks(project)-1 do
  local t=reaper.GetTrack(project,i)
  local _,is_input=reaper.GetSetMediaTrackInfo_String(t,'P_EXT:utrp_library_input','',false)
  local _,patch=reaper.GetSetMediaTrackInfo_String(t,'P_EXT:utrp_patch','',false)
  if is_input=='1' then assert(not input,'Multiple library inputs');input=t end
  if patch~='' then
    local ok,name=reaper.TrackFX_GetFXName(t,0)
    assert(ok and name:find('Surge XT',1,true),'Expected Surge XT as first FX: '..patch)
    entries[#entries+1]={track=t,solo=false,guid=reaper.TrackFX_GetFXGUID(t,0)}
  end
end
assert(input and #entries>0,'Open synth.rpp first')
local token=reaper.genGuid()
reaper.SetExtState(section,'running',token,false)
local active,deadline,initialized,last_selected=nil,0,false,nil
local function show_audition(target)
  if reaper.GetToggleCommandState(40377)~=1 then reaper.Main_OnCommand(40377,0) end
  reaper.TrackFX_Show(target,0,3)
  -- Leave computer-keyboard focus in Chord Lab, not in the synth editor.
  for i=0,reaper.TrackFX_GetRecCount(input)-1 do
    local fx=i|0x1000000
    local ok,ident=reaper.TrackFX_GetNamedConfigParm(input,fx,'fx_ident')
    if ok and ident=='ChordLab/chordlab.jsfx' then
      reaper.TrackFX_Show(input,fx,3);break
    end
  end
end
local function route(target)
  -- Disconnect MIDI first; unload the old synth before loading the new one.
  for i=0,reaper.GetTrackNumSends(input,0)-1 do
    reaper.SetTrackSendInfo_Value(input,0,i,'B_MUTE',1)
  end
  for _,e in ipairs(entries) do
    local enabled=e.track==target
    if not enabled and not reaper.TrackFX_GetOffline(e.track,0) then
      reaper.TrackFX_SetOffline(e.track,0,true)
    end
    reaper.SetMediaTrackInfo_Value(e.track,'I_SOLO',enabled and 2 or 0)
    e.solo=enabled
  end
  if target and reaper.TrackFX_GetOffline(target,0) then
    reaper.TrackFX_SetOffline(target,0,false)
  end
  for i=0,reaper.GetTrackNumSends(input,0)-1 do
    local dest=reaper.GetTrackSendInfo_Value(input,0,i,'P_DESTTRACK')
    if dest==target then reaper.SetTrackSendInfo_Value(input,0,i,'B_MUTE',0) end
  end
end
local function cleanup()
  if reaper.GetExtState(section,'running')~=token then return end
  local chord=reaper.GetExtState('utrp.chordlab','running')
  if chord~='' then reaper.SetExtState('utrp.chordlab','stop',chord,false) end
  reaper.DeleteExtState(section,'running',false)
  reaper.DeleteExtState(section,'stop',false)
end
reaper.atexit(cleanup)
local function tick()
  if reaper.EnumProjects(-1,'')~=project or reaper.GetExtState(section,'stop')==token then return end
  if not reaper.ValidatePtr2(project,input,'MediaTrack*') then return end
  if reaper.time_precise()<deadline then reaper.defer(tick);return end
  deadline=reaper.time_precise()+.1
  local selected=reaper.GetSelectedTrack(project,0)
  local changed_selection=selected~=last_selected
  last_selected=selected
  local chosen,first,clicked=nil,nil,nil
  for _,e in ipairs(entries) do
    if not reaper.ValidatePtr2(project,e.track,'MediaTrack*') then return end
    if reaper.TrackFX_GetFXGUID(e.track,0)~=e.guid then return end
    local solo=reaper.GetMediaTrackInfo_Value(e.track,'I_SOLO')>0
    if solo then first=first or e.track;if not e.solo then chosen=e.track end end
    if changed_selection and e.track==selected then clicked=e.track end
  end
  chosen=clicked or chosen or first
  if chosen~=active or not initialized then
    if active and active~=chosen then reaper.TrackFX_Show(active,0,2) end
    route(chosen);active=chosen;initialized=true
    if chosen then show_audition(chosen) end
  elseif clicked then
    show_audition(clicked)
  end
  reaper.defer(tick)
end
-- The fixed source remains the only armed track. Selecting synths never adds Input FX.
reaper.SetOnlyTrackSelected(input)
local chord=reaper.GetExtState('utrp.chordlab','running')
if chord=='' then
  local action=reaper.AddRemoveReaScript(true,0,reaper.GetResourcePath()..'/Scripts/ChordLab/Open Chord Lab.lua',true)
  assert(action>0);reaper.Main_OnCommand(action,0)
end
tick()
