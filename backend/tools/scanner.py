from pathlib import Path


def scan_directory(directory: str) -> list[dict]:
    """
    Scan a directory and return basic information about its files.
    """

    root = Path(directory)

    if not root.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    files = []

    for path in root.rglob("*"):
        if path.is_file():
            files.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                }
            )

    return files