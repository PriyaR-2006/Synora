from agent.state import (
    MissionState,
    SAFE_MODE,
    ASK_BEFORE_ACTION_MODE,
    AUTONOMOUS_MODE,
)

from agent.executor import execute_compression
from agent.controller import run_mission

from engines.risk import assess_file_risk
from engines.simulation import simulate_compression

from tools.duplicates import find_duplicates

from storage.database import (
    save_mission,
    load_mission,
    clear_mission,
)


def test_safe_mode_requires_approval(tmp_path):
    """
    SAFE mode must not execute a compression action
    without explicit approval.
    """

    test_file = tmp_path / "safe_test.txt"

    test_file.write_text(
        "This is test data for Synora compression."
        * 20
    )

    state = MissionState(
        "test-safe",
        "Test safe mode",
        1,
    )

    state.set_operation_mode(
        SAFE_MODE
    )

    state = execute_compression(
        state,
        {
            "path": str(test_file),
        },
        str(tmp_path / "compressed"),
    )

    assert len(state.completed_actions) == 0
    assert len(state.failed_actions) == 1

    assert (
        state.failed_actions[0]["status"]
        == "APPROVAL_REQUIRED"
    )


def test_safe_mode_waits_for_approval(tmp_path):
    """
    An approval-required action should pause the mission
    instead of triggering replanning.
    """

    test_file = tmp_path / "approval_test.txt"

    test_file.write_text(
        "Synora approval workflow test."
        * 50
    )

    state = MissionState(
        "approval-test",
        "Free storage",
        100,
    )

    state.set_operation_mode(
        SAFE_MODE
    )

    state = execute_compression(
        state,
        {
            "path": str(test_file),
        },
        str(tmp_path / "compressed"),
    )

    assert len(state.completed_actions) == 0

    assert len(state.failed_actions) == 1

    assert (
        state.failed_actions[0]["status"]
        == "APPROVAL_REQUIRED"
    )

    assert (
        state.status
        == "WAITING_FOR_APPROVAL"
    )

    assert (
        state.replanning_count
        == 0
    )

    assert len(state.rejected_actions) == 0

    # The original file must remain untouched.
    assert test_file.exists()


def test_autonomous_mode_executes_low_risk_file(tmp_path):
    """
    AUTONOMOUS mode should execute a LOW-risk
    compression action automatically.
    """

    test_file = tmp_path / "autonomous_test.txt"

    test_file.write_text(
        "This is highly compressible test data."
        * 50
    )

    state = MissionState(
        "test-autonomous",
        "Test autonomous mode",
        1,
    )

    state.set_operation_mode(
        AUTONOMOUS_MODE
    )

    state = execute_compression(
        state,
        {
            "path": str(test_file),
        },
        str(tmp_path / "compressed"),
    )

    assert len(state.completed_actions) == 1
    assert len(state.failed_actions) == 0

    action = state.completed_actions[0]

    assert (
        action["operation_mode"]
        == AUTONOMOUS_MODE
    )

    assert (
        action["status"]
        == "VERIFIED_AND_QUARANTINED"
    )

    assert (
        action["storage_recovered_bytes"]
        > 0
    )


def test_high_risk_file_is_blocked(tmp_path):
    """
    HIGH-risk files must always be blocked.
    """

    test_file = tmp_path / "dangerous.exe"

    test_file.write_bytes(
        b"fake executable data"
    )

    file_info = {
        "path": str(test_file),
        "name": test_file.name,
        "size_bytes": test_file.stat().st_size,
    }

    assert (
        assess_file_risk(file_info)
        == "HIGH"
    )


def test_unprofitable_compression_is_rejected(tmp_path):
    """
    Compression that would make a file larger
    must not be considered profitable.
    """

    test_file = tmp_path / "small.txt"

    test_file.write_text("tiny")

    result = simulate_compression(
        {
            "path": str(test_file),
            "size_bytes": test_file.stat().st_size,
        }
    )

    assert result["profitable"] is False

    assert (
        result["estimated_recovered_bytes"]
        == 0
    )


