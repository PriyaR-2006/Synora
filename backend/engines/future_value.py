from pathlib import Path


def estimate_file_value(file_info: dict) -> float:
    """
    Estimate how valuable a file is likely to be.

    Higher scores mean the file should be preserved more carefully.
    """

    path = Path(file_info["path"])
    name = path.name.lower()
    suffix = path.suffix.lower()

    # Important personal/work files get higher value.
    high_value_extensions = {
        ".docx",
        ".xlsx",
        ".pptx",
        ".pdf",
        ".py",
        ".js",
        ".html",
        ".csv",
    }

    if suffix in high_value_extensions:
        return 0.9

    # Media and common user files have moderate value.
    medium_value_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".mp4",
        ".mp3",
        ".txt",
    }

    if suffix in medium_value_extensions:
        return 0.6

    # Temporary/cache-style files are generally less valuable.
    low_value_extensions = {
        ".tmp",
        ".bak",
        ".log",
        ".cache",
    }

    if suffix in low_value_extensions:
        return 0.2

    # Hidden/system-style files should be treated conservatively.
    if name.startswith("."):
        return 0.5

    return 0.5


def estimate_files_value(files: list[dict]) -> list[dict]:
    """
    Add a future-value score to each file.
    """

    assessed = []

    for file_info in files:
        result = dict(file_info)
        result["future_value"] = estimate_file_value(file_info)
        assessed.append(result)

    return assessed