from pathlib import Path
import gzip
import tempfile


def simulate_compression(file_info: dict) -> dict:
    """
    Estimate the result of compressing a file.

    Performs a real gzip compression in a temporary file so the
    planner can make a realistic storage-saving estimate.

    The original file is never modified.
    """

    source = Path(file_info["path"])

    if not source.exists():
        return {
            "action_type": "COMPRESS",
            "path": str(source),
            "original_size_bytes": 0,
            "estimated_size_bytes": 0,
            "estimated_recovered_bytes": 0,
            "profitable": False,
        }

    if not source.is_file():
        return {
            "action_type": "COMPRESS",
            "path": str(source),
            "original_size_bytes": 0,
            "estimated_size_bytes": 0,
            "estimated_recovered_bytes": 0,
            "profitable": False,
        }

    original_size = source.stat().st_size

    if original_size <= 0:
        return {
            "action_type": "COMPRESS",
            "path": str(source),
            "original_size_bytes": original_size,
            "estimated_size_bytes": 0,
            "estimated_recovered_bytes": 0,
            "profitable": False,
        }

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".gz",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        with source.open("rb") as source_file:
            with gzip.open(
                temp_path,
                "wb",
            ) as compressed_file:

                while chunk := source_file.read(
                    1024 * 1024
                ):
                    compressed_file.write(chunk)

        estimated_size = temp_path.stat().st_size

    except Exception:
        return {
            "action_type": "COMPRESS",
            "path": str(source),
            "original_size_bytes": original_size,
            "estimated_size_bytes": 0,
            "estimated_recovered_bytes": 0,
            "profitable": False,
        }

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    recovered = max(
        0,
        original_size - estimated_size,
    )

    return {
        "action_type": "COMPRESS",
        "path": str(source),
        "original_size_bytes": original_size,
        "estimated_size_bytes": estimated_size,
        "estimated_recovered_bytes": recovered,
        "profitable": recovered > 0,
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
        "profitable": False,
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