def test_duplicate_detection(tmp_path):
    """
    Identical files should be detected as duplicates.
    """

    file_a = tmp_path / "duplicate_a.txt"
    file_b = tmp_path / "duplicate_b.txt"

    content = (
        "Synora duplicate detection test."
    )

    file_a.write_text(content)
    file_b.write_text(content)

    files = [
        {
            "path": str(file_a),
            "name": file_a.name,
            "size_bytes": file_a.stat().st_size,
        },
        {
            "path": str(file_b),
            "name": file_b.name,
            "size_bytes": file_b.stat().st_size,
        },
    ]

    duplicates = find_duplicates(
        files
    )

    assert len(duplicates) == 1
    assert len(duplicates[0]) == 2


def test_operation_mode_validation():
    """
    Synora should reject unsupported operation modes.
    """

    state = MissionState(
        "test-mode",
        "Test modes",
        1,
    )

    state.set_operation_mode(
        ASK_BEFORE_ACTION_MODE
    )

    assert (
        state.operation_mode
        == ASK_BEFORE_ACTION_MODE
    )

    try:
        state.set_operation_mode(
            "INVALID_MODE"
        )

        assert False, (
            "Invalid operation mode "
            "was accepted."
        )

    except ValueError:
        pass


def test_mission_completes_storage_goal(tmp_path):
    """
    Synora should keep acting until the storage goal
    is reached or no safe action remains.
    """

    test_file = tmp_path / "goal_test.txt"

    test_file.write_text(
        "Highly compressible Synora test data. "
        * 500
    )

    state = MissionState(
        "goal-test",
        "Free storage",
        1,
    )

    state.set_operation_mode(
        AUTONOMOUS_MODE
    )

    state = run_mission(
        state,
        str(tmp_path),
        max_cycles=5,
    )

    assert state.recovered_bytes >= 1

    assert (
        len(state.completed_actions)
        >= 1
    )


def test_failed_action_triggers_replanning(tmp_path):
    """
    A missing file should fail safely and trigger
    the agent's replanning state.
    """

    missing_file = (
        tmp_path
        / "does_not_exist.txt"
    )

    state = MissionState(
        "replan-test",
        "Free storage",
        100,
    )

    state.set_operation_mode(
        AUTONOMOUS_MODE
    )

    state = execute_compression(
        state,
        {
            "path": str(missing_file),
        },
        str(tmp_path / "compressed"),
    )

    assert (
        len(state.failed_actions)
        == 1
    )

    assert (
        state.status
        == "REPLANNING"
    )

    assert (
        state.replanning_count
        == 1
    )


def test_mission_state_persists(tmp_path):
    """
    Mission state should be saved and loaded correctly.
    """

    clear_mission()

    state = MissionState(
        "persistence-test",
        "Free storage",
        500,
    )

    state.recovered_bytes = 250
    state.status = "RUNNING"

    save_mission(
        {
            "mission_id": state.mission_id,
            "user_goal": state.user_goal,
            "target_storage_bytes": (
                state.target_storage_bytes
            ),
            "recovered_bytes": (
                state.recovered_bytes
            ),
            "status": state.status,
        }
    )

    loaded = load_mission()

    assert loaded is not None

    assert (
        loaded["mission_id"]
        == "persistence-test"
    )

    assert (
        loaded["recovered_bytes"]
        == 250
    )

    assert (
        loaded["status"]
        == "RUNNING"
    )

    clear_mission()


def test_directory_action_fails_safely(tmp_path):
    """
    Synora should safely reject a directory passed
    as a compression target.
    """

    directory = tmp_path / "not_a_file"
    directory.mkdir()

    state = MissionState(
        "directory-test",
        "Free storage",
        100,
    )

    state.set_operation_mode(
        AUTONOMOUS_MODE
    )

    state = execute_compression(
        state,
        {
            "path": str(directory),
        },
        str(tmp_path / "compressed"),
    )

    assert len(state.failed_actions) == 1

    assert (
        state.status
        == "REPLANNING"
    )

    assert (
        state.replanning_count
        == 1
    )


