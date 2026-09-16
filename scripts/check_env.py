"""
Проверка окружения p309 (third_party/assetto_corsa_gym).

Запуск:
    conda activate p309
    python scripts/check_env.py

Ничего не подключается к Assetto Corsa - только импорт модулей и версии.
"""

import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SUBMODULE_ROOT = REPO_ROOT / "third_party" / "assetto_corsa_gym"

sys.path.insert(0, str(SUBMODULE_ROOT / "assetto_corsa_gym"))
sys.path.insert(0, str(SUBMODULE_ROOT / "algorithm" / "discor"))

failures = []


def check(label, fn):
    try:
        result = fn()
        print(f"[OK] {label}: {result}")
    except Exception as e:
        print(f"[FAIL] {label}: {e}")
        failures.append(label)


def check_python():
    return sys.version.split()[0]


def check_torch():
    import torch
    cuda_ok = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_ok else "N/A"
    if not cuda_ok:
        raise RuntimeError("torch.cuda.is_available() is False")
    return f"torch {torch.__version__}, cuda available, device: {device_name}"


def check_numpy():
    import numpy
    return numpy.__version__


def check_gym():
    import gym
    return gym.__version__


def check_pandas():
    import pandas
    return pandas.__version__


def check_matplotlib():
    import matplotlib
    return matplotlib.__version__


def check_tensorboard():
    import tensorboard
    return tensorboard.__version__


def check_wandb():
    import wandb
    return wandb.__version__


def check_ac_env_module():
    import AssettoCorsaEnv.ac_env as ac_env
    return ac_env.__file__


def check_ac_client_module():
    from AssettoCorsaEnv.ac_client import Client
    return Client.__module__


def check_discor_sac():
    from discor.algorithm import SAC, DisCor
    return f"{SAC.__module__}.{SAC.__name__}, {DisCor.__module__}.{DisCor.__name__}"


def check_discor_agent():
    from discor.agent import Agent
    return f"{Agent.__module__}.{Agent.__name__}"


if __name__ == "__main__":
    print(f"Repo root: {REPO_ROOT}")
    print(f"Submodule root: {SUBMODULE_ROOT}")
    print()

    check("Python version", check_python)
    check("torch + CUDA", check_torch)
    check("numpy", check_numpy)
    check("gym", check_gym)
    check("pandas", check_pandas)
    check("matplotlib", check_matplotlib)
    check("tensorboard", check_tensorboard)
    check("wandb", check_wandb)
    check("AssettoCorsaEnv.ac_env import", check_ac_env_module)
    check("AssettoCorsaEnv.ac_client import", check_ac_client_module)
    check("discor.algorithm (SAC, DisCor) import", check_discor_sac)
    check("discor.agent.Agent import", check_discor_agent)

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
        sys.exit(1)
    else:
        print("All checks passed.")
        sys.exit(0)
