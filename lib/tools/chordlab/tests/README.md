# Embedded engine validation

[中文](README.cn.md) · [Current product](../../chordlab_clap/README.md)

Run `python -m pytest lib/tools/chordlab/tests lib/tools/chordlab_clap lib/tools/library -q`.
Theme tests validate generated assets and reject invalid configuration. Library lifecycle
mocks exercise the current CLAP-only host workflow.

Lua/JSFX probe fixtures in this directory are musical-engine references for isolated
scratch REAPER projects only. They are not installed into the user's profile. Use the
current CLAP `stage_port.py`, `ab_test.lua`, `state_ab.lua`, `parameter_ab.lua` and
mixed-input tests for host acceptance. The old installer, VKB map and Lua-mode tests
were deleted together with that product; historical test counts do not describe the
current suite. See the CLAP retirement report for the new results.
