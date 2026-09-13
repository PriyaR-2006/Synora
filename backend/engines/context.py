from pathlib import Path

from tools.scanner import scan_directory


IGNORED_DIRECTORIES = {
    "compressed",
    "quarantine",
    "restored",
}


def build_storage_context(directory: str) -> dict:
    """
    Analyze a directory and build a storage context
    for the Synora planning system.

    Generated storage-management directories are
    excluded from agent planning so Synora does not
    attempt to process files that it created or
    restored itself.
    """

    root = Path(directory)

    files = scan_directory(directory)

    filtered_files = []

    for file_info in files:
        file_path = Path(file_info["path"])

        try:
            relative_path = file_path.relative_to(root)
        except ValueError:
            continue

        if any(
            part.lower() in IGNORED_DIRECTORIES
            for part in relative_path.parts
        ):
            continue

        filtered_files.append(file_info)

    total_files = len(filtered_files)

    total_size_bytes = sum(
        file["size_bytes"]
        for file in filtered_files
    )

    largest_files = sorted(
        filtered_files,
        key=lambda file: file["size_bytes"],
        reverse=True,
    )[:10]

    extensions: dict[str, int] = {}

    for file in filtered_files:
        suffix = Path(file["name"]).suffix.lower()

        if not suffix:
            suffix = "[no extension]"

        extensions[suffix] = (
            extensions.get(suffix, 0) + 1
        )

    return {
        "directory": str(root.resolve()),
        "total_files": total_files,
        "total_size_bytes": total_size_bytes,
        "extensions": extensions,
        "largest_files": largest_files,
        "files": filtered_files,
    }
