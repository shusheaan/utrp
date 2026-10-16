-- Scratch-only: shared-degree memory, reset, type changes, and real RPP reload.
local _,path=reaper.EnumProjects(-1,'')
assert(path:match('^/tmp/chordlab%-'),'Scratch project only')
local t=reaper.GetTrack(0,0)
local fx=0x1000000
local checks=0
local function p(i) return reaper.TrackFX_GetParam(t,fx,i) end
local function tap(n) reaper.StuffMIDIMessage(0,0x9f,n,100); reaper.StuffMIDIMessage(0,0x8f,n,0) end
local function hold() reaper.StuffMIDIMessage(0,0x9f,74,100) end
local function release() reaper.StuffMIDIMessage(0,0x8f,74,0) end
local function check(ok,message) assert(ok,message); checks=checks+1 end
local function voices(want)
  check(p(8)==1,'Missing chord')
  local masks={0,0,0,0}
  for i,n in ipairs(want) do
    check(p(i==5 and 16 or 8+i)==n,'Voice mismatch '..i)
    local j=math.floor(n/32)+1; masks[j]=masks[j]+2^(n%32)
  end
  for i=1,4 do check(reaper.TrackFX_GetParam(t,0,i-1)==masks[i],'Output mask '..i) end
end
reaper.TrackFX_SetParam(t,fx,13,1)
local cases={
  function() tap(60); hold() end,
  function() voices({60,64,67,71}); tap(85) end,
  function() voices({60,62,64,67,71}); tap(80) end,
  function() voices({62,64,67,71,72}); tap(81) end,
  function() release() end,
  function() tap(61) end,
  function() hold() end,
  function()
    check(p(15)==2 and p(2)==1 and p(3)==72,'Type/register lost across keys')
    voices({63,65,68,72,73}); tap(82)
  end,
  function() voices({61,63,65,68,72}); release() end,
  function() tap(60) end,
  function() hold() end,
  function()
    voices({60,62,64,67,71}); check(p(15)==2 and p(2)==0 and p(3)==60,'Reset not remembered'); tap(85)
  end,
  function() voices({60,64,67}); tap(79) end,
  function() voices({55,60,64}); tap(81) end,
  function() release() end,
  function()
    check(p(8)==0,'Still sounding'); reaper.TrackFX_SetParam(t,fx,13,0)
    reaper.Main_SaveProject(0,false); reaper.Main_OnCommand(40860,0)
    reaper.Main_OnCommand(40859,0); reaper.Main_openProject(path)
    t=assert(reaper.GetTrack(0,0))
  end,
  function()
    check(p(8)==0,'Sounding restored on reload')
    reaper.TrackFX_SetParam(t,fx,13,1); hold()
  end,
  function()
    check(p(15)==0 and p(2)==2,'Saved type/inversion missing after RPP reload'); voices({55,60,64}); release()
  end,
  function() check(p(8)==0,'Release after reload failed'); reaper.TrackFX_SetParam(t,fx,13,0) end,
}
local index,deadline=1,0
local function tick()
  if reaper.time_precise()<deadline then reaper.defer(tick); return end
  local ok,err=pcall(cases[index])
  if not ok then
    local f=assert(io.open('/tmp/chordlab-state.txt','w')); f:write('FAIL ',tostring(err));f:close();return
  end
  index=index+1;deadline=reaper.time_precise()+.3
  if index<=#cases then reaper.defer(tick)
  else local f=assert(io.open('/tmp/chordlab-state.txt','w'));f:write('passed=',checks,'\n');f:close() end
end
tick()
