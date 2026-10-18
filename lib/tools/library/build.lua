-- One-shot migration. Never run on an existing synth.rpp; later edits live in the project.
return function(config)
  assert(reaper.GetPlayState()==0,'Stop transport first')
  assert(not reaper.file_exists(config.destination),'Refusing to overwrite library')
  local old=reaper.GetSelectedTrack(0,0)
  assert(old and reaper.TrackFX_GetRecCount(old)==1,'Select the original Chord Lab track')
  local _,ident=reaper.TrackFX_GetNamedConfigParm(old,0x1000000,'fx_ident')
  assert(ident=='org.utrp.chordlab','Expected Chord Lab CLAP Input FX')
  reaper.Main_SaveProject(0,false)
  reaper.Main_OnCommand(40859,0)
  reaper.InsertTrackAtIndex(0,false)
  local input=reaper.GetTrack(0,0)
  reaper.GetSetMediaTrackInfo_String(input,'P_NAME','CHORD LAB CLAP - shared MIDI input',true)
  reaper.GetSetMediaTrackInfo_String(input,'P_EXT:utrp_library_input','1',true)
  reaper.TrackFX_CopyToTrack(old,0x1000000,input,0x1000000,false)
  reaper.TrackFX_SetParamNormalized(input,0x1000000,13,1)
  reaper.SetMediaTrackInfo_Value(input,'B_MAINSEND',0)
  reaper.SetMediaTrackInfo_Value(input,'B_SOLO_DEFEAT',1)
  reaper.SetMediaTrackInfo_Value(input,'I_RECINPUT',4096+63*32)
  reaper.SetMediaTrackInfo_Value(input,'I_RECARM',0)
  reaper.SetMediaTrackInfo_Value(input,'I_RECMON',1)
  reaper.SetMediaTrackInfo_Value(reaper.GetMasterTrack(0),'D_VOL',config.master_volume)
  local groups={}
  for _,p in ipairs(config.patches) do
    if not groups[p.group] then groups[#groups+1]=p.group;groups[p.group]={} end
    table.insert(groups[p.group],p)
  end
  for _,group in ipairs(groups) do
    reaper.InsertTrackAtIndex(reaper.CountTracks(0),false)
    local folder=reaper.GetTrack(0,reaper.CountTracks(0)-1)
    reaper.GetSetMediaTrackInfo_String(folder,'P_NAME',group,true)
    reaper.SetMediaTrackInfo_Value(folder,'I_FOLDERDEPTH',1)
    for i,p in ipairs(groups[group]) do
      reaper.InsertTrackAtIndex(reaper.CountTracks(0),false)
      local t=reaper.GetTrack(0,reaper.CountTracks(0)-1)
      reaper.GetSetMediaTrackInfo_String(t,'P_NAME',p.name,true)
      reaper.GetSetMediaTrackInfo_String(t,'P_EXT:utrp_patch',p.group..'/'..p.name,true)
      reaper.GetSetMediaTrackInfo_String(t,'P_EXT:utrp_patch_source',p.path,true)
      reaper.SetMediaTrackInfo_Value(t,'D_VOL',config.track_volume)
      reaper.SetMediaTrackInfo_Value(t,'I_RECINPUT',-1)
      reaper.SetMediaTrackInfo_Value(t,'I_RECARM',0)
      if i==#groups[group] then reaper.SetMediaTrackInfo_Value(t,'I_FOLDERDEPTH',-1) end
      local fx=reaper.TrackFX_AddByName(t,'CLAPi: Surge XT (Surge Synth Team)',false,-1)
      assert(fx==0,'Cannot instantiate Surge XT')
      local f=assert(io.open(p.state,'r'));local chunk=f:read('*a');f:close()
      assert(reaper.TrackFX_SetNamedConfigParm(t,fx,'clap_chunk',chunk),'Patch load failed: '..p.name)
      local send=reaper.CreateTrackSend(input,t)
      reaper.SetTrackSendInfo_Value(input,0,send,'I_SRCCHAN',-1) -- MIDI only
      reaper.SetTrackSendInfo_Value(input,0,send,'I_MIDIFLAGS',0)
      if p.group..'/'..p.name==config.initial_patch then
        reaper.SetMediaTrackInfo_Value(t,'I_SOLO',2)
      end
    end
  end
  reaper.SetOnlyTrackSelected(input)
  reaper.TrackList_AdjustWindows(false)
  reaper.UpdateArrange()
  -- Give Surge's audio thread time to consume its queued patch states before saving.
  local until_time=reaper.time_precise()+2
  local function save()
    if reaper.time_precise()<until_time then reaper.defer(save);return end
    assert(reaper.CountMediaItems(0)==0,'Library must not contain media items')
    for i=1,reaper.CountTracks(0)-1 do
      local t=reaper.GetTrack(0,i)
      if reaper.TrackFX_GetCount(t)>0 then
        reaper.TrackFX_SetOffline(t,0,reaper.GetMediaTrackInfo_Value(t,'I_SOLO')==0)
      end
    end
    for i=0,reaper.GetTrackNumSends(input,0)-1 do
      local t=reaper.GetTrackSendInfo_Value(input,0,i,'P_DESTTRACK')
      reaper.SetTrackSendInfo_Value(input,0,i,'B_MUTE',reaper.GetMediaTrackInfo_Value(t,'I_SOLO')==0 and 1 or 0)
    end
    reaper.Main_SaveProjectEx(0,'/tmp/synth-building.rpp',8)
    local f=assert(io.open('/tmp/library-build-result.txt','w'))
    f:write('tracks=',reaper.CountTracks(0),' patches=',#config.patches,' items=0\n');f:close()
  end
  reaper.defer(save)
end
