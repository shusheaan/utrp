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
