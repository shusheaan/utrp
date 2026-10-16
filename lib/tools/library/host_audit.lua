-- Manual acceptance action. Run only on a /tmp/ copy, with Library mode active.
local project,path=reaper.EnumProjects(-1,'')
assert(path:sub(1,5)=='/tmp/','Audit only a disposable project copy')
assert(reaper.GetExtState('utrp.library','running')~='','Start Library mode first')
local source=reaper.GetTrack(project,0)
local master=reaper.GetMasterTrack(project)
local old_volume=reaper.GetMediaTrackInfo_Value(master,'D_VOL')
local tracks={}
for i=0,reaper.CountTracks(project)-1 do
  local t=reaper.GetTrack(project,i)
  local _,id=reaper.GetSetMediaTrackInfo_String(t,'P_EXT:utrp_patch','',false)
  if id~='' then tracks[#tracks+1]={track=t,id=id,index=i} end
end
assert(#tracks==86,'Unexpected library inventory')
local log=assert(io.open('/tmp/library-audio-results.tsv','w'))
log:write('index\tpatch\tcomputer_peak\tmidi_message_peak\theld\tonline\tsolo\tarmed\tsurge_windows\taudio_xrun\tmedia_xrun\n');log:flush()
local index,phase,deadline,peak,computer_peak=1,'select',0,0,0
local closed=false
local function release()
  reaper.StuffMIDIMessage(0,0x8f,74,0)
  reaper.StuffMIDIMessage(0,0x80,60,0)
end
local function cleanup()
  if closed then return end
  closed=true;release()
  if reaper.ValidatePtr2(project,master,'MediaTrack*') then
    reaper.SetMediaTrackInfo_Value(master,'D_VOL',old_volume)
  end
  log:close()
end
reaper.atexit(cleanup)
reaper.SetMediaTrackInfo_Value(master,'D_VOL',0)
local function tick()
  if reaper.EnumProjects(-1,'')~=project then cleanup();return end
  local now=reaper.time_precise();local current=tracks[index]
  if phase=='select' then
    reaper.SetOnlyTrackSelected(current.track)
    deadline=now+.6;phase='settle'
  elseif phase=='settle' and now>=deadline then
    assert(not reaper.TrackFX_GetOffline(current.track,0),'Manager failed to activate synth')
    reaper.StuffMIDIMessage(0,0x9f,74,88)
    peak=0;deadline=now+2;phase='computer'
  elseif phase=='computer' or phase=='hardware' then
    peak=math.max(peak,reaper.Track_GetPeakInfo(current.track,0),reaper.Track_GetPeakInfo(current.track,1))
    if now>=deadline then
      if phase=='computer' then
        computer_peak=peak;release();phase='gap';deadline=now+.3
      else
        local online,solo,armed,windows=0,0,0,0
        for _,e in ipairs(tracks) do
          if not reaper.TrackFX_GetOffline(e.track,0) then online=online+1 end
          if reaper.GetMediaTrackInfo_Value(e.track,'I_SOLO')>0 then solo=solo+1 end
          if reaper.TrackFX_GetFloatingWindow(e.track,0) then windows=windows+1 end
        end
        for i=0,reaper.CountTracks(project)-1 do
          armed=armed+reaper.GetMediaTrackInfo_Value(reaper.GetTrack(project,i),'I_RECARM')
        end
        assert(online==1,'More than one synth online')
        assert(solo==1 and armed==1 and windows==1,'Audition isolation failed')
        assert(reaper.Track_GetPeakInfo(master,0)==0,'Audit master must remain silent')
        local audio_xrun,media_xrun=reaper.GetUnderrunTime()
        log:write(current.index,'\t',current.id,'\t',computer_peak,'\t',peak,'\t',
          reaper.TrackFX_GetParam(source,0x1000000,8),'\t',online,'\t',solo,'\t',armed,'\t',
          windows,'\t',audio_xrun,'\t',media_xrun,'\n');log:flush()
        local ok,state=reaper.TrackFX_GetNamedConfigParm(current.track,0,'clap_chunk');assert(ok)
        local f=assert(io.open('/tmp/synth-build-stage/loaded-'..current.index..'.b64','w'))
        f:write(state);f:close()
        release();phase='release';deadline=now+.3
      end
    end
  elseif phase=='gap' and now>=deadline then
    reaper.StuffMIDIMessage(0,0x90,60,88);peak=0;deadline=now+1;phase='hardware'
  elseif phase=='release' and now>=deadline then
    index=index+1;phase='select'
    if index>#tracks then
      for _,v in ipairs(tracks) do if v.id=='endless/A2-fmpad' then reaper.SetOnlyTrackSelected(v.track) end end
      local f=assert(io.open('/tmp/library-audio-done.txt','w'));f:write('Completed ',#tracks,' patches');f:close()
      cleanup();return
    end
  end
  reaper.defer(tick)
end
tick()
