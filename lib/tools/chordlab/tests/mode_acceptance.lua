-- Run only in the isolated scratch profile, with the test MIDI probe at normal FX 0.
local _, path = reaper.EnumProjects(-1, '')
assert(path:match('^/tmp/chordlab%-'), 'Scratch project only')
assert(reaper.GetExtState('utrp.chordlab','running') == '', 'Stop mode before testing')
local track = reaper.GetTrack(0, 0)
local fx = 0x1000000
-- This test may also be loaded by the temporary host runner.
local source = debug.getinfo(1, 'S').source:sub(2):match('^(.*)/tests/')
local action = reaper.AddRemoveReaScript(true, 0, source .. '/Open Chord Lab.lua', true)
local checks = 0
local function check(value, message)
  assert(value, message); checks = checks + 1
end
local function toggle(command, wanted)
  if reaper.GetToggleCommandState(command) ~= wanted then reaper.Main_OnCommand(command, 0) end
end
local function hold(note)
  reaper.StuffMIDIMessage(0, 0x9f, note, 100)
end
local function mode(value) reaper.TrackFX_SetParam(track, fx, 13, value) end
local function sounding() return reaper.TrackFX_GetParam(track, fx, 8) end
local original = {
  input=reaper.GetMediaTrackInfo_Value(track,'I_RECINPUT'),
  arm=reaper.GetMediaTrackInfo_Value(track,'I_RECARM'),
  monitor=reaper.GetMediaTrackInfo_Value(track,'I_RECMON'),
  send=reaper.GetToggleCommandState(40637), visible=reaper.GetToggleCommandState(40377),
}
local cases = {
  function()
    reaper.SetMediaTrackInfo_Value(track,'I_RECINPUT',0)
    reaper.SetMediaTrackInfo_Value(track,'I_RECARM',0)
    reaper.SetMediaTrackInfo_Value(track,'I_RECMON',0)
    toggle(40637,0); toggle(40377,0)
  end,
  function()
    check(reaper.GetToggleCommandState(40377)==0,'Baseline VKB still visible')
    reaper.SetOnlyTrackSelected(track)
    reaper.Main_OnCommand(action,0)
  end,
  function()
    check(reaper.GetExtState('utrp.chordlab','running')~='', 'Session did not start')
    check(reaper.TrackFX_GetRecCount(track)==1, 'Duplicate Input FX')
    check(reaper.GetMediaTrackInfo_Value(track,'I_RECINPUT')==6112, 'All MIDI input missing')
    check(reaper.GetMediaTrackInfo_Value(track,'I_RECARM')==1, 'Not armed')
    check(reaper.GetMediaTrackInfo_Value(track,'I_RECMON')==1, 'Not monitored')
    check(reaper.GetToggleCommandState(40637)==1, 'Send-all disabled')
    hold(74)
  end,
  function() check(sounding()==1,'Computer chord missing'); mode(0) end,
  function()
    check(sounding()==0,'Mode off did not stop')
    check(reaper.GetToggleCommandState(40637)==0,'Mode off still captures keys')
    reaper.StuffMIDIMessage(0,0x90,60,99)
  end,
  function()
    check(reaper.TrackFX_GetParam(track,0,1)==2^28,'Physical MIDI blocked with mode off')
    reaper.StuffMIDIMessage(0,0x80,60,0); mode(1)
  end,
  function() check(reaper.GetToggleCommandState(40637)==1,'Mode on failed'); hold(74) end,
  function() check(sounding()==1,'Chord missing after mode on'); reaper.TrackFX_SetEnabled(track,fx,false) end,
  function()
    check(sounding()==0,'Bypass did not flush notes')
    check(not reaper.TrackFX_GetEnabled(track,fx),'Bypass not restored')
    reaper.TrackFX_SetEnabled(track,fx,true); mode(1)
  end,
  function() hold(74) end,
  function()
    check(sounding()==1,'Chord missing before shutdown')
    reaper.Main_OnCommand(action,0)
  end,
  function()
    check(reaper.GetExtState('utrp.chordlab','running')=='','Session did not exit')
    check(sounding()==0,'Exit did not release chord')
    check(reaper.TrackFX_GetParam(track,fx,13)==0,'Mode flag not cleared')
    check(reaper.GetMediaTrackInfo_Value(track,'I_RECINPUT')==0,'Input not restored')
    check(reaper.GetMediaTrackInfo_Value(track,'I_RECARM')==0,'Arm not restored')
    check(reaper.GetMediaTrackInfo_Value(track,'I_RECMON')==0,'Monitor not restored')
    check(reaper.GetToggleCommandState(40637)==0,'VKB send not restored')
    check(reaper.GetToggleCommandState(40377)==0,'VKB window not restored')
    reaper.SetMediaTrackInfo_Value(track,'I_RECINPUT',original.input)
    reaper.SetMediaTrackInfo_Value(track,'I_RECARM',original.arm)
    reaper.SetMediaTrackInfo_Value(track,'I_RECMON',original.monitor)
    toggle(40637,original.send); toggle(40377,original.visible)
  end,
}
local index, deadline = 1, 0
local function tick()
  if reaper.time_precise() < deadline then reaper.defer(tick); return end
  local ok, err = pcall(cases[index])
  if not ok then
    local f=assert(io.open('/tmp/chordlab-mode.txt','w')); f:write('FAIL ',tostring(err)); f:close()
    return  -- Report failures without opening a modal dialog or killing the host runner.
  end
  index=index+1; deadline=reaper.time_precise()+0.25
  if index<=#cases then reaper.defer(tick)
  else
    local f=assert(io.open('/tmp/chordlab-mode.txt','w')); f:write('passed=',checks,'\n'); f:close()
  end
end
tick()
