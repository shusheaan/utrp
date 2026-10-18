-- Run AFTER ab_test.lua, in its isolated scratch project. Real RPP reload.
local profile=reaper.GetResourcePath()
local root=assert(profile:match('^(/tmp/chordlab%-.+)/reaper$'),'Scratch profile only')
local _,path=reaper.EnumProjects(-1,'')
assert(path==root..'/prototype.rpp' and reaper.CountTracks(0)==2)
local result=assert(io.open(root..'/ab-result.txt'))
assert(result:read('*a'):find('\nscope='),'First complete the MIDI A/B test');result:close()
reaper.gmem_attach('ChordLab_AB_Prototype')
local serial=reaper.gmem_read(0)
local function send(events)
  reaper.gmem_write(1,#events)
  for i,event in ipairs(events) do
    for j,v in ipairs(event) do reaper.gmem_write(30+(i-1)*4+j-1,v) end
  end
  serial=serial+1;reaper.gmem_write(0,serial)
end
local function tap(note) send({{0,0x9f,note,100},{1,0x8f,note,0}}) end
local function hold() send({{13,0x9f,74,100}}) end
local function release() send({{63,0x8f,74,0}}) end
local function param(index) return reaper.TrackFX_GetParam(reaper.GetTrack(0,0),1,index) end
local function capture(lane)
  assert(reaper.gmem_read(10+lane)==serial,'Input not processed')
  local base=1000+lane*50000
  assert(reaper.gmem_read(base+1)==0,'Capture overflow')
  local events={}
  for i=0,reaper.gmem_read(base)-1 do
    local p=base+2+i*4
    events[#events+1]=string.format('%d:%02x:%d:%d',reaper.gmem_read(p),
      reaper.gmem_read(p+1),reaper.gmem_read(p+2),reaper.gmem_read(p+3))
  end
  return table.concat(events,','),#events
end
local expected,checks='',0
local function equal(minimum)
  local a,n=capture(0);local b=capture(1)
  assert(n>=minimum and a==b,'Native/CLAP state output mismatch: '..a..' / '..b)
  checks=checks+1;return a
end
local steps={
  function() tap(60) end,
  hold,
  function()
    local events={}
    for _=1,(2-param(15))%3 do
      events[#events+1]={0,0x9f,85,100};events[#events+1]={1,0x8f,85,0}
    end
    send(events)
  end,
  function() tap(81) end,
  function() tap(80) end,
  function() equal(10);assert(param(15)==2 and param(2)==1);release() end,
  hold,
  function() expected=equal(5);release() end,
  function() equal(5);if param(17)==0 then tap(82) else send({}) end end,
  function() assert(param(17)==1,'Sustain fixture not enabled');send({}) end,
  function()
    equal(0);assert(param(8)==0,'Held note before save')
    reaper.Main_SaveProject(0,false)
    reaper.Main_OnCommand(40860,0) -- close current project tab
    reaper.Main_OnCommand(40859,0) -- new project tab
    reaper.Main_openProject(path)
  end,
  function()
    assert(reaper.CountTracks(0)==2 and param(8)==0,'Unexpected reload state')
    assert(param(17)==0,'Sustain must reset on reload, matching baseline safety')
    hold()
  end,
  function() assert(equal(5)==expected,'Voicing memory changed after reload');release() end,
  function() equal(5);send({{193,0xb0,64,0}}) end,
  function() assert(equal(1)=='193:b0:64:0','Sustain still locked after reload');send({}) end,
}
local index,deadline=1,reaper.time_precise()+.5
local function finish(err)
  send({{0,0xbf,123,0},{1,0xb0,123,0}})
  local f=assert(io.open(root..'/state-result.txt','w'))
  f:write(err and ('FAIL '..tostring(err)) or ('PASS checks='..checks..'\nexpected='..expected))
  f:close()
end
local function tick()
  if reaper.time_precise()<deadline then reaper.defer(tick);return end
  local ok,err=pcall(steps[index])
  if not ok then finish(err);return end
  index=index+1;deadline=reaper.time_precise()+.3
  if index<=#steps then reaper.defer(tick) else finish() end
end
reaper.defer(tick)
