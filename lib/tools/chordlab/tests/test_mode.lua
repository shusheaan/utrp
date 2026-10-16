-- Host API simulation only: does not emulate JSFX audio or native window events.
local source = 'lib/tools/chordlab/'
local function host(initially_open, initially_vkb)
  local track = {I_RECINPUT=0, I_RECARM=0, I_RECMON=0, I_FXEN=1}
  local other = {I_RECINPUT=6112, I_RECARM=0}
  local s = {track=track, other=other, project=1, selected=track, ext={},
    params={[6]=0, [7]=23, [8]=0, [13]=0}, enabled=true, offline=false,
    floating=initially_open, chain=false, valid=true, exists=true,
    toggles={[40377]=initially_vkb and 1 or 0, [40637]=0},
    shows=0, enables=0, stops=0, warnings=0, writes=0}
  local api, env = {}, {}
  local function run(name) assert(loadfile(source..name, 't', env))() end
  api.GetSelectedTrack=function() return s.selected end
  api.EnumProjects=function() return s.project end
  api.TrackFX_GetRecCount=function() return s.exists and 1 or 0 end
  api.TrackFX_GetNamedConfigParm=function() return true,'ChordLab/chordlab.jsfx' end
  api.TrackFX_GetFXGUID=function(_,fx) assert(fx==0x1000000);return 'fx' end
  api.TrackFX_AddByName=function() s.exists=true;return 0 end
  api.GetTrackGUID=function() return 'track' end
  api.genGuid=function() return 'session' end
  api.GetMediaTrackInfo_Value=function(t,k) return t[k] end
  api.SetMediaTrackInfo_Value=function(t,k,v) t[k]=v;s.writes=s.writes+1 end
  api.SetTrackUIInputMonitor=function(t,v) t.I_RECMON=v end
  api.GetToggleCommandState=function(id) return assert(s.toggles[id]) end
  api.Main_OnCommand=function(id)
    if id==1 then run('Chord Lab mode.lua')
    else s.toggles[id]=1-s.toggles[id];s.writes=s.writes+1 end
  end
  api.ValidatePtr2=function() return s.valid end
  api.TrackFX_GetParam=function(_,_,p) return assert(s.params[p]) end
  api.TrackFX_SetParam=function(_,_,p,v)
    s.params[p]=v;s.writes=s.writes+1
    if p==6 and s.params[7]==23 then s.stops=s.stops+1 end
  end
  api.TrackFX_GetEnabled=function() return s.enabled end
  api.TrackFX_GetOffline=function() return s.offline end
  api.TrackFX_SetEnabled=function(_,_,v) s.enabled=v;s.enables=s.enables+1 end
  api.TrackFX_GetOpen=function() return s.floating or s.chain end
  api.TrackFX_Show=function(_,fx,mode)
    assert(fx==0x1000000 and mode==3);s.floating=true;s.shows=s.shows+1
  end
  api.TrackFX_SetOpen=function(_,fx,v)
    assert(fx==0x1000000 and not v);s.floating=false;s.chain=false
  end
  api.CountTracks=function() return 2 end
  api.GetTrack=function(_,i) return i==0 and track or other end
  api.GetExtState=function(section,k) return s.ext[section..'/'..k] or '' end
  api.SetExtState=function(section,k,v) s.ext[section..'/'..k]=v end
  api.DeleteExtState=function(section,k) s.ext[section..'/'..k]=nil end
  api.atexit=function(f) s.cleanup=f end
  api.defer=function(f) s.deferred=f end
  api.MB=function() s.warnings=s.warnings+1 end
  api.get_action_context=function() return false,'/mock/Open Chord Lab.lua' end
  api.AddRemoveReaScript=function(_,_,path)
    assert(path=='/mock/Chord Lab mode.lua');return 1
  end
  env.reaper=api;env.math=math
  s.run=run
  s.tick=function()
    local f=assert(s.deferred);s.deferred=nil;f()
  end
  return s
