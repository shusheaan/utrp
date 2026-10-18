-- User-authorized library audit. Master silenced; fixture removed on every exit.
local project,path=reaper.EnumProjects(-1,'')
assert(path=='/home/shu/storage/daw/synth.rpp','Only the migrated library')
assert(reaper.GetExtState('utrp.library','running')~='','Start library first')
local source=reaper.GetTrack(project,0)
assert(reaper.TrackFX_GetRecCount(source)==1)
local _,ident=reaper.TrackFX_GetNamedConfigParm(source,0x1000000,'fx_ident')
assert(ident=='org.utrp.chordlab')
local master=reaper.GetMasterTrack(project)
local volume=reaper.GetMediaTrackInfo_Value(master,'D_VOL')
local muted=reaper.GetMediaTrackInfo_Value(master,'B_MUTE')
local _,saved=reaper.TrackFX_GetNamedConfigParm(source,0x1000000,'clap_chunk')
local initial=reaper.GetSelectedTrack(project,0)
local log=assert(io.open('/tmp/synth-clap-migration/audio.tsv','w'))
log:write('index\tpatch\tchord_peak\tmidi_peak\tonline\tsolo\tarmed\twindows\n')
local entries={}
for i=1,reaper.CountTracks(project)-1 do
 local t=reaper.GetTrack(project,i)
 local _,id=reaper.GetSetMediaTrackInfo_String(t,'P_EXT:utrp_patch','',false)
 if id~='' then entries[#entries+1]={track=t,id=id,index=i} end
end
reaper.gmem_attach('UTRP_Library_CLAP_Audit')
local serial=0
local function send(status,note,value)
 serial=serial+1
 reaper.gmem_write(1,1);reaper.gmem_write(10,0);reaper.gmem_write(11,status)
 reaper.gmem_write(12,note);reaper.gmem_write(13,value);reaper.gmem_write(0,serial)
end
reaper.gmem_write(0,0);reaper.gmem_write(1,0)
local fixture=nil
local closed=false
local function cleanup()
 if closed then return end
 closed=true
 if reaper.ValidatePtr2(project,source,'MediaTrack*') then
  if fixture then
   for i=reaper.TrackFX_GetRecCount(source)-1,0,-1 do
    if reaper.TrackFX_GetFXGUID(source,i|0x1000000)==fixture then reaper.TrackFX_Delete(source,i|0x1000000) end
   end
  end
  reaper.TrackFX_SetNamedConfigParm(source,0x1000000,'clap_chunk',saved)
 end
 if reaper.ValidatePtr2(project,master,'MediaTrack*') then
  reaper.SetMediaTrackInfo_Value(master,'D_VOL',volume)
  reaper.SetMediaTrackInfo_Value(master,'B_MUTE',muted)
 end
 if reaper.ValidatePtr2(project,initial,'MediaTrack*') then reaper.SetOnlyTrackSelected(initial) end
 log:close()
end
reaper.atexit(cleanup)
reaper.SetMediaTrackInfo_Value(master,'D_VOL',0)
reaper.SetMediaTrackInfo_Value(master,'B_MUTE',1)
assert(reaper.TrackFX_AddByName(source,'ChordLabMigration/audit_input.jsfx',true,-1)==1)
fixture=reaper.TrackFX_GetFXGUID(source,0x1000001)
reaper.TrackFX_CopyToTrack(source,0x1000001,source,0x1000000,true)
local step,phase,deadline,peak,chord=1,'select',0,0,0
local function finish(message)
 local f=assert(io.open('/tmp/synth-clap-migration/audio-result.txt','w'))
 f:write(message);f:close();cleanup()
end
local tick
local function safe()
 local ok,err=pcall(tick)
 if not ok then finish('FAIL '..tostring(err)) end
end
tick=function()
 assert(reaper.EnumProjects(-1,'')==project,'Project changed during audit')
 local e=entries[step];local now=reaper.time_precise()
 if phase=='select' then
  reaper.SetOnlyTrackSelected(e.track);deadline=now+.8;phase='settle'
 elseif phase=='settle' and now>=deadline then
  assert(not reaper.TrackFX_GetOffline(e.track,0),'Instrument offline')
  send(0x9f,74,64);peak=0;deadline=now+1.3;phase='chord'
 elseif phase=='chord' or phase=='midi' then
  peak=math.max(peak,reaper.Track_GetPeakInfo(e.track,0),reaper.Track_GetPeakInfo(e.track,1))
  if now>=deadline then
   if phase=='chord' then
    chord=peak;send(0x8f,74,0);phase='gap';deadline=now+.2
   else
    local online,solo,armed,windows=0,0,0,0
    for _,v in ipairs(entries) do
     if not reaper.TrackFX_GetOffline(v.track,0) then online=online+1 end
     if reaper.GetMediaTrackInfo_Value(v.track,'I_SOLO')>0 then solo=solo+1 end
     if reaper.TrackFX_GetFloatingWindow(v.track,0) then windows=windows+1 end
    end
    for i=0,reaper.CountTracks(project)-1 do armed=armed+reaper.GetMediaTrackInfo_Value(reaper.GetTrack(project,i),'I_RECARM') end
    assert(online==1 and solo==1 and armed==1 and windows==1,'Routing/editor isolation failure')
    assert(reaper.TrackFX_GetOpen(source,0x1000001),'CLAP editor missing')
    assert(reaper.GetToggleCommandState(40377)==0,'Legacy VKB unexpectedly active')
    -- Meter taps can be pre-fader; verify explicit output protection instead.
    assert(reaper.GetMediaTrackInfo_Value(master,'D_VOL')==0 and
      reaper.GetMediaTrackInfo_Value(master,'B_MUTE')==1,'Master output protection changed')
    log:write(e.index,'\t',e.id,'\t',chord,'\t',peak,'\t',online,'\t',solo,'\t',armed,'\t',windows,'\n');log:flush()
    assert(chord>1e-8 and peak>1e-8,'Silent patch '..e.id)
    send(0x80,60,0);phase='release';deadline=now+.2
   end
  end
 elseif phase=='gap' and now>=deadline then
  send(0x90,60,88);peak=0;deadline=now+1;phase='midi'
 elseif phase=='release' and now>=deadline then
  step=step+1;phase='select'
  if step>#entries then finish('PASS '..#entries..' patches, chord + MIDI audio, exclusive routing, no VKB');return end
 end
 reaper.defer(safe)
end
reaper.defer(safe)
