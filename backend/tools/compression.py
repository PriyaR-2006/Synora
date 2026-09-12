from pathlib import Path
import gzip
import shutil


def compress_file(
    file_path: str,
    output_directory: str,
) -> str:
    """
    Compress a file using gzip.

    Returns the path of the compressed file.
    """

    source = Path(file_path)
    output_dir = Path(output_directory)

    if not source.exists():
        raise FileNotFoundError(
            f"File does not exist: {file_path}"
        )

    if not source.is_file():
        raise ValueError(
            f"Not a file: {file_path}"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = output_dir / f"{source.name}.gz"

    with source.open("rb") as source_file:
        with gzip.open(destination, "wb") as compressed_file:
            shutil.copyfileobj(
                source_file,
                compressed_file,
            )

    return str(destination)