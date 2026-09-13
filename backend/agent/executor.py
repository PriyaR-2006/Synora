from pathlib import Path
import gzip

from agent.state import MissionState
from engines.risk import assess_file_risk
from tools.compression import compress_file
from tools.quarantine import quarantine_file


def execute_compression(
    state: MissionState,
    action: dict,
    output_directory: str,
) -> MissionState:
    """
    Execute one compression action safely.

    HIGH-risk files are blocked.
    LOW and MEDIUM-risk files may proceed.
    The compressed copy is verified before the
    original is moved into the Synora quarantine
    directory.
    """

    file_path = Path(action["path"])

    try:
        if not file_path.exists():
            raise FileNotFoundError(
                f"File does not exist: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Not a file: {file_path}"
            )

        # -------------------------------------------------
        # SAFETY GATE
        # -------------------------------------------------

        file_info = {
            "path": str(file_path),
            "name": file_path.name,
            "size_bytes": file_path.stat().st_size,
        }

        risk_level = assess_file_risk(file_info)

        if risk_level == "HIGH":
            state.protected_paths.append(
                str(file_path)
            )

            state.record_failure(
                {
                    "action_type": "COMPRESS",
                    "path": str(file_path),
                    "risk_level": risk_level,
                    "status": "BLOCKED",
                    "error": (
                        "HIGH-risk file is protected "
                        "from automatic modification."
                    ),
                }
            )

            return state

        original_size = file_path.stat().st_size

        # -------------------------------------------------
        # COMPRESS
        # -------------------------------------------------

        compressed_path = compress_file(
            str(file_path),
            output_directory,
        )

        compressed = Path(compressed_path)

        if not compressed.exists():
            raise RuntimeError(
                "Compressed file was not created."
            )

        # -------------------------------------------------
        # VERIFY
        # -------------------------------------------------

        with gzip.open(
            compressed,
            "rb",
        ) as compressed_file:
            compressed_data = compressed_file.read()

        with file_path.open("rb") as original_file:
            original_data = original_file.read()

        if compressed_data != original_data:
            raise RuntimeError(
                "Verification failed: decompressed data "
                "does not match the original file."
            )

        compressed_size = compressed.stat().st_size

        # -------------------------------------------------
        # QUARANTINE ORIGINAL
        # -------------------------------------------------

        quarantine_directory = (
            Path(output_directory).parent
            / "quarantine"
        )

        quarantine_path = quarantine_file(
            str(file_path),
            str(quarantine_directory),
        )

        quarantine = Path(quarantine_path)

        if not quarantine.exists():
            raise RuntimeError(
                "Original file was not successfully "
                "moved to quarantine."
            )

        recovered_bytes = max(
            0,
            original_size - compressed_size,
        )

        # -------------------------------------------------
        # RECORD SUCCESS
        # -------------------------------------------------

        state.record_success(
            {
                "action_type": "COMPRESS",
                "path": str(file_path),
                "output_path": str(compressed),
                "quarantine_path": str(quarantine),
                "risk_level": risk_level,
                "storage_recovered_bytes": recovered_bytes,
                "original_size_bytes": original_size,
                "compressed_size_bytes": compressed_size,
                "status": "VERIFIED_AND_QUARANTINED",
            }
        )

        return state

    except Exception as error:
        state.record_failure(
            {
                "action_type": "COMPRESS",
                "path": str(file_path),
                "status": "FAILED",
                "error": str(error),
            }
        )

        return state