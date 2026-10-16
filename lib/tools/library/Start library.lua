-- Safe startup action: do not toggle an already running audition session off.
if reaper.GetExtState('utrp.library','running')~='' then return end
local input=reaper.GetTrack(0,0)
if not input then return end
local _,marker=reaper.GetSetMediaTrackInfo_String(input,'P_EXT:utrp_library_input','',false)
if marker~='1' then return end
local _,path=reaper.get_action_context()
local directory=path:match('^(.*[/\\])')
local action=reaper.AddRemoveReaScript(true,0,directory..'Library mode.lua',true)
assert(action>0,'Cannot register Library mode')
reaper.Main_OnCommand(action,0)
