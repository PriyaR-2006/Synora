from hashlib import sha256
from pathlib import Path


def file_hash(path: Path) -> str:
    """
    Calculate a SHA-256 hash for a file.
    """

    hasher = sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            hasher.update(chunk)

    return hasher.hexdigest()


def find_duplicates(files: list[dict]) -> list[list[dict]]:
    """
    Find files with identical contents.

    Returns groups containing duplicate files.
    """

    hashes: dict[str, list[dict]] = {}

    for file_info in files:
        path = Path(file_info["path"])

        if not path.exists() or not path.is_file():
            continue

        file_hash_value = file_hash(path)

        hashes.setdefault(file_hash_value, []).append(file_info)

    duplicates = [
        group
        for group in hashes.values()
        if len(group) > 1
    ]

    return duplicates