end
local checks=0
local function check(value) assert(value);checks=checks+1 end
local s=host(false,false)
s.run('Chord Lab mode.lua')
-- Background startup never opens VKB or the FX editor.
check(s.shows==0 and s.enables==0 and s.toggles[40377]==0)
check(s.params[13]==0 and s.toggles[40637]==0)
check(s.track.I_RECARM==1 and s.track.I_RECMON==1 and s.track.I_RECINPUT==6112)
local writes=s.writes;s.tick();check(s.writes==writes)
-- Opening either Input FX editor view enables VKB and computer monitoring.
s.chain=true;s.tick()
check(s.toggles[40377]==1 and s.toggles[40637]==1 and s.params[13]==1)
check(s.shows==0 and s.enabled and s.enables==0)
s.floating=true;s.chain=false;writes=s.writes;s.tick();check(s.writes==writes)
-- Hiding the editor does not stop the open VKB or computer notes.
s.toggles[40377]=1;s.tick();check(s.params[13]==1 and s.toggles[40637]==1)
s.params[8]=1;s.floating=false;s.tick()
check(s.stops==0 and s.params[13]==1 and s.toggles[40377]==1)
check(s.track.I_RECARM==1 and s.track.I_RECMON==1 and s.enabled)
-- Closing VKB releases generated notes but neither closes nor opens the editor.
s.floating=true;s.tick();s.toggles[40377]=0;s.tick()
check(s.stops==1 and s.params[13]==0 and s.toggles[40637]==0)
check(s.floating and s.enabled and s.enables==0)
check(s.ext['utrp.chordlab/running']=='session')
writes=s.writes;s.tick();check(s.writes==writes and s.toggles[40377]==0)
s.params[8]=0;s.floating=false;s.toggles[40377]=1;s.tick()
check(not s.floating and s.shows==0 and s.params[13]==1)
s.floating=true;s.tick()
-- Stable polling and track selection never steal focus or change the input target.
s.selected=s.other;writes=s.writes;s.tick()
check(s.writes==writes and s.shows==0 and s.other.I_RECARM==0)
-- Explicit bypass is independent of windows; re-enable resumes computer input.
s.enabled=false;s.tick()
check(s.params[13]==0 and s.floating and s.toggles[40377]==1)
s.floating=false;s.tick();check(not s.enabled and s.params[13]==0)
s.floating=true;s.tick();check(not s.enabled and s.params[13]==0)
s.enabled=true;s.tick();check(s.params[13]==1)
-- Existing held-note bypass safety remains asynchronous.
s.params[8]=1;s.enabled=false;s.tick()
check(s.enabled and s.enables==1)
s.params[8]=0;s.tick();check(not s.enabled and s.enables==2)
s.tick();check(s.params[13]==0 and s.toggles[40637]==0)
s.enabled=true;s.tick();check(s.params[13]==1)
-- Offline/chain bypass suspend computer control, without hiding the editor.
s.offline=true;s.tick();check(s.params[13]==0 and s.floating)
s.offline=false;s.tick();check(s.params[13]==1)
s.track.I_FXEN=0;s.tick();check(s.params[13]==0)
s.track.I_FXEN=1;s.tick();check(s.params[13]==1)
-- Conflicting armed MIDI receivers block computer keys, then recover without restart.
s.other.I_RECARM=1;s.tick();check(s.params[13]==0 and s.warnings==1)
s.tick();check(s.warnings==1)
s.other.I_RECARM=0;s.tick();check(s.params[13]==1)
-- Project switch restores input/send state, but preserves the manually opened VKB.
s.project=2;s.tick();s.tick();check(s.deferred==nil)
s.cleanup()
check(s.ext['utrp.chordlab/running']==nil and s.params[13]==0)
check(s.track.I_RECINPUT==0 and s.track.I_RECARM==0 and s.track.I_RECMON==0)
check(s.toggles[40377]==1 and s.toggles[40637]==0)
-- Explicit Open retains its original action contract (open/start, then stop).
s=host(false,false);s.exists=false;s.run('Open Chord Lab.lua');s.tick()
check(s.exists and s.floating and s.shows==1 and s.params[13]==1 and s.toggles[40377]==1)
s.run('Open Chord Lab.lua');s.tick();s.tick();check(s.deferred==nil)
s.cleanup();check(s.toggles[40377]==1 and s.ext['utrp.chordlab/running']==nil)
-- A saved open FX editor is preserved; no fresh show/focus request at startup.
s=host(true,false);s.run('Chord Lab mode.lua')
check(s.floating and s.shows==0 and s.toggles[40377]==1 and s.params[13]==1)
s.valid=false;s.tick();check(s.deferred==nil);s.cleanup()
check(s.ext['utrp.chordlab/running']==nil)
-- Pre-existing manual VKB remains open, even with no Chord Lab editor.
s=host(false,true);s.run('Chord Lab mode.lua')
check(not s.floating and s.params[13]==1 and s.toggles[40377]==1)
s.toggles[40377]=0;s.tick();s.cleanup()
check(s.toggles[40377]==0)
print('Chord Lab window lifecycle: '..checks..' assertions passed')
