-- Run ONLY in the dedicated scratch project, with Chord Lab Input FX,
-- tests/midi_probe.jsfx as normal FX 0, and a synth as normal FX 1.
local t = assert(reaper.GetTrack(0, 0), 'Missing scratch track')
local _, path = reaper.EnumProjects(-1, '')
assert(path:match('/tmp/chordlab%-'), 'Refusing to alter a non-scratch project')
local fx, probe = 0x1000000, 0
local _, name = reaper.TrackFX_GetFXName(t, fx, '')
assert(name:find('Chord Lab'), 'Missing Chord Lab Input FX')
local _, pname = reaper.TrackFX_GetFXName(t, probe, '')
assert(pname:find('test MIDI probe'), 'Missing test probe')
local cases, passed, failed = {}, 0, {}
local steps = {0,2,4,5,7,9,11}
local function expected(key, degree, inv, count)
  count=count or 4
  local notes, sum = {}, 0
  local root=key+steps[degree+1]
  local base={}
  for role=0,count-1 do
    local d=degree+role*2
    local n=key+steps[d%7+1]+math.floor(d/7)*12
    if n-root>=12 then n=n-12 end
    base[#base+1]=n
  end
  table.sort(base)
  for i=0,count-1 do
    local n=base[(i+inv)%count+1]+math.floor((i+inv)/count)*12
    notes[#notes+1]=n; sum=sum+n
  end
  local shift=12*math.floor((60-sum/count)/12+0.5)
  for i=1,count do notes[i]=notes[i]+shift end
  return notes
end
local function param(i) return reaper.TrackFX_GetParam(t,fx,i) end
local function command(n)
  reaper.TrackFX_SetParam(t,fx,7,n)
  reaper.TrackFX_SetParam(t,fx,6,(param(6)+1)%1000001)
end
local function note(status,n,v) reaper.StuffMIDIMessage(0,status,n,v) end
local function notes_equal(want)
  for i=1,#want do assert(param(i==5 and 16 or 8+i)==want[i], 'Wrong voice '..i) end
  local masks={0,0,0,0}
  for _,n in ipairs(want) do local j=math.floor(n/32)+1; masks[j]=masks[j]+2^(n%32) end
  for i=1,4 do assert(reaper.TrackFX_GetParam(t,probe,i-1)==masks[i], 'Output MIDI mask mismatch '..i) end
end
local function add(label,act,check,delay) cases[#cases+1]={label=label,act=act,check=check,delay=delay or .15} end
reaper.TrackFX_SetParam(t,fx,13,1)
local last_trigger=74
local function tap(n) note(0x9f,n,100); note(0x8f,n,0) end
local function silent()
  assert(param(8)==0,'Still sounding after release')
  for i=0,3 do assert(reaper.TrackFX_GetParam(t,probe,i)==0,'Stuck MIDI note') end
end
local function ascending(k,d,steps,count)
  local result=expected(k,d,0,count)
  for i=1,steps do local n=table.remove(result,1);result[#result+1]=n+12 end
  return result
end
for key=0,11 do
  add('stop before key '..key,function() command(23) end,silent)
  add('select key '..key,function() command(key) end,function() assert(param(0)==key) end)
  for degree=0,6 do
    for count=3,5 do
      local k,d,c=key,degree,count
      add(string.format('hold key=%d degree=%d count=%d',k,d,c),function()
        last_trigger=60+12+(d+2)%7; note(0x9f,last_trigger,100)
      end,function() notes_equal(expected(k,d,0,4)) end)
      for inv=0,count-1 do
        local v=inv
        add(string.format('voicing key=%d degree=%d count=%d step=%d',k,d,c,v),function()
          if v==0 then
            local current=param(15)+3
            if (c-current+3)%3>0 then command(25) end
            -- Serial commands coalesce in one audio block; use MIDI for repeated Tab.
            if (c-current+3)%3==2 then tap(85) end
          else tap(80) end
        end,function() notes_equal(ascending(k,d,v,c)) end)
      end
      add('release chord '..key..'/'..degree..'/'..count,function() note(0x8f,last_trigger,0) end,silent)
    end
  end
end
add('select C',function() command(0) end,function() assert(param(0)==0) end)
add('root C hold',function() note(0x9f,74,100) end,function() notes_equal({60,64,67,71}) end)
add('key locked while held',function() command(5) end,function() assert(param(0)==0) end)
add('L moves upward',function() tap(80) end,function() notes_equal({64,67,71,72}) end)
add('K returns downward',function() tap(79) end,function() notes_equal({60,64,67,71}) end)
add('K crosses octave',function() tap(79) end,function() notes_equal({59,60,64,67}) end)
add('low voicing remembered automatically',function() end,function() notes_equal({59,60,64,67}) end)
add('semicolon central reset',function() tap(81) end,function() notes_equal({60,64,67,71}) end)
add('release velocity zero',function() note(0x9f,74,0) end,silent)
add('recall reset degree',function() note(0x9f,74,100) end,function() notes_equal({60,64,67,71}) end)
add('semicolon again',function() tap(81) end,function() notes_equal({60,64,67,71}) end)
add('overwrite memory at centre',function() tap(81) end,function() end)
add('overlap F wins',function() note(0x9f,75,100) end,function() notes_equal(expected(0,1,0)) end)
add('release F returns held D',function() note(0x8f,75,0) end,function() notes_equal({60,64,67,71}) end)
add('repeat D does not retrigger',function()
  local ons=reaper.TrackFX_GetParam(t,probe,4); reaper.SetExtState('chordlab.test','ons',tostring(ons),false)
  note(0x9f,74,100)
end,function() assert(reaper.TrackFX_GetParam(t,probe,4)==tonumber(reaper.GetExtState('chordlab.test','ons'))) end)
add('hardware shares bass',function() note(0x90,60,101) end,function() notes_equal({60,64,67,71}) end)
add('chord release preserves physical bass',function() note(0x8f,74,0) end,function()
  assert(param(8)==0)
  assert(reaper.TrackFX_GetParam(t,probe,1)==2^28)
end)
add('physical release',function() note(0x80,60,0) end,silent)
add('S control emits exactly four notes',function()
  reaper.SetExtState('chordlab.test','ons',tostring(reaper.TrackFX_GetParam(t,probe,4)),false)
  note(0x9f,73,100)
end,function()
  notes_equal(expected(0,6,0))
  assert(reaper.TrackFX_GetParam(t,probe,4)-tonumber(reaper.GetExtState('chordlab.test','ons'))==4,'Leaked control or extra note')
end)
add('S release',function() note(0x8f,73,0) end,silent)
add('show UI',function() reaper.TrackFX_Show(t,fx,3) end,function() end)
add('mouse hold',function() command(14) end,function() notes_equal({60,64,67,71}) end)
add('mouse release',function() command(24) end,silent)
add('mouse hold before hide',function() command(14) end,function() assert(param(8)==1) end)
add('hidden UI releases mouse gate',function() reaper.TrackFX_Show(t,fx,2) end,silent,.7)
add('pedal passes through',function() note(0xb0,64,127) end,function()
  assert(reaper.TrackFX_GetParam(t,probe,6)==64 and reaper.TrackFX_GetParam(t,probe,7)==127)
end)
add('pedal reset',function() note(0xb0,64,0) end,function() end)
add('hold before mode off',function() note(0x9f,74,100) end,function() assert(param(8)==1) end)
add('mode off flushes held chord',function() reaper.TrackFX_SetParam(t,fx,13,0) end,silent)
add('ignore computer when disabled',function() note(0x9f,74,100);note(0x8f,74,0) end,silent)
local index, waiting, start = 1, false, 0
local report_path='/tmp/chordlab-acceptance.txt'
local function finish()
  command(23)
  local f=assert(io.open(report_path,'w'))
  f:write('passed=',passed,' total=',#cases,'\n',table.concat(failed,'\n')); f:close()
end
local function tick()
  local case=cases[index]
  if not case then finish(); return end
  if not waiting then
    local ok,err=pcall(case.act)
    if not ok then failed[#failed+1]=case.label..': '..tostring(err) end
    waiting=true; start=reaper.time_precise()
  elseif reaper.time_precise()-start>case.delay then
    local ok,err=pcall(case.check)
    if ok then passed=passed+1 else failed[#failed+1]=case.label..': '..tostring(err) end
    index=index+1; waiting=false
  end
  reaper.defer(tick)
end
tick()
