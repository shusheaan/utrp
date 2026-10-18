-- Isolated dummy-audio profile only. No production project/device changes.
local root=assert(reaper.GetResourcePath():match('^(/tmp/guitar%-frontend%-.+)/reaper$'))
local _,path=reaper.EnumProjects(-1,'')
assert(path==root..'/test.rpp' and reaper.CountTracks(0)==0,'Empty isolated project required')
reaper.gmem_attach('UTRP_Guitar_Frontend_Test')
reaper.gmem_write(0,1)
local function track(index,name)
  reaper.InsertTrackAtIndex(index,false)
  local t=reaper.GetTrack(0,index)
  reaper.GetSetMediaTrackInfo_String(t,'P_NAME',name,true)
  reaper.SetMediaTrackInfo_Value(t,'B_MAINSEND',1)
  reaper.SetMediaTrackInfo_Value(t,'I_PERFFLAGS',3)
  reaper.SetMediaTrackInfo_Value(t,'I_RECINPUT',4096+62*32)
  reaper.SetMediaTrackInfo_Value(t,'I_RECARM',1)
  reaper.SetTrackUIInputMonitor(t,1,0)
  return t
end
reaper.SetMediaTrackInfo_Value(reaper.GetMasterTrack(0),'B_MUTE',1)
local audio=track(0,'Synthetic dry audio -> Guitar Frontend')
assert(reaper.TrackFX_AddByName(audio,'GuitarFrontendTest/test_source.jsfx',false,-1)==0)
assert(reaper.TrackFX_AddByName(audio,'CLAP: Guitar Frontend',false,-1)==1)
assert(reaper.TrackFX_AddByName(audio,'GuitarFrontendTest/test_capture.jsfx',false,-1)==2)
local display=track(1,'MIDI only -> unchanged Chord Lab')
assert(reaper.TrackFX_AddByName(display,'CLAP: Chord Lab',false,-1)==0)
assert(reaper.TrackFX_AddByName(display,'GuitarFrontendTest/test_capture.jsfx',false,-1)==1)
reaper.TrackFX_SetParam(display,1,0,1)
local send=reaper.CreateTrackSend(audio,display)
reaper.SetTrackSendInfo_Value(audio,0,send,'I_SRCCHAN',-1)
reaper.SetTrackSendInfo_Value(audio,0,send,'I_MIDIFLAGS',0)
reaper.OnPlayButton()
local notes={38,40,45,50,55,59,60,64,66,67,72,76,83,88}
local expected,step,phase,deadline={},1,'begin',reaper.time_precise()+0.5
local log=assert(io.open(root..'/events.tsv','w'))
local function finish(message)
  reaper.TrackFX_SetParam(audio,0,0,-1)
  reaper.OnStopButton()
  local f=assert(io.open(root..'/result.txt','w'));f:write(message,'\n');f:close();log:close()
  reaper.Main_SaveProject(0,false)
end
local function lane(index)
  local base=100+index*10000
  local count=reaper.gmem_read(base)
  local result={}
  for i=0,count-1 do
    local p=base+1+4*i
    local status,note,velocity=reaper.gmem_read(p+1),reaper.gmem_read(p+2),reaper.gmem_read(p+3)
    if status==0x91 or status==0x81 then result[#result+1]=string.format('%02x:%d:%d',status,note,velocity) end
  end
  return table.concat(result,',')
end
local tick
local function safe()
  local ok,err=pcall(tick)
  if not ok then finish('FAIL '..tostring(err)) end
end
tick=function()
  if reaper.time_precise()<deadline then reaper.defer(safe);return end
  if phase=='begin' then
    local n=notes[step]
    reaper.TrackFX_SetParam(audio,0,0,n)
    expected[#expected+1]=string.format('91:%d:90',n)
    phase='held';deadline=reaper.time_precise()+0.35
  elseif phase=='held' then
    assert(reaper.TrackFX_GetParam(audio,1,7)==notes[step],'Wrong detected note')
    reaper.TrackFX_SetParam(audio,0,0,-1)
    expected[#expected+1]=string.format('81:%d:0',notes[step])
    phase='released';deadline=reaper.time_precise()+0.25
  else
    local wanted=table.concat(expected,',')
    local a,b=lane(0),lane(1)
    log:write(step,'\t',notes[step],'\t',a,'\t',b,'\n');log:flush()
    assert(a==wanted,'Frontend on/off mismatch at '..notes[step]..' got '..a)
    assert(b==wanted,'Chord Lab routed on/off mismatch at '..notes[step]..' got '..b)
    step=step+1
    if step>#notes then finish('PASS 14 synthetic pitches, 28 MIDI events before and after Chord Lab; MIDI-only send; no hardware certification');return end
    phase='begin'
  end
  reaper.defer(safe)
end
reaper.defer(safe)