def test_compression_verification_failure_is_safe(
    tmp_path,
    monkeypatch,
):
    """
    Synora should safely handle corrupted compressed output
    and must not quarantine the original file.
    """

    test_file = tmp_path / "verification_test.txt"

    test_file.write_text(
        "Synora verification safety test."
        * 50
    )

    compressed_dir = tmp_path / "compressed"

    def fake_compress_file(
        source,
        output_directory,
    ):
        compressed_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        corrupted = (
            compressed_dir
            / "verification_test.txt.gz"
        )

        import gzip

        with gzip.open(
            corrupted,
            "wb",
        ) as output:
            output.write(
                b"CORRUPTED DATA"
            )

        return str(corrupted)

    monkeypatch.setattr(
        "agent.executor.compress_file",
        fake_compress_file,
    )

    state = MissionState(
        "verification-test",
        "Free storage",
        100,
    )

    state.set_operation_mode(
        AUTONOMOUS_MODE
    )

    state = execute_compression(
        state,
        {
            "path": str(test_file),
        },
        str(compressed_dir),
    )

    assert len(state.completed_actions) == 0

    assert len(state.failed_actions) == 1

    assert (
        state.failed_actions[0]["status"]
        == "FAILED"
    )

    assert (
        "Verification failed"
        in state.failed_actions[0]["error"]
    )

    # Original must remain untouched.
    assert test_file.exists()


def test_quarantine_failure_is_safe(
    tmp_path,
    monkeypatch,
):
    """
    Synora should treat quarantine failure as an unsuccessful
    action and must not report the file as completed.
    """

    test_file = tmp_path / "quarantine_test.txt"

    test_file.write_text(
        "Synora quarantine safety test."
        * 50
    )

    compressed_dir = tmp_path / "compressed"

    def fake_quarantine_file(
        source,
        quarantine_directory,
    ):
        raise RuntimeError(
            "Simulated quarantine failure"
        )

    monkeypatch.setattr(
        "agent.executor.quarantine_file",
        fake_quarantine_file,
    )

    state = MissionState(
        "quarantine-test",
        "Free storage",
        100,
    )

    state.set_operation_mode(
        AUTONOMOUS_MODE
    )

    state = execute_compression(
        state,
        {
            "path": str(test_file),
        },
        str(compressed_dir),
    )

    assert len(state.completed_actions) == 0

    assert len(state.failed_actions) == 1

    assert (
        state.failed_actions[0]["status"]
        == "FAILED"
    )

    assert (
        "Simulated quarantine failure"
        in state.failed_actions[0]["error"]
    )

    # Original must still exist.
    assert test_file.exists()


def test_planner_avoids_failed_file(tmp_path):
    """
    The planner should not select a file that previously
    failed compression.
    """

    failed_file = tmp_path / "failed.txt"
    good_file = tmp_path / "good.txt"

    failed_file.write_text(
        "Failed Synora file."
        * 100
    )

    good_file.write_text(
        "Good Synora compression candidate."
        * 100
    )

    state = MissionState(
        "planner-recovery-test",
        "Free storage",
        100,
    )

    state.set_operation_mode(
        AUTONOMOUS_MODE
    )

    state.record_failure(
        {
            "action_type": "COMPRESS",
            "path": str(failed_file),
            "status": "FAILED",
            "error": "Simulated failure",
        }
    )

    from agent.planner import create_plan

    state = create_plan(
        state,
        str(tmp_path),
    )

    planned_paths = {
        action.get("path")
        for action in state.planned_actions
        if action.get("action_type") == "COMPRESS"
    }

    assert str(failed_file) not in planned_paths

def test_controller_pauses_when_approval_is_required(tmp_path):
    """
    The controller should stop the mission when an action
    requires user approval.
    """

    test_file = tmp_path / "controller_approval.txt"

    test_file.write_text(
        "Synora controller approval test."
        * 100
    )

    state = MissionState(
        "controller-approval-test",
        "Free storage",
        100,
    )

    state.set_operation_mode(
        SAFE_MODE
    )

    final_state = run_mission(
        state,
        str(tmp_path),
        max_cycles=5,
    )

    assert (
        final_state.status
        == "WAITING_FOR_APPROVAL"
    )

    assert (
        final_state.replanning_count
        == 0
    )

    assert len(
        final_state.completed_actions
    ) == 0

    assert len(
        final_state.failed_actions
    ) >= 1

    assert (
        final_state.failed_actions[-1]["status"]
        == "APPROVAL_REQUIRED"
    )

    # The original file must remain untouched.
    assert test_file.exists()