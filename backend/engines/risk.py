from pathlib import Path


def assess_file_risk(file_info: dict) -> str:
    """
    Assess how risky it would be for Synora to act on a file.
    """

    path = Path(file_info["path"])
    name = path.name.lower()
    suffix = path.suffix.lower()

    # Never automatically modify obvious system/config files.
    protected_names = {
        "desktop.ini",
        "bootmgr",
        "ntuser.dat",
    }

    if name in protected_names:
        return "HIGH"

    # Configuration and executable files deserve extra caution.
    high_risk_extensions = {
        ".exe",
        ".dll",
        ".sys",
        ".bat",
        ".cmd",
        ".ps1",
        ".msi",
    }

    if suffix in high_risk_extensions:
        return "HIGH"

    # User documents are generally safer candidates.
    low_risk_extensions = {
        ".txt",
        ".log",
        ".tmp",
        ".bak",
        ".zip",
        ".gz",
        ".jpg",
        ".jpeg",
        ".png",
        ".mp4",
    }

    if suffix in low_risk_extensions:
        return "LOW"

    return "MEDIUM"


def assess_files(files: list[dict]) -> list[dict]:
    """
    Add a risk level to each scanned file.
    """

    assessed = []

    for file_info in files:
        result = dict(file_info)
        result["risk_level"] = assess_file_risk(file_info)
        assessed.append(result)

    return assessed