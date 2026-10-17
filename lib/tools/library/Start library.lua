-- Safe startup action: do not toggle an already running audition session off.
if reaper.GetExtState('utrp.library','running')~='' then return end
local input=reaper.GetTrack(0,0)
if not input then return end
local _,marker=reaper.GetSetMediaTrackInfo_String(input,'P_EXT:utrp_library_input','',false)
if marker~='1' then return end
-- A project may nominate one startup sound, independent of its last saved selection.
local default=nil
for i=1,reaper.CountTracks(0)-1 do
  local track=reaper.GetTrack(0,i)
  local _,value=reaper.GetSetMediaTrackInfo_String(track,'P_EXT:utrp_library_default','',false)
  if value=='1' then
    assert(not default,'Multiple default library sounds')
    local _,patch=reaper.GetSetMediaTrackInfo_String(track,'P_EXT:utrp_patch','',false)
    assert(patch~='','Default sound must be a library entry')
    local ok,name=reaper.TrackFX_GetFXName(track,0)
    assert(ok and (name:find('Surge XT',1,true) or name:find('LV2i: sfizz',1,true)),
      'Default sound needs Surge XT or sfizz')
    default=track
  end
end
if default then
  for i=1,reaper.CountTracks(0)-1 do
    local track=reaper.GetTrack(0,i)
    local _,patch=reaper.GetSetMediaTrackInfo_String(track,'P_EXT:utrp_patch','',false)
    if patch~='' then reaper.SetMediaTrackInfo_Value(track,'I_SOLO',track==default and 2 or 0) end
  end
end
local _,path=reaper.get_action_context()
local directory=path:match('^(.*[/\\])')
local action=reaper.AddRemoveReaScript(true,0,directory..'Library mode.lua',true)
assert(action>0,'Cannot register Library mode')
reaper.Main_OnCommand(action,0)
if default then
  reaper.SetOnlyTrackSelected(default)
  reaper.Main_OnCommand(40913,0) -- Track: Vertical scroll selected tracks into view
end
