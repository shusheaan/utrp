-- Scratch-only: sustain latch, unmodified hardware velocities, automatic Tab memory.
local _,path=reaper.EnumProjects(-1,'')
assert(path:match('^/tmp/chordlab%-'),'Scratch project only')
local t=assert(reaper.GetTrack(0,0))
local fx=0x1000000
local checks,cases=0,{}
local expected_kind,reset_kind,reset_revision
local function check(ok,message) assert(ok,message);checks=checks+1 end
local function p(i) return reaper.TrackFX_GetParam(t,fx,i) end
local function probe(i) return reaper.TrackFX_GetParam(t,0,i) end
local function command(n)
 reaper.TrackFX_SetParam(t,fx,7,n)
 reaper.TrackFX_SetParam(t,fx,6,(p(6)+1)%1000001)
end
local function midi(s,n,v) reaper.StuffMIDIMessage(0,s,n,v) end
local function add(f) cases[#cases+1]=f end
add(function()
 check(p(17)==0 and probe(10)==0,'Initial sustain is not OFF')
 reaper.TrackFX_SetParam(t,fx,13,1)
 command(26)
end)
add(function()
 check(p(17)==1 and probe(10)==32767,'Sustain ON must reach channels 1..15 only')
 reaper.TrackFX_SetOpen(t,fx,false)
 midi(0xb0,64,0);midi(0xbe,64,0)
end)
add(function()
 check(p(17)==1 and probe(10)==32767,'Pedal release or hidden editor cleared latch')
 command(27)
end)
add(function()
 check(p(17)==0 and probe(10)==0,'Forced sustain OFF failed')
 midi(0xb0,64,127)
end)
add(function()
 check(probe(10)==1,'Unlocked pedal ON was not forwarded')
 midi(0xb0,64,0)
end)
add(function()
 check(probe(10)==0,'Unlocked pedal OFF was not forwarded')
 command(26)
end)
add(function() midi(0xbe,123,0) end)
add(function()
 check(p(17)==0 and probe(10)==0,'Panic on channel 15 did not reset latch')
 command(26)
end)
add(function() reaper.TrackFX_SetParam(t,fx,5,0) end)
add(function()
 check(p(17)==0 and probe(10)==0,'Disabled controls retained sustain')
 command(26)
end)
add(function()
 check(p(17)==0,'Disabled controls allowed sustain ON')
 reaper.TrackFX_SetParam(t,fx,5,1)
end)
add(function()
 reset_kind=p(15)
 midi(0x9f,80,100);midi(0x8f,80,0) -- L moves voicing.
end)
add(function()
 check(p(2)~=0 or p(3)~=60,'Reset test did not move voicing')
 reset_revision=p(14)
 midi(0x9f,81,100);midi(0x8f,81,0) -- Semicolon.
end)
add(function()
 check(p(2)==0 and p(3)==60 and p(15)==reset_kind,'Semicolon did not reset without changing type')
 check(p(14)>reset_revision,'Semicolon reset was not remembered')
 reset_revision=p(14)
 midi(0x9f,82,100) -- Hold Enter.
end)
add(function()
 check(p(17)==1 and probe(10)==32767,'Enter did not enable sustain')
 midi(0x9f,82,100) -- Auto-repeat must not toggle again.
end)
add(function()
 check(p(17)==1,'Held Enter repeat toggled sustain')
 check(p(14)==reset_revision,'Enter changed voicing memory')
 midi(0x8f,82,0)
end)
add(function()
 check(p(17)==1,'Enter release cancelled sustain latch')
 midi(0x9f,82,100);midi(0x8f,82,0)
end)
add(function()
 check(p(17)==0 and probe(10)==0,'Second Enter did not disable sustain')
end)
-- Boundary and representative velocities on two hardware channels pass unchanged.
for _,ch in ipairs({0,14}) do
 for _,velocity in ipairs({1,2,16,32,48,56,64,76,88,100,126,127}) do
  add(function() midi(0x90+ch,60,velocity) end)
  add(function()
   check(probe(8)==velocity and probe(9)==ch,'Hardware velocity/channel changed')
   midi(0x90+ch,60,0)
  end)
 end
end
add(function()
 check(probe(0)==0 and probe(1)==0 and probe(2)==0 and probe(3)==0,'Velocity-zero release failed')
 reaper.TrackFX_SetParam(t,fx,4,64)
 midi(0x9f,74,100) -- I chord
end)
add(function()
 check(probe(8)==64 and p(8)==1,'Computer chord velocity changed unexpectedly')
 expected_kind=(p(15)+1)%3
 command(25) -- no save or voicing movement
end)
add(function()
 check(p(15)==expected_kind,'Type did not cycle')
 midi(0x8f,74,0);midi(0x8f,75,0)
end)
add(function() midi(0x9f,75,100) end) -- ii chord
add(function()
 check(p(15)==1,'Tab changed another degree')
 midi(0x8f,74,0);midi(0x8f,75,0)
end)
add(function() midi(0x9f,74,100) end)
add(function()
 check(p(15)==expected_kind,'Tab type was not automatically remembered')
 midi(0x8f,74,0);midi(0x8f,75,0)
end)
add(function()
 command(26)
end)
add(function()
 check(p(17)==1,'Sustain missing before save')
 reaper.Main_SaveProject(0,false)
 reaper.Main_OnCommand(40860,0);reaper.Main_OnCommand(40859,0)
 reaper.Main_openProject(path);t=assert(reaper.GetTrack(0,0))
end)
add(function()
 check(p(17)==0 and probe(10)==0,'Saved project restored locked sustain')
 reaper.TrackFX_SetParam(t,fx,13,1);midi(0x9f,74,100)
end)
add(function()
 check(p(15)==expected_kind,'Automatic Tab memory missing after RPP reload')
 command(23)
end)
add(function() check(p(8)==0 and p(17)==0,'Stop failed') end)
local index,deadline=1,0
local function tick()
 if reaper.time_precise()<deadline then reaper.defer(tick);return end
 local ok,err=pcall(cases[index])
 if not ok then
  local f=assert(io.open('/tmp/chordlab-controls-result.txt','w'))
  f:write('FAIL case=',index,' ',tostring(err));f:close();return
 end
 index=index+1;deadline=reaper.time_precise()+.15
 if index<=#cases then reaper.defer(tick)
 else
  local f=assert(io.open('/tmp/chordlab-controls-result.txt','w'))
  f:write('passed=',checks,'\n');f:close()
 end
end
tick()
