"""
Tests for domains/router.py.
"""

import pytest

from domains import router as domain_router
from agent.state import MissionState


def test_file_domain_is_implemented():
    capabilities = domain_router.get_capabilities("FILE")
    assert capabilities["implemented"] is True
    assert "COMPRESS" in capabilities["actions"]


def test_data_domain_is_not_implemented():
    capabilities = domain_router.get_capabilities("DATA")
    assert capabilities["implemented"] is False


def test_web_domain_is_not_implemented():
    capabilities = domain_router.get_capabilities("WEB")
    assert capabilities["implemented"] is False


def test_unknown_domain_raises():
    with pytest.raises(domain_router.UnknownDomainError):
        domain_router.get_capabilities("NOT_A_REAL_DOMAIN")


def test_routing_to_unimplemented_domain_raises(tmp_path):
    state = MissionState(mission_id="m1", user_goal="test", target_storage_bytes=100)

    with pytest.raises(domain_router.DomainNotImplementedError):
        domain_router.route("DATA", state, str(tmp_path))


def test_routing_to_file_domain_runs_mission(tmp_path):
    (tmp_path / "big.txt").write_text("x" * 5000)

    state = MissionState(mission_id="m1", user_goal="test", target_storage_bytes=100)
    state.set_operation_mode("AUTONOMOUS")

    result = domain_router.route("FILE", state, str(tmp_path))

    assert result.status in {"COMPLETED", "NO_SAFE_ACTIONS", "RUNNING"}


def test_infer_domain_defaults_to_file():
    assert domain_router.infer_domain("free up disk space") == domain_router.FILE


def test_infer_domain_detects_data_keywords():
    assert domain_router.infer_domain("profile this csv dataset") == domain_router.DATA


def test_infer_domain_detects_web_keywords():
    assert domain_router.infer_domain("scrape this website for prices") == domain_router.WEB


def test_list_all_capabilities_returns_three_domains():
    capabilities = domain_router.list_all_capabilities()
    domain_names = {entry["domain"] for entry in capabilities}
    assert domain_names == {"FILE", "DATA", "WEB"}