from pathlib import Path


def simulate_compression(file_info: dict) -> dict:
    """
    Estimate the result of compressing a file.

    This does not modify the file.
    """

    size = file_info["size_bytes"]
    path = Path(file_info["path"])

    # Conservative estimate: gzip may reduce a file to
    # roughly 60% of its original size.
    estimated_size = int(size * 0.6)

    recovered = max(
        0,
        size - estimated_size,
    )

    return {
        "action_type": "COMPRESS",
        "path": str(path),
        "original_size_bytes": size,
        "estimated_size_bytes": estimated_size,
        "estimated_recovered_bytes": recovered,
    }


def simulate_quarantine(file_info: dict) -> dict:
    """
    Simulate moving a file to quarantine.

    Quarantine itself does not recover storage,
    so the estimated recovered space is zero.
    """

    return {
        "action_type": "QUARANTINE",
        "path": file_info["path"],
        "original_size_bytes": file_info["size_bytes"],
        "estimated_recovered_bytes": 0,
    }


def simulate_files(files: list[dict]) -> list[dict]:
    """
    Simulate compression for a collection of files.
    """

    simulations = []

    for file_info in files:
        simulations.append(
            simulate_compression(file_info)
        )

    return simulations