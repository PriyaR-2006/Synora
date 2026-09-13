from pathlib import Path
import gzip

from agent.state import (
    MissionState,
    SAFE_MODE,
    ASK_BEFORE_ACTION_MODE,
    AUTONOMOUS_MODE,
)
from engines.risk import assess_file_risk
from tools.compression import compress_file
from tools.quarantine import quarantine_file


def execute_compression(
    state: MissionState,
    action: dict,
    output_directory: str,
    approved: bool = False,
) -> MissionState:
    """
    Execute one compression action safely.

    Operation modes:

    SAFE:
        Every compression action requires explicit approval.

    ASK_BEFORE_ACTION:
        LOW-risk files can execute automatically.
        MEDIUM-risk files require approval.
        HIGH-risk files are always blocked.

    AUTONOMOUS:
        LOW-risk and MEDIUM-risk files can execute automatically.
        HIGH-risk files are always blocked.

    HIGH-risk files are never automatically modified
    in any operation mode.
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

        file_info = {
            "path": str(file_path),
            "name": file_path.name,
            "size_bytes": file_path.stat().st_size,
        }

        risk_level = assess_file_risk(
            file_info
        )

        if risk_level == "HIGH":
            state.protected_paths.append(
                str(file_path)
            )

            state.record_failure(
                {
                    "action_type": "COMPRESS",
                    "path": str(file_path),
                    "risk_level": risk_level,
                    "operation_mode": (
                        state.operation_mode
                    ),
                    "status": "BLOCKED",
                    "error": (
                        "HIGH-risk file is protected "
                        "from automatic modification."
                    ),
                }
            )

            return state

        approval_required = False

        if state.operation_mode == SAFE_MODE:
            approval_required = True

        elif state.operation_mode == ASK_BEFORE_ACTION_MODE:
            if risk_level == "MEDIUM":
                approval_required = True

        elif state.operation_mode == AUTONOMOUS_MODE:
            approval_required = False

        else:
            raise ValueError(
                f"Unsupported operation mode: "
                f"{state.operation_mode}"
            )

        if approval_required and not approved:
            state.record_failure(
                {
                    "action_type": "COMPRESS",
                    "path": str(file_path),
                    "risk_level": risk_level,
                    "operation_mode": (
                        state.operation_mode
                    ),
                    "status": "APPROVAL_REQUIRED",
                    "error": (
                        "This action requires explicit "
                        "user approval in the current "
                        "operation mode."
                    ),
                }
            )

            return state

        original_size = file_path.stat().st_size

        compressed_path = compress_file(
            str(file_path),
            output_directory,
        )

        compressed = Path(
            compressed_path
        )

        if not compressed.exists():
            raise RuntimeError(
                "Compressed file was not created."
            )

        with gzip.open(
            compressed,
            "rb",
        ) as compressed_file:
            compressed_data = (
                compressed_file.read()
            )

        with file_path.open("rb") as original_file:
            original_data = (
                original_file.read()
            )

        if compressed_data != original_data:
            raise RuntimeError(
                "Verification failed: decompressed data "
                "does not match the original file."
            )

        compressed_size = compressed.stat().st_size

        recovered_bytes = max(
            0,
            original_size - compressed_size,
        )

        quarantine_directory = (
            Path(output_directory).parent
            / "quarantine"
        )

        quarantine_path = quarantine_file(
            str(file_path),
            str(quarantine_directory),
        )

        quarantine = Path(
            quarantine_path
        )

        if not quarantine.exists():
            raise RuntimeError(
                "Original file was not successfully "
                "moved to quarantine."
            )

        state.record_success(
            {
                "action_type": "COMPRESS",
                "path": str(file_path),
                "output_path": str(compressed),
                "quarantine_path": str(quarantine),
                "risk_level": risk_level,
                "operation_mode": (
                    state.operation_mode
                ),
                "storage_recovered_bytes": (
                    recovered_bytes
                ),
                "original_size_bytes": (
                    original_size
                ),
                "compressed_size_bytes": (
                    compressed_size
                ),
                "status": (
                    "VERIFIED_AND_QUARANTINED"
                ),
            }
        )

        return state

    except Exception as error:
        state.record_failure(
            {
                "action_type": "COMPRESS",
                "path": str(file_path),
                "operation_mode": (
                    state.operation_mode
                ),
                "status": "FAILED",
                "error": str(error),
            }
        )

        return state