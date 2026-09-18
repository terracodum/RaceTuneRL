# RaceTuneRL

Hierarchical RL for sim racing car tuning in Assetto Corsa. A Driving Agent
(SAC) learns to drive; a Tuning Agent (Bayesian Optimization) searches car
setup on top of it. Built on a fork of
[`dasGringuen/assetto_corsa_gym`](https://github.com/terracodum/assetto_corsa_gym).

**Status:** the AC↔plugin↔Python wiring is verified end-to-end (a pretrained
checkpoint drives a real lap in AC). Target track (Magione) and car (Porsche
911 RSR 2017) are not set up yet, and manual-gearbox control isn't
implemented — see `docs/acgym_audit.md` for the full list of what's missing.

Windows only. `parcer/lap_recorder.py` reads Assetto Corsa's own Shared
Memory via `mmap.mmap(-1, size, tagname=name, ...)`, which relies on Windows
named file mappings.

## Layout

```
environment.yml            # conda env "p309" for third_party/assetto_corsa_gym
requirements.txt           # deps for this repo's own notebooks/ and parcer/
third_party/assetto_corsa_gym/   # our fork, git submodule

parcer/
  lap_recorder.py          # records a human lap from AC's Shared Memory to CSV
  fix_car_z_sign.py        # one-off: derive a car_z-corrected copy of an old CSV
data/                      # raw recordings - never edited in place; derived
                            # copies live alongside with a suffix, e.g. .car_z_fixed.csv
notebooks/                 # EDA and zone-reward exploration on recorded laps

scripts/
  gui_launcher.py          # GUI to launch/stop/watch a run without a console
  run_tracker.py           # shared PID/log state gui_launcher.py and Bash both use
  check_env.py             # verifies the p309 env (torch/CUDA/fork imports)
  extract_lap_times.py     # parses lap times out of a finished run's output
  diagnostics/             # one-off troubleshooting tools (not part of normal use)

docs/
  install_plugin.md        # step-by-step: vJoy, the AC plugin, Custom Shaders
                            # Patch, FPS - everything needed before a run
  run_monza_bmw_z4_gt3_checkpoint.md  # worked example: run a pretrained checkpoint
  acgym_audit.md            # code-level audit of the fork (not its README) -
                            # connection protocol, obs/action space, reward,
                            # what's missing for Magione/RSR/manual gearbox
  zone_reward_notes.md      # design notes for the zone-based reward (not yet code)
  reports/                  # write-ups of specific runs/experiments
```

## Getting started

1. **Clone with the submodule:**
   ```
   git clone --recursive <this-repo-url>
   ```
   Already cloned without `--recursive`? `git submodule update --init --recursive`

2. **Two separate Python environments** (they pin incompatible dependency
   versions, do not merge them):
   - This repo's own tools (`notebooks/`, `parcer/`, `scripts/`) — whatever
     Python you already use, deps in `requirements.txt`.
   - The fork (`third_party/assetto_corsa_gym`) — a dedicated conda env:
     ```
     conda env create -f environment.yml
     conda activate p309
     ```

3. **Install the AC plugin** — follow `docs/install_plugin.md` (vJoy, the
   plugin folder, Custom Shaders Patch + "Use extended physics", FPS capped
   at 50). This is the part most likely to silently misbehave; the doc lists
   every failure mode we actually hit.

4. **Verify the environment:**
   ```
   conda activate p309
   python scripts\check_env.py
   ```
   Should report CUDA available and successful imports from the fork.

5. **Run something** — either double-click the GUI (`scripts\gui_launcher.py`,
   or the desktop shortcut if you made one) and pick a preset, or follow
   `docs/run_monza_bmw_z4_gt3_checkpoint.md` for a concrete worked example
   (load a pretrained checkpoint, watch it drive).

## Day to day

`scripts/gui_launcher.py` is the normal way to launch runs — no console
needed, live log, a Stop button that actually stops AC-connected processes
cleanly. It shares state (`.run_state.json`, `.run_logs/`) with
`scripts/run_tracker.py`, so a run started from a plain terminal is just as
visible and stoppable from the GUI, and vice versa.

## Reference

- `docs/acgym_audit.md` — what the fork's code actually does, with
  `file:line` citations, not what its README claims.
- `docs/reports/` — results and troubleshooting notes from specific runs.
- Session-by-session history lives outside this repo (Notion), linked from
  the project's own notes there.
