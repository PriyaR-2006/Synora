from pathlib import Path
import gzip
import shutil


def compress_file(file_path: str, output_directory: str) -> str:
    source = Path(file_path)
    output_dir = Path(output_directory)

    if not source.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    if not source.is_file():
        raise ValueError(f"Not a file: {file_path}")

    # Prevent compressing an already compressed gzip file
    if source.suffix.lower() == ".gz":
        raise ValueError("File is already compressed.")

    output_dir.mkdir(parents=True, exist_ok=True)

    destination = output_dir / f"{source.name}.gz"

    # Prevent overwriting an existing compressed file
    if destination.exists():
        raise FileExistsError(
            f"Compressed file already exists: {destination}"
        )

    with source.open("rb") as source_file:
        with gzip.open(destination, "wb") as compressed_file:
            shutil.copyfileobj(source_file, compressed_file)

    return str(destination)
