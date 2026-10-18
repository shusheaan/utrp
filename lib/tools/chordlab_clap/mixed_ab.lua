-- Mixed computer/hardware protocol regression. Scratch profile only; no hardware.
local root=assert(reaper.GetResourcePath():match('^(/tmp/chordlab%-mixed%-.+)/reaper$'))
local marker=assert(io.open(root..'/manifest.json'));marker:close()
assert(reaper.CountTracks(0)==0,'Empty scratch project required')
local input=root:match('%-input$')~=nil
local flag=input and 0x1000000 or 0
reaper.gmem_attach('ChordLab_AB_Prototype')
for i=0,101002 do reaper.gmem_write(i,0) end
local function setup(lane)
  reaper.InsertTrackAtIndex(lane,false)
  local track=reaper.GetTrack(0,lane)
  local plugin=lane==0 and 'ChordLab/chordlab.jsfx' or 'CLAP: Chord Lab'
  assert(reaper.TrackFX_AddByName(track,plugin,input,-1)==0)
  reaper.TrackFX_SetParamNormalized(track,flag,13,1)
  assert(reaper.TrackFX_AddByName(track,'ChordLab/ab_source.jsfx',input,-1)==1)
  reaper.TrackFX_CopyToTrack(track,flag+1,track,flag,true)
  reaper.TrackFX_SetParam(track,flag,0,lane)
  local capture=reaper.TrackFX_AddByName(track,'ChordLab/ab_capture.jsfx',false,-1)
  reaper.TrackFX_SetParam(track,capture,0,lane)
  reaper.GetSetMediaTrackInfo_String(track,'P_NAME',lane==0 and 'JSFX mixed' or 'CLAP mixed',true)
  reaper.SetMediaTrackInfo_Value(track,'I_RECINPUT',4096+62*32)
  reaper.SetMediaTrackInfo_Value(track,'I_RECARM',1)
  reaper.SetMediaTrackInfo_Value(track,'I_PERFFLAGS',3)
  reaper.SetTrackUIInputMonitor(track,1,0)
  return track
end
local tracks={setup(0),setup(1)}
local cases={}
local function add(label,events,expected)
  cases[#cases+1]={label=label,events=events,expected=expected}
end
local function chord(status,offset,exclude)
  local result={}
  for _,note in ipairs({60,64,67,71}) do
    if note~=exclude then result[#result+1]={offset,status,note,status==0x90 and 64 or 0} end
  end
  return result
end
local function pedal(value)
  local result={}
  for ch=0,14 do result[#result+1]={0,0xb0+ch,64,value} end
  return result
end
for _,ch in ipairs({0,1,14}) do
  local on,off=0x90+ch,0x80+ch
  local prefix='channel '..(ch+1)..' '
  add(prefix..'computer chord',{{13,0x9f,74,100}},chord(0x90,13))
  add(prefix..'external F sharp',{{31,on,66,93}},{{31,on,66,93}})
  add(prefix..'external D scale tone',{{47,on,62,37}},{{47,on,62,37}})
  add(prefix..'external release',{{12,off,66,0},{53,off,62,0}},{{12,off,66,0},{53,off,62,0}})
  add(prefix..'shared C while chord held',{{17,on,60,81}},ch==0 and {} or {{17,on,60,81}})
  add(prefix..'computer release preserves hardware C',{{25,0x8f,74,0}},chord(0x80,25,ch==0 and 60 or nil))
  add(prefix..'last owner releases C',{{39,off,60,0}},{{39,off,60,0}})
  add(prefix..'hardware C first',{{11,on,60,51}},{{11,on,60,51}})
  add(prefix..'computer joins hardware C',{{21,0x9f,74,100}},chord(0x90,21,ch==0 and 60 or nil))
  add(prefix..'hardware release preserves chord C',{{33,off,60,0}},ch==0 and {} or {{33,off,60,0}})
  add(prefix..'final computer release',{{45,0x8f,74,0}},chord(0x80,45))
  add(prefix..'sustain on',{{0,0x9f,82,100},{1,0x8f,82,0}},pedal(127))
  add(prefix..'physical pedal cannot cancel lock',{{43,0xb0+ch,64,0}},{{43,0xb0+ch,64,127}})
  add(prefix..'sustain off',{{0,0x9f,82,100},{1,0x8f,82,0}},pedal(0))
end
local function text(events)
  local values={}
  for _,e in ipairs(events) do values[#values+1]=string.format('%d:%02x:%d:%d',table.unpack(e)) end
  return table.concat(values,',')
end
local function capture(lane)
  local base=1000+lane*50000
  assert(reaper.gmem_read(base+1)==0,'Capture overflow')
  local events={}
  for i=0,reaper.gmem_read(base)-1 do
    local event={}
    for j=0,3 do event[#event+1]=reaper.gmem_read(base+2+i*4+j) end
    events[#events+1]=event
  end
  return text(events)
end
local log=assert(io.open(root..'/mixed-events.tsv','w'))
log:write('case\tlabel\texpected\tJSFX\tCLAP\n')
local step,passed,deadline=0,0,reaper.time_precise()+1
local function finish(error)
  log:close()
  local f=assert(io.open(root..'/mixed-result.txt','w'))
  f:write('placement=',input and 'Input FX' or 'Track FX','\npassed=',passed,'/',#cases,'\n')
  if error then f:write('ERROR=',error,'\n') end
  f:close()
  reaper.Main_SaveProject(0,false)
  reaper.TrackFX_Show(tracks[2],flag+1,3)
end
local tick
local function safe()
  local ok,err=pcall(tick);if not ok then finish(tostring(err)) end
end
tick=function()
  if reaper.time_precise()<deadline then reaper.defer(safe);return end
  if step>0 then
    local case=cases[step]
    local a,b,expected=capture(0),capture(1),text(case.expected)
    log:write(step,'\t',case.label,'\t',expected,'\t',a,'\t',b,'\n');log:flush()
    assert(reaper.gmem_read(10)==step and reaper.gmem_read(11)==step,'Both lanes processed')
    assert(a==expected and b==expected,'Mixed MIDI differs: '..case.label)
    passed=passed+1
  end
  step=step+1
  if step>#cases then finish();return end
  reaper.gmem_write(1,#cases[step].events)
  for i,event in ipairs(cases[step].events) do
    for j,value in ipairs(event) do reaper.gmem_write(30+(i-1)*4+j-1,value) end
  end
  reaper.gmem_write(0,step)
  deadline=reaper.time_precise()+.12
  reaper.defer(safe)
end
reaper.defer(safe)
