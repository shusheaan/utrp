-- Run after mixed_ab.lua in its isolated Input FX profile. No real audio/device.
local root=assert(reaper.GetResourcePath():match('^(/tmp/chordlab%-mixed%-.+)/reaper$'))
assert(root:match('%-input$'),'Input FX scratch profile required')
assert(reaper.CountTracks(0)==2)
local marker=assert(io.open(root..'/mixed-result.txt'));assert(marker:read('*a'):find('passed=42/42',1,true));marker:close()
for i=0,1 do
  local track=reaper.GetTrack(0,i)
  assert(reaper.CountTrackMediaItems(track)==0,'Empty scratch tracks required')
  reaper.SetMediaTrackInfo_Value(track,'I_RECMODE',0)
end
reaper.gmem_attach('ChordLab_AB_Prototype')
local serial=200
local function send(events)
  serial=serial+1
  reaper.gmem_write(1,#events)
  for i,event in ipairs(events) do
    for j,value in ipairs(event) do reaper.gmem_write(30+(i-1)*4+j-1,value) end
  end
  reaper.gmem_write(0,serial)
end
local function notes(track)
  local item=assert(reaper.GetTrackMediaItem(track,0),'Recorded item exists')
  local take=assert(reaper.GetActiveTake(item))
  assert(reaper.TakeIsMIDI(take))
  local _,count=reaper.MIDI_CountEvts(take)
  assert(count==6,'Chord plus two external notes, not channel-16 trigger')
  local result={}
  for i=0,count-1 do
    local ok,_,_,start,finish,ch,pitch,velocity=reaper.MIDI_GetNote(take,i)
    assert(ok and finish>start and ch==0,'Positive note length and channel 1')
    result[#result+1]=pitch..':'..velocity
  end
  table.sort(result)
  return table.concat(result,',')
end
local function verify()
  local expected='60:64,62:37,64:64,66:93,67:64,71:64'
  for i=0,1 do assert(notes(reaper.GetTrack(0,i))==expected,'Recorded mixed MIDI pitches/velocities') end
  reaper.Main_SaveProject(0,false)
end
local stage=0
reaper.SetEditCurPos(0,false,false)
reaper.Main_OnCommand(1013,0)
local begin=reaper.time_precise()
local function finish(error)
  if reaper.GetPlayState()~=0 then reaper.OnStopButton() end
  local f=assert(io.open(root..'/mixed-record-result.txt','w'))
  f:write(error and 'FAIL '..error or 'PASS JSFX and CLAP Input FX: 6 recorded notes each; exact pitches/channels/velocities; positive lengths')
  f:write('\n');f:close()
end
local tick
local function safe()
  local ok,err=pcall(tick);if not ok then finish(tostring(err)) end
end
tick=function()
  local elapsed=reaper.time_precise()-begin
  if stage==0 and elapsed>.25 then send({{0,0x9f,74,100}});stage=1
  elseif stage==1 and elapsed>.45 then send({{0,0x90,66,93},{11,0x90,62,37}});stage=2
  elseif stage==2 and elapsed>.65 then send({{0,0x8f,74,0}});stage=3
  elseif stage==3 and elapsed>.85 then send({{0,0x80,66,0},{11,0x80,62,0}});stage=4
  elseif stage==4 and elapsed>1.2 then reaper.Main_OnCommand(1016,0);stage=5
  elseif stage==5 and elapsed>1.6 then verify();finish();return end
  reaper.defer(safe)
end
reaper.defer(safe)
