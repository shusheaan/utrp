-- Bind Tab as a REAPER Global shortcut; act only on the active Chord Lab target.
local section='utrp.chordlab'
if reaper.GetExtState(section,'running')=='' then
  reaper.Main_OnCommand(40375,0) -- Preserve default Tab: next transient.
  return
end
local guid=reaper.GetExtState(section,'target_track')
local fxguid=reaper.GetExtState(section,'target_fx')
for i=0,reaper.CountTracks(0)-1 do
  local track=reaper.GetTrack(0,i)
  if reaper.GetTrackGUID(track)==guid then
    for j=0,reaper.TrackFX_GetRecCount(track)-1 do
      local fx=j|0x1000000
      if reaper.TrackFX_GetFXGUID(track,fx)==fxguid and reaper.TrackFX_GetEnabled(track,fx)
        and reaper.TrackFX_GetParam(track,fx,13)>=.5 then
        reaper.TrackFX_SetParam(track,fx,7,25)
        reaper.TrackFX_SetParam(track,fx,6,(reaper.TrackFX_GetParam(track,fx,6)+1)%1000001)
        return
      end
    end
  end
end
