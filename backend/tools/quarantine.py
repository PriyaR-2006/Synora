from pathlib import Path
import shutil


def quarantine_file(
    file_path: str,
    quarantine_directory: str,
) -> str:
    """
    Move a file into the quarantine directory.

    Returns the new location of the quarantined file.
    """

    source = Path(file_path)
    quarantine = Path(quarantine_directory)

    if not source.exists():
        raise FileNotFoundError(
            f"File does not exist: {file_path}"
        )

    if not source.is_file():
        raise ValueError(
            f"Not a file: {file_path}"
        )

    quarantine.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = quarantine / source.name

    # Avoid overwriting an existing quarantined file.
    counter = 1

    while destination.exists():
        destination = (
            quarantine
            / f"{source.stem}_{counter}{source.suffix}"
        )
        counter += 1

    shutil.move(
        str(source),
        str(destination),
    )

    return str(destination)