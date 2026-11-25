"""Writes research/results/host_info.json — CPU/RAM/library versions for
the methodology write-up. Run once per environment (host, not Docker)."""
import json
import os
import platform
import subprocess
import sys

import psutil

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "results", "host_info.json")


def _sysctl(key):
    try:
        return subprocess.check_output(["sysctl", "-n", key], text=True).strip()
    except Exception:
        return None


def pkg_version(name):
    try:
        import importlib.metadata as md
        return md.version(name)
    except Exception:
        return None


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    info = {
        "platform": platform.platform(),
        "python_version": sys.version,
        "execution_context": (
            "Host machine, dedicated venv at research/.venv -- NOT inside the "
            "python-api Docker container (that image has no bind mount and no "
            "research/ dependencies by design; see research/README.md). No "
            "Docker CPU/memory limits apply to this run."
        ),
        "cpu_model": _sysctl("machdep.cpu.brand_string") or platform.processor(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "total_ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "loadavg_at_collection": os.getloadavg(),
        "library_versions": {
            name: pkg_version(name)
            for name in [
                "pandas", "numpy", "statsmodels", "prophet", "scipy",
                "scikit-learn", "psutil", "sqlalchemy", "psycopg2-binary", "cmdstanpy",
            ]
        },
    }
    with open(OUT_PATH, "w") as f:
        json.dump(info, f, indent=2, default=str)
    print(f"Wrote {OUT_PATH}")
    print(json.dumps(info, indent=2, default=str))


if __name__ == "__main__":
    main()
