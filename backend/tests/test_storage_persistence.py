"""
Tests for storage/database.py's mission-ID-keyed persistence.
"""

import json

import storage.database as database


def test_save_and_load_multiple_missions(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "state.json")

    database.save_mission({"mission_id": "m1", "status": "CREATED"})
    database.save_mission({"mission_id": "m2", "status": "RUNNING"})

    assert database.load_mission("m1")["status"] == "CREATED"
    assert database.load_mission("m2")["status"] == "RUNNING"


def test_load_mission_with_no_argument_returns_latest(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "state.json")

    database.save_mission({"mission_id": "m1", "status": "CREATED"})
    database.save_mission({"mission_id": "m2", "status": "RUNNING"})

    latest = database.load_mission()

    assert latest["mission_id"] == "m2"


def test_list_missions_returns_all(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "state.json")

    database.save_mission({"mission_id": "m1", "status": "CREATED"})
    database.save_mission({"mission_id": "m2", "status": "RUNNING"})

    missions = database.list_missions()

    assert len(missions) == 2


def test_clear_specific_mission(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "state.json")

    database.save_mission({"mission_id": "m1", "status": "CREATED"})
    database.save_mission({"mission_id": "m2", "status": "RUNNING"})

    database.clear_mission("m1")

    assert database.load_mission("m1") is None
    assert database.load_mission("m2") is not None


def test_clear_all_missions(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "state.json")

    database.save_mission({"mission_id": "m1", "status": "CREATED"})
    database.clear_mission()

    assert database.load_mission() is None
    assert not database.DATABASE_FILE.exists()


def test_legacy_flat_format_is_migrated(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(database, "DATABASE_FILE", state_file)

    legacy_data = {"mission_id": "legacy-1", "status": "COMPLETED"}
    state_file.write_text(json.dumps(legacy_data))

    loaded = database.load_mission()

    assert loaded["mission_id"] == "legacy-1"
    assert loaded["status"] == "COMPLETED"


def test_history_events_are_recorded(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "state.json")

    database.append_history_event({"mission_id": "m1", "event_type": "mission_created"})
    database.append_history_event({"mission_id": "m2", "event_type": "mission_created"})

    all_events = database.read_history()
    m1_events = database.read_history(mission_id="m1")

    assert len(all_events) == 2
    assert len(m1_events) == 1
    assert m1_events[0]["mission_id"] == "m1"