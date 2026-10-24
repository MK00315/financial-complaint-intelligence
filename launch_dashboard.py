"""Open the local dashboard, reusing a compatible environment when available."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8765"
PROJECT = "Financial Complaint Intelligence"
HIDDEN = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
REQUIRED = dict(line.strip().split("==") for line in (ROOT / "requirements.txt").read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#"))


def probe(executable):
    code = "import sys,json,importlib.metadata as m;print(json.dumps({'python':list(sys.version_info[:2]),'packages':{p:m.version(p) for p in " + repr(list(REQUIRED)) + "}}))"
    try:
        result = subprocess.run([str(executable), "-c", code], cwd=ROOT, capture_output=True, text=True,
                                timeout=30, creationflags=HIDDEN)
        value = json.loads(result.stdout) if result.returncode == 0 else {}
        return tuple(value.get("python", [])) in ((3, 12), (3, 13)) and value.get("packages") == REQUIRED
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def runtime(install):
    relative_python = Path("Scripts/python.exe") if sys.platform == "win32" else Path("bin/python")
    candidates = [ROOT / ".dashboard-env" / relative_python, ROOT / ".venv" / relative_python,
                  Path(sys.executable), ROOT.parents[1] / "work/financial-complaint-intelligence/.venv" / relative_python]
    for candidate in dict.fromkeys(candidates):
        if candidate.is_file() and probe(candidate):
            return candidate
    if not install:
        raise RuntimeError("A matching Python environment is not ready. Run Start_Dashboard.cmd to set it up.")
    base = Path(sys.executable) if sys.version_info[:2] in ((3, 12), (3, 13)) else None
    if not base and shutil.which("py"):
        for version in ("-3.13", "-3.12"):
            result = subprocess.run(["py", version, "-c", "import sys;print(sys.executable)"], capture_output=True,
                                    text=True, creationflags=HIDDEN)
            if result.returncode == 0:
                base = Path(result.stdout.strip()); break
    if not base:
        raise RuntimeError("Python 3.12 or 3.13 is required. Install one of these versions, then run Start_Dashboard.cmd again.")
    environment = ROOT / ".dashboard-env"
    executable = environment / relative_python
    print("First-time setup: preparing the dashboard environment. Internet access is needed only for this setup.", flush=True)
    if not executable.exists():
        subprocess.run([str(base), "-m", "venv", str(environment)], check=True, cwd=ROOT)
    subprocess.run([str(executable), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True, cwd=ROOT)
    if not probe(executable):
        raise RuntimeError("The dashboard environment does not match the saved model requirements.")
    return executable


def health():
    try:
        with urllib.request.urlopen(URL + "/api/health", timeout=1) as response:
            value = json.load(response)
        if value.get("project") != PROJECT:
            raise RuntimeError("Port 8765 is already used by another application. Close that application before launching this dashboard.")
        return value
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify runtime and artifacts without opening a browser or server")
    args = parser.parse_args()
    executable = runtime(install=not args.check)
    if args.check:
        code = ("from api import load_artifacts,ROOT;from dashboard_data import load_dashboard_data;"
                "a=load_artifacts();d=load_dashboard_data(ROOT,a['data']['source']);"
                "print('READY: verified '+a['profile']+' model; '+str(sum(r['complaints'] for r in d['rows']))+' reporting records; local dashboard assets present.')")
        subprocess.run([str(executable), "-c", code], cwd=ROOT, check=True)
        return
    if health():
        print("The dashboard is already running. Opening it in your browser.")
        webbrowser.open(URL)
        return
    print("Starting Financial Complaint Intelligence...", flush=True)
    server = subprocess.Popen([str(executable), str(ROOT / "api.py")], cwd=ROOT)
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError("The dashboard could not start. See the message above for details.")
            if health():
                break
            time.sleep(.2)
        else:
            raise RuntimeError("The dashboard took too long to start. Check the messages above and try again.")
        print("\nDashboard ready: " + URL + "\nKeep this window open while using it. Press Ctrl+C here to stop.\n", flush=True)
        webbrowser.open(URL)
        server.wait()
    except KeyboardInterrupt:
        print("\nStopping the dashboard.")
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print("\n" + str(exc), file=sys.stderr)
        sys.exit(1)
