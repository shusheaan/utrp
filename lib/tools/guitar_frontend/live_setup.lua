-- Build only an empty, explicitly named trial project. Never change synth.rpp.
local project,path=reaper.EnumProjects(-1,'')
assert(path:match('/Guitar Lab%.rpp$'),'Open the new Guitar Lab.rpp first')
assert(reaper.CountTracks(project)==0,'Refusing to replace any existing tracks')
local function named(index,name)
  reaper.InsertTrackAtIndex(index,false)
  local t=reaper.GetTrack(project,index)
  reaper.GetSetMediaTrackInfo_String(t,'P_NAME',name,true)
  return t
end
local source=named(0,'GUITAR - Spark dry input -> MIDI')
reaper.SetMediaTrackInfo_Value(source,'I_RECINPUT',0) -- mono hardware input 1, never a monitor source
reaper.SetMediaTrackInfo_Value(source,'I_RECARM',1)
reaper.SetTrackUIInputMonitor(source,1,0)
reaper.SetMediaTrackInfo_Value(source,'B_MAINSEND',0) -- listen directly on Spark; avoid doubled monitoring
reaper.SetMediaTrackInfo_Value(source,'I_PERFFLAGS',3)
assert(reaper.TrackFX_AddByName(source,'CLAP: Guitar Frontend',false,-1)==0,'Scan/install Guitar Frontend first')
local display=named(1,'CHORD LAB - detected guitar notes (display only)')
reaper.SetMediaTrackInfo_Value(display,'I_RECINPUT',-1)
reaper.SetMediaTrackInfo_Value(display,'I_RECARM',0)
reaper.SetMediaTrackInfo_Value(display,'I_PERFFLAGS',3)
assert(reaper.TrackFX_AddByName(display,'CLAP: Chord Lab',false,-1)==0)
local send=reaper.CreateTrackSend(source,display)
assert(send>=0)
reaper.SetTrackSendInfo_Value(source,0,send,'I_SRCCHAN',-1) -- no guitar audio into the display track
reaper.SetTrackSendInfo_Value(source,0,send,'I_MIDIFLAGS',0)
reaper.GetSetProjectNotes(project,true,'Guitar Frontend 0.1.1: MONO prototype. Spark hardware input 1; direct monitoring on Spark. MIDI channel 2 -> Chord Lab normal FX. No synth on this display-only track. Software dry monitoring disabled intentionally. Never use playback/monitor ports as guitar input. Double/triple notes and ringing arpeggios are NOT supported yet.')
reaper.TrackList_AdjustWindows(false)
reaper.SetOnlyTrackSelected(source)
reaper.TrackFX_Show(source,0,3)
reaper.TrackFX_Show(display,0,3)
reaper.Main_SaveProject(project,false)
