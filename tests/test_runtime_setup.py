from pathlib import Path
import sys
import json
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import runtime_setup as setup

WANTED={"numpy":"2.5.4"}


def test_colab_install_stops_before_importing_any_updated_package(monkeypatch,tmp_path):
    calls=[]
    monkeypatch.setattr(setup,"distribution_versions",lambda required:{"numpy":"older"})
    monkeypatch.setattr(setup,"install_packages",lambda specs:calls.append(specs))
    monkeypatch.setattr(setup,"probe_fresh_interpreter",lambda required:required)
    monkeypatch.setattr(setup,"import_versions",lambda required:pytest.fail("Imported without restart"))
    with pytest.raises(RuntimeError,match="ONE SESSION RESTART"):
        setup.ensure_runtime(WANTED,tmp_path,in_colab=True)
    assert calls==[["numpy==2.5.4"]]
    assert json.loads((tmp_path/setup.MARKER).read_text())["pid"]==setup.os.getpid()


def test_rerunning_without_restart_cannot_bypass_the_guard(monkeypatch,tmp_path):
    (tmp_path/setup.MARKER).write_text(json.dumps({"pid":setup.os.getpid()}))
    monkeypatch.setattr(setup,"install_packages",lambda specs:pytest.fail("Unnecessary reinstall"))
    with pytest.raises(RuntimeError,match="ONE SESSION RESTART"):
        setup.ensure_runtime(WANTED,tmp_path,in_colab=True)


def test_new_session_continues_without_reinstalling(monkeypatch,tmp_path):
    (tmp_path/setup.MARKER).write_text(json.dumps({"pid":-1}))
    monkeypatch.setattr(setup,"distribution_versions",lambda required:required)
    monkeypatch.setattr(setup,"import_versions",lambda required:required)
    monkeypatch.setattr(setup,"install_packages",lambda specs:pytest.fail("Packages reinstalled after restart"))
    assert setup.ensure_runtime(WANTED,tmp_path,in_colab=True)==WANTED
    assert not (tmp_path/setup.MARKER).exists()


def test_stale_loaded_version_requires_restart_even_without_install(monkeypatch,tmp_path):
    monkeypatch.setattr(setup,"distribution_versions",lambda required:required)
    monkeypatch.setattr(setup,"import_versions",lambda required:{"numpy":"older"})
    monkeypatch.setattr(setup,"probe_fresh_interpreter",lambda required:required)
    with pytest.raises(RuntimeError,match="ONE SESSION RESTART"):
        setup.ensure_runtime(WANTED,tmp_path,in_colab=True)


def test_current_import_failure_with_healthy_disk_requires_restart(monkeypatch,tmp_path):
    monkeypatch.setattr(setup,"distribution_versions",lambda required:required)
    def broken(required):
        raise ImportError("cannot import name '_slice'")
    monkeypatch.setattr(setup,"import_versions",broken)
    monkeypatch.setattr(setup,"probe_fresh_interpreter",lambda required:required)
    with pytest.raises(RuntimeError,match="ONE SESSION RESTART"):
        setup.ensure_runtime(WANTED,tmp_path,in_colab=True)


def test_fresh_interpreter_does_not_treat_broken_install_as_success():
    with pytest.raises(RuntimeError,match="fresh Python process"):
        setup.probe_fresh_interpreter({"numpy":"this-version-does-not-exist"})
