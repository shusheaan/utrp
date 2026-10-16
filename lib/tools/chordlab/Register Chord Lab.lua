-- Load this once from Actions > New action > Load ReaScript.
local _, path = reaper.get_action_context()
local dir = assert(path:match('^(.*[/\\])'))
local id = reaper.AddRemoveReaScript(true, 0, dir .. 'Open Chord Lab.lua', true)
reaper.AddRemoveReaScript(true, 0, dir .. 'Cycle chord type.lua', true)
assert(id ~= 0, 'Could not register Chord Lab action')
reaper.MB('Registered: Script: Open Chord Lab.lua\n\nSelect a synth track, then run that action.\nRun it again to exit and restore the previous input settings.', 'Chord Lab', 0)
