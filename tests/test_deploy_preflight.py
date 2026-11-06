"""Exercise deploy ordering in a temporary checkout with fake git/docker/preflight.

No real checkout, Docker daemon, env file, network or deployment is touched.
"""
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _bash():
    git = shutil.which("git")
    candidates = []
    if git:
        candidates.append(Path(git).resolve().parent.parent / "bin" / "bash.exe")
    if shutil.which("bash"):
        candidates.append(Path(shutil.which("bash")))
    return next((str(path) for path in candidates if path.is_file()), None)


@pytest.mark.parametrize("fail_stage", ["1", "2", "none"])
def test_deploy_checks_both_old_and_updated_code_before_build(tmp_path, fail_stage):
    bash = _bash()
    if not bash:
        pytest.skip("bash is unavailable")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(ROOT / "scripts" / "deploy.sh", scripts / "deploy.sh")
    (scripts / "preflight.sh").write_text(
        'stage=1\n[ -f pulled ] && stage=2\n'
        'echo "preflight:$stage" >> calls\n'
        '[ "$FAIL_STAGE" != "$stage" ]\n', encoding="utf-8",
    )
    # Shell functions take precedence over executables, including Git for Windows
    # injecting its own git.exe directory ahead of PATH. No real git/docker runs.
    (tmp_path / "mock_commands.sh").write_text(
        'git() { echo "git:$*" >> calls; : > pulled; }\n'
        'docker() { echo "docker:$*" >> calls; }\n', encoding="utf-8",
    )
    env = os.environ.copy()
    env["BASH_ENV"] = "mock_commands.sh"
    env["FAIL_STAGE"] = fail_stage
    result = subprocess.run(
        [bash, "--noprofile", "--norc", "scripts/deploy.sh"], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=30,
    )
    calls = (tmp_path / "calls").read_text(encoding="utf-8").splitlines()
    if fail_stage == "1":
        assert result.returncode != 0
        assert calls == ["preflight:1"]
    elif fail_stage == "2":
        assert result.returncode != 0
        assert calls == ["preflight:1", "git:pull --ff-only", "preflight:2"]
    else:
        assert result.returncode == 0, result.stderr
        assert calls == [
            "preflight:1", "git:pull --ff-only", "preflight:2",
            "docker:compose build --no-cache", "docker:compose up -d",
        ]


def test_deployment_preflight_enables_production_guard():
    wrapper = (ROOT / "scripts" / "preflight.sh").read_text(encoding="utf-8")
    assert "scripts/preflight_check.py --production" in wrapper
