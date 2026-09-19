"""
Tests for agent/replanner.py.
"""

from agent.replanner import propose_alternative, _versioned_path


class _RecorderState:
    def __init__(self):
        self.replans = []

    def record_replan(self, event):
        self.replans.append(event)


def test_versioned_path_finds_first_free_name(tmp_path):
    existing = tmp_path / "report.pdf"
    existing.write_text("x")

    versioned = _versioned_path(existing)

    assert versioned.name == "report_v2.pdf"


def test_versioned_path_skips_existing_versions(tmp_path):
    (tmp_path / "report.pdf").write_text("x")
    (tmp_path / "report_v2.pdf").write_text("x")

    versioned = _versioned_path(tmp_path / "report.pdf")

    assert versioned.name == "report_v3.pdf"


def test_propose_alternative_for_existing_destination(tmp_path):
    conflicting = tmp_path / "report.pdf.gz"
    conflicting.write_text("existing")

    failed_action = {
        "action_type": "COMPRESS",
        "path": str(tmp_path / "report.pdf"),
        "status": "FAILED",
        "error": f"Compressed file already exists: {conflicting}",
        "risk_level": "LOW",
    }

    state = _RecorderState()

    alternative = propose_alternative(state, failed_action, str(tmp_path))

    assert alternative is not None
    assert alternative["action_type"] == "COMPRESS"
    assert "v2" in alternative["expected_outcome"]


def test_propose_alternative_returns_none_for_non_failed_status():
    state = _RecorderState()

    action = {"status": "BLOCKED", "error": "HIGH-risk file is protected"}

    assert propose_alternative(state, action, "/tmp") is None


def test_propose_alternative_returns_none_for_missing_file():
    state = _RecorderState()

    action = {
        "action_type": "COMPRESS",
        "path": "/tmp/gone.txt",
        "status": "FAILED",
        "error": "File does not exist: /tmp/gone.txt",
    }

    assert propose_alternative(state, action, "/tmp") is None


def test_propose_alternative_returns_none_when_no_handler_matches():
    state = _RecorderState()

    action = {
        "action_type": "COMPRESS",
        "path": "/tmp/x.txt",
        "status": "FAILED",
        "error": "Some unrelated error message",
    }

    assert propose_alternative(state, action, "/tmp") is None