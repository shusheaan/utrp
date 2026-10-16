local _,path=reaper.EnumProjects(-1,'')
assert(path:match('/tmp/chordlab%-'),'Scratch project only')
local t=reaper.GetTrack(0,0)
assert(reaper.CountTrackMediaItems(t)==0,'Scratch track must have no items')
local fx=0x1000000
reaper.TrackFX_SetParam(t,fx,0,0)
reaper.TrackFX_SetParam(t,fx,2,0)
reaper.TrackFX_SetParam(t,fx,13,1)
reaper.SetMediaTrackInfo_Value(t,'I_RECMODE',0)
reaper.SetEditCurPos(0,false,false)
reaper.Main_OnCommand(1013,0)
local begin=reaper.time_precise()
local stage=0
local function tap(n)
 reaper.StuffMIDIMessage(0,0x9f,n,100); reaper.StuffMIDIMessage(0,0x8f,n,0)
end
local function tick()
 local elapsed=reaper.time_precise()-begin
 if stage==0 and elapsed>.2 then reaper.StuffMIDIMessage(0,0x9f,74,100); stage=1
 elseif stage==1 and elapsed>.6 then tap(80); stage=2
 elseif stage==2 and elapsed>1 then reaper.StuffMIDIMessage(0,0x8f,74,0); stage=3
 elseif stage==3 and elapsed>1.3 then reaper.Main_OnCommand(1016,0); stage=4
 elseif stage==4 and elapsed>1.6 then
  local item=assert(reaper.GetTrackMediaItem(t,0),'No recorded MIDI item')
  local take=assert(reaper.GetActiveTake(item),'No take')
  local _,count=reaper.MIDI_CountEvts(take)
  local notes={}
  for i=0,count-1 do
   local ok,_,_,start,finish,ch,pitch=reaper.MIDI_GetNote(take,i)
   assert(ok and finish>start and ch==0,'Invalid recorded note')
   notes[#notes+1]=pitch
  end
  local f=assert(io.open('/tmp/chordlab-recording.txt','w'))
  f:write('notes=',count,' pitches=',table.concat(notes,','),'\n'); f:close()
  assert(count==8,'Expected two four-note voicings, not trigger keys')
  return
 end
 reaper.defer(tick)
end
tick()
