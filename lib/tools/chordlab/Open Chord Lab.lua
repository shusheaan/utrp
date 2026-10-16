-- Short action entry point; the deferred session has its own lifetime.
local section = 'utrp.chordlab'
local token = reaper.GetExtState(section, 'running')
if token ~= '' then
  reaper.SetExtState(section, 'stop', token, false)
  return
end
local _, path = reaper.get_action_context()
local directory = path:match('^(.*[/\\])')
local action = reaper.AddRemoveReaScript(true, 0, directory .. 'Chord Lab mode.lua', true)
if action == 0 then reaper.MB('Cannot register Chord Lab mode.', 'Chord Lab', 0); return end
reaper.Main_OnCommand(action, 0)
-- Only the explicit Open action requests a window; Library startup does not.
local track = reaper.GetSelectedTrack(0, 0)
if not track or reaper.GetExtState(section, 'running') == '' then return end
local guid = reaper.GetExtState(section, 'target_fx')
for i = 0, reaper.TrackFX_GetRecCount(track) - 1 do
  local fx = i | 0x1000000
  if reaper.TrackFX_GetFXGUID(track, fx) == guid then
    reaper.TrackFX_Show(track, fx, 3)
    break
  end
end
