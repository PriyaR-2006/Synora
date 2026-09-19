"""
Tests for tools/registry.py.
"""

import pytest

from tools.registry import default_registry, invoke, list_tools, ToolNotFoundError
from security.sandbox import Sandbox, SandboxViolation


def test_all_expected_tools_are_registered():
    names = {tool["name"] for tool in list_tools()}

    assert names == {
        "scan_directory",
        "find_duplicates",
        "compress_file",
        "quarantine_file",
        "restore_file",
        "calculate_hash",
        "verify_file",
    }


def test_invoke_unknown_tool_raises():
    with pytest.raises(ToolNotFoundError):
        invoke("does_not_exist")


def test_invoke_scan_directory(tmp_path):
    (tmp_path / "a.txt").write_text("hello")

    result = invoke("scan_directory", directory=str(tmp_path))

    assert len(result) == 1
    assert result[0]["name"] == "a.txt"


def test_invoke_respects_sandbox(tmp_path):
    sandbox = Sandbox(str(tmp_path))

    with pytest.raises(SandboxViolation):
        invoke("scan_directory", sandbox=sandbox, directory="/etc")


def test_invoke_calculate_hash_and_verify(tmp_path):
    file_path = tmp_path / "data.txt"
    file_path.write_text("content")

    file_hash = invoke("calculate_hash", file_path=str(file_path))

    assert invoke("verify_file", file_path=str(file_path), expected_hash=file_hash) is True
    assert invoke("verify_file", file_path=str(file_path), expected_hash="wrong") is False


def test_tool_spec_has_required_metadata():
    tool = default_registry.get("compress_file")

    assert tool.spec.name == "compress_file"
    assert tool.spec.risk_level
    assert tool.spec.description
    assert isinstance(tool.spec.permissions, list)