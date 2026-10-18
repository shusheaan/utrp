-- Installed as Scripts/__startup.lua; shared CLAP startup, no legacy VKB.
local deadline=reaper.time_precise()+10
local function tick()
 if reaper.GetExtState('utrp.library','running')~='' then return end
 local input=reaper.GetTrack(0,0)
 if input then
  local _,marker=reaper.GetSetMediaTrackInfo_String(input,'P_EXT:utrp_library_input','',false)
  if marker=='1' then
   local action=reaper.AddRemoveReaScript(true,0,reaper.GetResourcePath()..'/Scripts/SynthLibrary/Start library.lua',true)
   assert(action>0,'Cannot register library startup')
   reaper.Main_OnCommand(action,0);return
  end
 end
 if reaper.time_precise()<deadline then reaper.defer(tick) end
end
reaper.defer(tick)
