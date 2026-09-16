# RaceTuneRL
Hierarchical RL agent for sim racing car tuning. Driving Agent (SAC) learns to drive, Tuning Agent (Bayesian Opt) optimizes car setup. Built on Assetto Corsa + assetto_corsa_gym.

## Requirements

Windows only. `parcer/lap_recorder.py` reads Assetto Corsa's Shared Memory via
`mmap.mmap(-1, size, tagname=name, ...)` (`parcer/lap_recorder.py:104`), which
relies on Windows named file mappings and does not work on Linux/macOS without
changes.

## Setup

The RL environment and SAC baseline live in a fork of `dasGringuen/assetto_corsa_gym`,
included as a git submodule at `third_party/assetto_corsa_gym`:
https://github.com/terracodum/assetto_corsa_gym

```
git clone --recursive <this-repo-url>
```

If already cloned without `--recursive`:

```
git submodule update --init --recursive
```

Python dependencies for this repo (recording + notebooks) are in
`requirements.txt`. The submodule has its own `requirements.txt` with
different pinned versions (Python 3.9.13, PyTorch 1.12.1, CUDA 11.6, per its
upstream README) — install it separately inside `third_party/assetto_corsa_gym`
if you need to run the env/SAC code.
