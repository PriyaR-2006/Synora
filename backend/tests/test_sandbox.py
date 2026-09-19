"""
Tests for security/sandbox.py.
"""

import pytest

from security.sandbox import Sandbox, SandboxViolation


def test_path_inside_root_validates(tmp_path):
    inside_file = tmp_path / "inside.txt"
    inside_file.write_text("hello")

    sandbox = Sandbox(str(tmp_path))

    resolved = sandbox.validate(str(inside_file))

    assert resolved == inside_file.resolve()


def test_path_outside_root_raises(tmp_path):
    sandbox = Sandbox(str(tmp_path))

    with pytest.raises(SandboxViolation):
        sandbox.validate("/etc/passwd")


def test_is_within_returns_bool_without_raising(tmp_path):
    inside_file = tmp_path / "inside.txt"
    inside_file.write_text("hello")

    sandbox = Sandbox(str(tmp_path))

    assert sandbox.is_within(str(inside_file)) is True
    assert sandbox.is_within("/etc/passwd") is False


def test_validate_pair_checks_both_paths(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("hi")
    destination = tmp_path / "dest.txt"

    sandbox = Sandbox(str(tmp_path))

    resolved_source, resolved_destination = sandbox.validate_pair(
        str(source), str(destination)
    )

    assert resolved_source == source.resolve()
    assert resolved_destination == destination.resolve()


def test_validate_pair_raises_if_destination_outside_root(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("hi")

    sandbox = Sandbox(str(tmp_path))

    with pytest.raises(SandboxViolation):
        sandbox.validate_pair(str(source), "/etc/passwd")


def test_nonexistent_workspace_root_raises():
    with pytest.raises(FileNotFoundError):
        Sandbox("/this/path/does/not/exist/at/all")


def test_workspace_root_must_be_a_directory(tmp_path):
    a_file = tmp_path / "not_a_directory.txt"
    a_file.write_text("hi")

    with pytest.raises(NotADirectoryError):
        Sandbox(str(a_file))