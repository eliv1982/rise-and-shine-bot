import asyncio
import os
import time
from types import SimpleNamespace

import pytest

import config as config_mod
from cleanup_outputs import cleanup_old_outputs, run_outputs_cleanup


def _touch(path, age_days=None):
    with open(path, "wb") as f:
        f.write(b"x")
    if age_days is not None:
        old_time = time.time() - age_days * 86400
        os.utime(path, (old_time, old_time))


def test_old_eligible_file_is_deleted(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    old_file = out_dir / "old.png"
    _touch(old_file, age_days=10)

    result = cleanup_old_outputs(str(out_dir), days=7)

    assert result["removed"] == 1
    assert not old_file.exists()


def test_recent_file_is_preserved(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    recent_file = out_dir / "recent.png"
    _touch(recent_file)  # mtime = now

    result = cleanup_old_outputs(str(out_dir), days=7)

    assert result["removed"] == 0
    assert recent_file.exists()


def test_non_matching_extension_is_skipped_even_if_old(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    other = out_dir / "notes.txt"
    _touch(other, age_days=100)

    result = cleanup_old_outputs(str(out_dir), days=7)

    assert result["removed"] == 0
    assert result["skipped_non_matching"] == 1
    assert other.exists()


def test_file_outside_output_root_is_never_touched(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    outside_dir = tmp_path / "elsewhere"
    outside_dir.mkdir()
    outside_file = outside_dir / "important.png"
    _touch(outside_file, age_days=100)

    result = cleanup_old_outputs(str(out_dir), days=7)

    assert result["removed"] == 0
    assert outside_file.exists()


def test_missing_output_directory_is_harmless(tmp_path):
    missing_dir = tmp_path / "does-not-exist"

    result = cleanup_old_outputs(str(missing_dir), days=7)

    assert result == {"removed": 0, "skipped_non_matching": 0, "errors": 0}


def test_zero_days_is_a_noop(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    old_file = out_dir / "old.png"
    _touch(old_file, age_days=100)

    result = cleanup_old_outputs(str(out_dir), days=0)

    assert result["removed"] == 0
    assert old_file.exists()


def test_cleanup_failure_on_one_entry_does_not_stop_the_sweep(tmp_path, monkeypatch):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    bad_file = out_dir / "locked.png"
    good_file = out_dir / "old.png"
    _touch(bad_file, age_days=10)
    _touch(good_file, age_days=10)

    real_remove = os.remove

    def _raising_remove(path):
        if os.path.basename(path) == "locked.png":
            raise OSError("simulated: permission denied")
        return real_remove(path)

    monkeypatch.setattr(os, "remove", _raising_remove)

    result = cleanup_old_outputs(str(out_dir), days=7)

    assert result["removed"] == 1
    assert result["errors"] == 1
    assert bad_file.exists()
    assert not good_file.exists()


def test_symlink_entry_never_deletes_its_target(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    protected_dir = tmp_path / "protected"
    protected_dir.mkdir()
    real_target = protected_dir / "real.png"
    _touch(real_target, age_days=100)

    link_path = out_dir / "link.png"
    try:
        os.symlink(real_target, link_path)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not permitted in this environment")

    cleanup_old_outputs(str(out_dir), days=7)

    # Only the symlink entry may be unlinked; the real file it points to must survive.
    assert real_target.exists()


def test_run_outputs_cleanup_uses_settings_dir_and_retention(tmp_path, monkeypatch):
    async def run():
        out_dir = tmp_path / "outputs"
        out_dir.mkdir()
        old_file = out_dir / "old.png"
        _touch(old_file, age_days=10)

        monkeypatch.setattr(config_mod, "get_outputs_dir", lambda: str(out_dir))
        monkeypatch.setattr(config_mod, "get_settings", lambda: SimpleNamespace(output_max_age_days=7))

        result = await run_outputs_cleanup()

        assert result["removed"] == 1
        assert not old_file.exists()

    asyncio.run(run())


def test_run_outputs_cleanup_explicit_days_overrides_settings(tmp_path, monkeypatch):
    async def run():
        out_dir = tmp_path / "outputs"
        out_dir.mkdir()
        recent_file = out_dir / "recent.png"
        _touch(recent_file, age_days=2)

        monkeypatch.setattr(config_mod, "get_outputs_dir", lambda: str(out_dir))
        monkeypatch.setattr(config_mod, "get_settings", lambda: SimpleNamespace(output_max_age_days=30))

        result = await run_outputs_cleanup(days=1)

        assert result["removed"] == 1
        assert not recent_file.exists()

    asyncio.run(run())


def test_run_outputs_cleanup_survives_unexpected_exception(monkeypatch):
    """A totally unexpected failure (e.g. get_settings raising) must not propagate - startup
    and the periodic job both depend on this never crashing the bot."""

    async def run():
        def _raise():
            raise RuntimeError("boom")

        monkeypatch.setattr(config_mod, "get_settings", _raise)

        result = await run_outputs_cleanup()
        assert result["errors"] == 1

    asyncio.run(run())


def test_setup_scheduler_registers_outputs_cleanup_job_alongside_delivery_job():
    import scheduler as scheduler_mod

    async def run():
        fake_bot = object()
        scheduler_mod.setup_scheduler(fake_bot)
        try:
            jobs = {job.id: job for job in scheduler_mod.scheduler.get_jobs()}
            assert "daily_affirmations" in jobs
            assert "outputs_cleanup" in jobs

            cleanup_job = jobs["outputs_cleanup"]
            assert cleanup_job.max_instances == 1
            # A distinct id and its own interval trigger, independent of the delivery cron job.
            assert cleanup_job.trigger.__class__.__name__ == "IntervalTrigger"
        finally:
            scheduler_mod.scheduler.shutdown(wait=False)

    asyncio.run(run())
