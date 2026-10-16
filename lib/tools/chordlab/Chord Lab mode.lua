-- Pure REAPER: manage one explicit target track, not whichever track has focus.
local SECTION = 'utrp.chordlab'
local VKB, SEND = 40377, 40637
local track = reaper.GetSelectedTrack(0, 0)
if not track then reaper.MB('Select an instrument track first.', 'Chord Lab', 0); return end
local project = reaper.EnumProjects(-1, '')
local fx = -1
for i = 0, reaper.TrackFX_GetRecCount(track) - 1 do
  local ok, ident = reaper.TrackFX_GetNamedConfigParm(track, i | 0x1000000, 'fx_ident')
  if ok and ident == 'ChordLab/chordlab.jsfx' then fx = i; break end
end
if fx < 0 then fx = reaper.TrackFX_AddByName(track, 'ChordLab/chordlab.jsfx', true, 1) end
if fx < 0 then reaper.MB('Install Chord Lab first (see README).', 'Chord Lab', 0); return end
-- AddByName(recFX=true) returns a plain index; other TrackFX APIs need the flag.
fx = fx | 0x1000000
local fxguid = reaper.TrackFX_GetFXGUID(track, fx)
local token = reaper.genGuid()
local previous = {
  input = reaper.GetMediaTrackInfo_Value(track, 'I_RECINPUT'),
  armed = reaper.GetMediaTrackInfo_Value(track, 'I_RECARM'),
  monitor = reaper.GetMediaTrackInfo_Value(track, 'I_RECMON'),
  send = reaper.GetToggleCommandState(SEND),
  visible = reaper.GetToggleCommandState(VKB),
}
local function set_toggle(action, wanted)
  if reaper.GetToggleCommandState(action) ~= wanted then reaper.Main_OnCommand(action, 0) end
end
local function valid_track()
  return reaper.ValidatePtr2(project, track, 'MediaTrack*')
end
local function valid()
  if not valid_track() then return false end
  for i = 0, reaper.TrackFX_GetRecCount(track) - 1 do
    if reaper.TrackFX_GetFXGUID(track, i | 0x1000000) == fxguid then
      fx = i | 0x1000000; return true
    end
  end
  return false
end
local function send_stop()
  if not valid() then return end
  reaper.TrackFX_SetParam(track, fx, 7, 23)
  local serial = reaper.TrackFX_GetParam(track, fx, 6)
  reaper.TrackFX_SetParam(track, fx, 6, (serial + 1) % 1000001)
end
local function conflict()
  for i = 0, reaper.CountTracks(project) - 1 do
    local other = reaper.GetTrack(project, i)
    local input = math.floor(reaper.GetMediaTrackInfo_Value(other, 'I_RECINPUT'))
    local device = math.floor((input - 4096) / 32)
    if other ~= track and reaper.GetMediaTrackInfo_Value(other, 'I_RECARM') == 1
      and input >= 4096 and (device == 62 or device == 63) then return true end
  end
  return false
end
local function cleanup()
  send_stop()
  if valid() then reaper.TrackFX_SetParam(track, fx, 13, 0) end
  if valid_track() then
    reaper.SetMediaTrackInfo_Value(track, 'I_RECINPUT', previous.input)
    reaper.SetMediaTrackInfo_Value(track, 'I_RECARM', previous.armed)
    reaper.SetTrackUIInputMonitor(track, previous.monitor, 0)
  end
  set_toggle(SEND, previous.send)
  set_toggle(VKB, previous.visible)
  reaper.DeleteExtState(SECTION, 'target_track', false)
  reaper.DeleteExtState(SECTION, 'target_fx', false)
  reaper.DeleteExtState(SECTION, 'running', false)
  reaper.DeleteExtState(SECTION, 'stop', false)
end
reaper.atexit(cleanup)
reaper.SetExtState(SECTION, 'running', token, false)
reaper.SetExtState(SECTION, 'target_track', reaper.GetTrackGUID(track), false)
reaper.SetExtState(SECTION, 'target_fx', fxguid, false)
-- Rebuild live monitoring even when a saved project was already armed/monitored.
-- Raw setters alone can leave downstream CLAP asleep until the first transport play.
reaper.SetTrackUIInputMonitor(track, 0, 0)
reaper.SetMediaTrackInfo_Value(track, 'I_RECINPUT', 4096 + 63 * 32)
reaper.SetMediaTrackInfo_Value(track, 'I_RECARM', 1)
reaper.SetTrackUIInputMonitor(track, 1, 0)
reaper.TrackFX_SetParam(track, fx, 13, 1)
reaper.TrackFX_Show(track, fx, 3)
local last_mode = -1
local bypass_pending = false
local stopping = false
local warned_conflict = false
local function tick()
  if not valid() then return end
  if reaper.GetExtState(SECTION, 'stop') == token or reaper.EnumProjects(-1, '') ~= project then
    if not stopping then send_stop(); stopping = true; reaper.defer(tick); return end
    return
  end
  if bypass_pending then
    if reaper.TrackFX_GetParam(track, fx, 8) < 0.5 then
      reaper.TrackFX_SetEnabled(track, fx, false); bypass_pending = false
    end
    reaper.defer(tick); return
  end
  if not reaper.TrackFX_GetEnabled(track, fx) and reaper.TrackFX_GetParam(track, fx, 8) > 0.5 then
    -- Flush only our own notes before honoring the user's bypass request.
    reaper.TrackFX_SetEnabled(track, fx, true); send_stop(); bypass_pending = true
    reaper.defer(tick); return
  end
  local active = reaper.TrackFX_GetEnabled(track, fx)
    and reaper.GetMediaTrackInfo_Value(track, 'I_FXEN') ~= 0
  local requested = reaper.TrackFX_GetParam(track, fx, 13) >= 0.5
  local blocked = requested and conflict()
  if blocked and not warned_conflict then
    reaper.MB('Keyboard mode disabled: another armed track receives Virtual MIDI Keyboard or All MIDI inputs. Disarm that track, then run Open Chord Lab twice to restart the mode.', 'Chord Lab', 0)
  end
  warned_conflict = blocked
  local mode = requested and active and not blocked
  if mode ~= last_mode then
    if mode then set_toggle(VKB, 1); set_toggle(SEND, 1)
    else send_stop(); set_toggle(SEND, 0); reaper.TrackFX_SetParam(track, fx, 13, 0) end
    last_mode = mode
  end
  reaper.defer(tick)
end
tick()
