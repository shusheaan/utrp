-- Native startup waits for project loading and never opens the legacy VKB.
local now,ready,running,registered,calls=0,false,false,0,0
local deferred
reaper={
 time_precise=function() return now end,
 defer=function(f) deferred=f end,
 GetExtState=function() return running and 'token' or '' end,
 GetTrack=function() return ready and {} or nil end,
 GetSetMediaTrackInfo_String=function() return true,'1' end,
 GetResourcePath=function() return '/mock' end,
 AddRemoveReaScript=function(_,_,path)
  assert(path=='/mock/Scripts/SynthLibrary/Start library.lua');registered=registered+1;return 999
 end,
 Main_OnCommand=function(id) assert(id==999);calls=calls+1 end,
}
local function tick()
 local f=deferred;deferred=nil;assert(f);f()
end
dofile('lib/tools/library/startup.lua');tick();assert(calls==0 and deferred)
ready=true;tick();assert(calls==1 and registered==1 and not deferred)
running=true;dofile('lib/tools/library/startup.lua');tick();assert(calls==1 and not deferred)
running=false;ready=false;dofile('lib/tools/library/startup.lua');now=11;tick();assert(not deferred and calls==1)
print('CLAP startup: load wait, startup, idempotency and timeout passed')
