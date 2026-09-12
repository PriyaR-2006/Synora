from pathlib import Path
from hashlib import sha256


def calculate_hash(file_path: str) -> str:
    """
    Calculate the SHA-256 hash of a file.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File does not exist: {file_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Not a file: {file_path}"
        )

    hasher = sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            hasher.update(chunk)

    return hasher.hexdigest()


def verify_file(file_path: str, expected_hash: str) -> bool:
    """
    Verify that a file matches an expected SHA-256 hash.
    """

    actual_hash = calculate_hash(file_path)

    return actual_hash == expected_hash