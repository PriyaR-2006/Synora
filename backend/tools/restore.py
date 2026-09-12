from pathlib import Path
import shutil


def restore_file(
    quarantined_file: str,
    restore_directory: str,
) -> str:
    """
    Restore a quarantined file to the specified directory.

    Returns the restored file path.
    """

    source = Path(quarantined_file)
    destination_directory = Path(restore_directory)

    if not source.exists():
        raise FileNotFoundError(
            f"Quarantined file does not exist: {quarantined_file}"
        )

    if not source.is_file():
        raise ValueError(
            f"Not a file: {quarantined_file}"
        )

    destination_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = destination_directory / source.name

    counter = 1

    while destination.exists():
        destination = (
            destination_directory
            / f"{source.stem}_{counter}{source.suffix}"
        )
        counter += 1

    shutil.move(
        str(source),
        str(destination),
    )

    return str(destination)