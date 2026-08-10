-- utrp_soundmatch.lua — 选中一个音频 item,一键得到 top-K 音色候选的试听轨。
--
-- 做什么:取选中 item 的源文件与时间范围 -> 调 repatch/reabridge.py
-- (索引检索 + surgepy 渲染试听)-> 在 item 下方为每个候选建一条轨,
-- 轨名 = 排名/距离/patch 路径,试听 wav 摆在 item 同一位置。
-- 听中哪个,就照轨名去 Surge 浏览器载入该 patch,再用 refine.py 精调。
--
-- 安装:lib/link.sh 会把 tools/reaper 链接进 ~/.config/REAPER/Scripts/utrp;
-- REAPER 里 Actions -> Show action list -> Load ReaScript 选本文件并绑键。

local HOME = os.getenv("HOME")
local PYTHON = HOME .. "/.cache/timbre-pipeline/venv-render/bin/python"
local BRIDGE = HOME .. "/work/utrp/lib/tools/repatch/reabridge.py"
local MODE, K = "pad", 5

local function msg(s) reaper.ShowConsoleMsg(tostring(s) .. "\n") end

local item = reaper.GetSelectedMediaItem(0, 0)
if not item then
  reaper.MB("先选中一个音频 item", "utrp soundmatch", 0)
  return
end
local take = reaper.GetActiveTake(item)
if not take or reaper.TakeIsMIDI(take) then
  reaper.MB("选中的 item 不是音频", "utrp soundmatch", 0)
  return
end

local src = reaper.GetMediaSourceFileName(reaper.GetMediaItemTake_Source(take))
local offs = reaper.GetMediaItemTakeInfo_Value(take, "D_STARTOFFS")
local rate = reaper.GetMediaItemTakeInfo_Value(take, "D_PLAYRATE")
local len = reaper.GetMediaItemInfo_Value(item, "D_LENGTH")
local pos = reaper.GetMediaItemInfo_Value(item, "D_POSITION")
local t0, t1 = offs, offs + len * rate

local cmd = string.format('%s "%s" "%s" --t0 %.3f --t1 %.3f --mode %s --k %d',
                          PYTHON, BRIDGE, src, t0, t1, MODE, K)
msg("utrp soundmatch: " .. src .. string.format("  [%.1fs..%.1fs]", t0, t1))
local ret = reaper.ExecProcess(cmd, 0)          -- 0 = wait; ~5-10s for K=5
if not ret then
  reaper.MB("ExecProcess 失败(检查 PYTHON/BRIDGE 路径)", "utrp soundmatch", 0)
  return
end

local cands = {}
for line in ret:gmatch("[^\n]+") do
  local rank, dist, rel, wav = line:match("^CAND\t(%d+)\t([%d%.]+)\t(.-)\t(.+)$")
  if rank then
    cands[#cands + 1] = { rank = rank, dist = dist, rel = rel, wav = wav }
  elseif line:match("^ERR\t") then
    msg(line)
  end
end
if #cands == 0 then
  reaper.MB("没有候选返回(先跑 soundmatch.py build?看 console)",
            "utrp soundmatch", 0)
  return
end

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)
local ref_track = reaper.GetMediaItemTrack(item)
local base_idx = reaper.GetMediaTrackInfo_Value(ref_track, "IP_TRACKNUMBER")
for i, c in ipairs(cands) do
  local idx = base_idx + i - 1
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME",
    string.format("~%s d%s · %s", c.rank, c.dist, c.rel), true)
  reaper.SetOnlyTrackSelected(tr)
  reaper.SetEditCurPos(pos, false, false)
  reaper.InsertMedia(c.wav, 0)
  if i > 1 then reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1) end
end
reaper.PreventUIRefresh(-1)
reaper.UpdateArrange()
reaper.Undo_EndBlock("utrp soundmatch: " .. #cands .. " candidates", -1)
msg(string.format("%d 个候选已建轨(仅 #1 未静音);听完在 Surge 浏览器里"
                  .. "按轨名载入 patch,精调用 refine.py", #cands))
