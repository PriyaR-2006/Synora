"""
Tests for verification/verifier.py.
"""

import gzip
from pathlib import Path

from models.schemes import VERIFICATION_PASSED, VERIFICATION_FAILED
from verification.verifier import verify_compression_action, verify_storage_goal
from agent.state import MissionState


def _make_valid_action(tmp_path: Path) -> dict:
    original_content = b"hello synora"

    quarantine_path = tmp_path / "quarantine" / "original.txt"
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_path.write_bytes(original_content)

    output_path = tmp_path / "compressed" / "original.txt.gz"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_path, "wb") as gz_file:
        gz_file.write(original_content)

    return {
        "path": str(tmp_path / "original.txt"),  # no longer exists here
        "output_path": str(output_path),
        "quarantine_path": str(quarantine_path),
        "action_id": "test-action",
        "storage_recovered_bytes": 5,
        "status": "VERIFIED_AND_QUARANTINED",
    }


def test_valid_compression_action_passes(tmp_path):
    action = _make_valid_action(tmp_path)

    result = verify_compression_action(action)

    assert result.result == VERIFICATION_PASSED
    assert result.passed is True


def test_missing_output_file_fails(tmp_path):
    action = _make_valid_action(tmp_path)
    Path(action["output_path"]).unlink()

    result = verify_compression_action(action)

    assert result.result == VERIFICATION_FAILED


def test_missing_required_fields_fails():
    result = verify_compression_action({"path": "/tmp/x.txt"})

    assert result.result == VERIFICATION_FAILED


def test_content_mismatch_fails(tmp_path):
    action = _make_valid_action(tmp_path)

    # Corrupt the quarantined original so hashes no longer match.
    Path(action["quarantine_path"]).write_bytes(b"tampered content")

    result = verify_compression_action(action)

    assert result.result == VERIFICATION_FAILED


def test_verify_storage_goal_passed_when_target_reached():
    state = MissionState(
        mission_id="m1",
        user_goal="test",
        target_storage_bytes=100,
    )

    state.completed_actions = [
        {"status": "VERIFIED_AND_QUARANTINED", "storage_recovered_bytes": 150}
    ]
    state.recovered_bytes = 150

    result = verify_storage_goal(state)

    assert result.result == VERIFICATION_PASSED


def test_verify_storage_goal_fails_when_target_not_reached():
    state = MissionState(
        mission_id="m1",
        user_goal="test",
        target_storage_bytes=1000,
    )

    state.completed_actions = [
        {"status": "VERIFIED_AND_QUARANTINED", "storage_recovered_bytes": 50}
    ]
    state.recovered_bytes = 50

    result = verify_storage_goal(state)

    assert result.result == VERIFICATION_FAILED