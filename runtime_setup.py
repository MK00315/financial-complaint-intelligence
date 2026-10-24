"""Install the notebook environment without using stale in-memory binary modules."""
from __future__ import annotations

import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys

MODULES={"scikit-learn":"sklearn","bottleneck":"bottleneck"}
MARKER=".runtime_restart_required.json"
RESTART_MESSAGE=(
    "SETUP COMPLETE: ONE SESSION RESTART IS REQUIRED. "
    "In Colab choose Runtime > Restart session (not Disconnect and delete runtime). "
    "Then run all cells again from Settings. Installed packages and runtime files are retained. "
    "Do not rerun the failing import cell in this same session."
)


def distribution_versions(required):
    found={}
    for package in required:
        try:
            found[package]=metadata.version(package)
        except metadata.PackageNotFoundError:
            found[package]=None
    return found


def install_packages(specs):
    subprocess.check_call([sys.executable,"-m","pip","install","--quiet","--upgrade",*specs])


def import_versions(required):
    return {package:importlib.import_module(MODULES.get(package,package)).__version__ for package in required}


def probe_fresh_interpreter(required):
    # A child process tests the installed files without reusing this kernel's NumPy.
    script=("import importlib,json; required="+repr(required)+"; modules="+repr(MODULES)+"; "
            "actual={p:importlib.import_module(modules.get(p,p)).__version__ for p in required}; "
            "assert actual==required,(actual,required); "
            "import numpy as np; assert np.char.lower(np.array(['CHECK']))[0]=='check'; "
            "print(json.dumps(actual))")
    process=subprocess.run([sys.executable,"-c",script],capture_output=True,text=True,timeout=180)
    if process.returncode:
        raise RuntimeError("The installed environment also fails in a fresh Python process. Installation needs repair before training.\n"+process.stderr[-5000:])
    return json.loads(process.stdout.strip().splitlines()[-1])


def mark_restart(root,reason):
    marker=Path(root)/MARKER
    marker.parent.mkdir(parents=True,exist_ok=True)
    marker.write_text(json.dumps({"pid":os.getpid(),"reason":reason}),encoding="utf-8")
    raise RuntimeError(RESTART_MESSAGE)


def assert_no_pending_restart(root):
    marker=Path(root)/MARKER
    if marker.exists():
        pending=json.loads(marker.read_text(encoding="utf-8"))
        if pending["pid"]==os.getpid():
            raise RuntimeError(RESTART_MESSAGE)


def ensure_runtime(required,root,in_colab=False):
    root=Path(root)
    assert_no_pending_restart(root)
    installed=distribution_versions(required)
    changes=[f"{p}=={wanted}" for p,wanted in required.items() if installed[p]!=wanted]
    loaded=[p for p in required if MODULES.get(p,p) in sys.modules]
    if changes:
        install_packages(changes)
        probe_fresh_interpreter(required)
        # Colab can preload numeric packages before a notebook's first import.
        if in_colab or loaded:
            mark_restart(root,"Dependencies were installed or changed in this kernel.")
    try:
        active=import_versions(required)
    except (ImportError,AttributeError,ValueError) as exc:
        probe_fresh_interpreter(required)
        try:
            mark_restart(root,"Installed files pass a fresh-process check but current imports fail.")
        except RuntimeError as restart:
            raise restart from exc
    if active!=required:
        probe_fresh_interpreter(required)
        mark_restart(root,"Loaded package versions differ from the installed requirements.")
    (root/MARKER).unlink(missing_ok=True)
    print("Environment checks passed:",active)
    return active
