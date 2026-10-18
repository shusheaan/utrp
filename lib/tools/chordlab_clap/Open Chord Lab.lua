-- Focused CLAP editor only. Never instantiate JSFX or start a VKB session.
local function open(track)
 if not track then return false end
 for i=0,reaper.TrackFX_GetRecCount(track)-1 do
  local fx=i|0x1000000
  local ok,ident=reaper.TrackFX_GetNamedConfigParm(track,fx,'fx_ident')
  if ok and ident=='org.utrp.chordlab' then reaper.TrackFX_Show(track,fx,3);return true end
 end
 return false
end
for i=0,reaper.CountTracks(0)-1 do
 local t=reaper.GetTrack(0,i)
 local _,marker=reaper.GetSetMediaTrackInfo_String(t,'P_EXT:utrp_library_input','',false)
 if marker=='1' and open(t) then return end
end
if open(reaper.GetSelectedTrack(0,0)) then return end
reaper.MB('Add Chord Lab CLAP to Input FX first. The legacy JSFX/VKB session is retired.','Chord Lab CLAP',0)
