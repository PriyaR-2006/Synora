from pathlib import Path
from tools.scanner import scan_directory


def build_storage_context(directory: str) -> dict:
    """
    Analyze a directory and build a storage context
    for the Synora planning system.
    """

    root = Path(directory)

    files = scan_directory(directory)

    total_files = len(files)
    total_size_bytes = sum(
        file["size_bytes"]
        for file in files
    )

    largest_files = sorted(
        files,
        key=lambda file: file["size_bytes"],
        reverse=True,
    )[:10]

    extensions: dict[str, int] = {}

    for file in files:
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
        "files": files,
    }