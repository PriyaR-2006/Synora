from typing import Any, Optional

from agent.state import MissionState
from domains.file import domain as file_domain


FILE = "FILE"
DATA = "DATA"
WEB = "WEB"

SUPPORTED_DOMAINS = {FILE, DATA, WEB}


class UnknownDomainError(ValueError):
    pass


class DomainNotImplementedError(NotImplementedError):
    pass


def _not_implemented_capabilities(domain_name: str) -> dict[str, Any]:
    return {
        "domain": domain_name,
        "implemented": False,
        "tools": [],
        "actions": [],
        "description": (
            f"The {domain_name} domain is part of Synora's target "
            f"architecture but has not been implemented yet. No "
            f"functionality is available for this domain."
        ),
    }


def get_capabilities(domain_name: str) -> dict[str, Any]:
    """
    Return a capability description for any supported domain name,
    whether or not it is implemented yet.
    """

    if domain_name not in SUPPORTED_DOMAINS:
        raise UnknownDomainError(
            f"Unknown domain: {domain_name}. "
            f"Supported domains: {sorted(SUPPORTED_DOMAINS)}"
        )

    if domain_name == FILE:
        return file_domain.capabilities()

    return _not_implemented_capabilities(domain_name)


def list_all_capabilities() -> list[dict[str, Any]]:
    return [get_capabilities(domain_name) for domain_name in sorted(SUPPORTED_DOMAINS)]


def route(
    domain_name: str,
    state: MissionState,
    directory: str,
    max_cycles: int = 10,
) -> MissionState:
    """
    Route a mission to the given domain and run it there.

    Raises DomainNotImplementedError (not a silent no-op) for DATA/WEB,
    so callers get an explicit, catchable signal rather than a mission
    that quietly does nothing.
    """

    if domain_name not in SUPPORTED_DOMAINS:
        raise UnknownDomainError(
            f"Unknown domain: {domain_name}. "
            f"Supported domains: {sorted(SUPPORTED_DOMAINS)}"
        )

    if domain_name == FILE:
        return file_domain.run(state, directory, max_cycles=max_cycles)

    raise DomainNotImplementedError(
        f"The {domain_name} domain has not been implemented yet. "
        f"Only the FILE domain is currently runnable."
    )


def infer_domain(goal_text: str, constraints: Optional[dict[str, Any]] = None) -> str:
    """
    Very small heuristic goal->domain classifier. Since only FILE is
    implemented, this currently always returns FILE, but is written as
    a real dispatch point (not hardcoded to return a literal) so
    DATA/WEB keyword rules can be added here later without changing any
    call site.
    """

    lowered = goal_text.lower()

    data_keywords = ("csv", "dataset", "spreadsheet", "rows", "columns", "dataframe")
    web_keywords = ("website", "web page", "url", "scrape", "search the web")

    if any(keyword in lowered for keyword in data_keywords):
        return DATA

    if any(keyword in lowered for keyword in web_keywords):
        return WEB

    return FILE