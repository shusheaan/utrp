-- Startup is idempotent and a nominated piano overrides only library solos.
local function scenario(has_default, running)
  local tracks={{input='1'}, {patch='basic/piano',default=has_default and '1' or '',solo=0},
    {patch='old/synth',solo=2}, {solo=1}}
  local calls,selected={},nil
  reaper={
    GetExtState=function() return running and 'session' or '' end,
    GetTrack=function(_,i) return tracks[i+1] end,
    CountTracks=function() return #tracks end,
    GetSetMediaTrackInfo_String=function(t,k)
      local fields={['P_EXT:utrp_library_input']='input',
        ['P_EXT:utrp_library_default']='default',['P_EXT:utrp_patch']='patch'}
      return true,t[fields[k]] or ''
    end,
    TrackFX_GetFXName=function() return true,'LV2i: sfizz (SFZTools)' end,
    TrackFX_GetInstrument=function() error('Default may be offline') end,
    SetMediaTrackInfo_Value=function(t,k,v) assert(k=='I_SOLO');t.solo=v end,
    get_action_context=function() return nil,'/mock/Start library.lua' end,
    AddRemoveReaScript=function(_,_,p) assert(p=='/mock/Library mode.lua');return 99 end,
    Main_OnCommand=function(id) calls[#calls+1]=id end,
    SetOnlyTrackSelected=function(t) selected=t end,
  }
  dofile('lib/tools/library/Start library.lua')
  if running then assert(#calls==0 and selected==nil and tracks[3].solo==2)
  elseif has_default then
    assert(tracks[2].solo==2 and tracks[3].solo==0 and tracks[4].solo==1)
    assert(selected==tracks[2] and table.concat(calls,',')=='99,40913')
  else assert(tracks[3].solo==2 and selected==nil and #calls==1) end
end
scenario(true,false)
scenario(false,false)
scenario(true,true)
print('Library startup: default piano, legacy projects, idempotency passed')
