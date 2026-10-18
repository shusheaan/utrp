-- Run after MIDI/state A/B. Compare settled parameter edits via the host API.
local profile=reaper.GetResourcePath()
local root=assert(profile:match('^(/tmp/chordlab%-.+)/reaper$'))
assert(reaper.CountTracks(0)==2)
local result=assert(io.open(root..'/ab-result.txt'));result:close()
local tracks={reaper.GetTrack(0,0),reaper.GetTrack(0,1)}
local cases={{0,0},{0,1},{0,0},{1,1},{1,0},{15,1},{2,.25},{2,0},
  {3,0},{3,1},{3,.5},{4,0},{4,1},{4,.5},{5,0},{5,1},{13,0},{13,1},
  {15,0},{15,.5},{15,1},{15,.5}}
local step,passed=0,0
local file=assert(io.open(root..'/parameter-result.txt','w'))
local deadline=reaper.time_precise()
local function finish(error)
  file:write('passed=',passed,'/',#cases,'\n')
  if error then file:write('ERROR=',error,'\n') end
  file:close()
end
local tick
local function safe()
  local ok,err=pcall(tick);if not ok then finish(tostring(err)) end
end
tick=function()
  if reaper.time_precise()<deadline then reaper.defer(safe);return end
  if step>0 then
    for _,i in ipairs({0,1,2,3,4,5,13,15,17}) do
      local a=reaper.TrackFX_GetParamNormalized(tracks[1],1,i)
      local b=reaper.TrackFX_GetParamNormalized(tracks[2],1,i)
      assert(math.abs(a-b)<1e-6,'case '..step..' param '..i..': '..a..' / '..b)
    end
    passed=passed+1
  end
  step=step+1
  if step>#cases then finish();return end
  for _,track in ipairs(tracks) do
    assert(reaper.TrackFX_SetParamNormalized(track,1,cases[step][1],cases[step][2]))
  end
  deadline=reaper.time_precise()+.2
  reaper.defer(safe)
end
reaper.defer(safe)
