import gzip
from pathlib import Path

from agent.state import MissionState
from policy.engine import evaluate_file_action
from tools.compression import compress_file
from tools.quarantine import quarantine_file
from tools.verification import calculate_hash


def _hash_of_gzip_contents(gzip_path: Path) -> str:
    """
    Compute the SHA-256 hash of the *decompressed* contents of a gzip
    file, so it can be compared against the original file's hash
    without ever holding either file's full contents in memory at once.
    """

    from hashlib import sha256

    hasher = sha256()

    with gzip.open(gzip_path, "rb") as compressed_file:
        while chunk := compressed_file.read(1024 * 1024):
            hasher.update(chunk)

    return hasher.hexdigest()


def execute_compression(
    state: MissionState,
    action: dict,
    output_directory: str,
    approved: bool = False,
) -> MissionState:
    """
    Execute one compression action safely.

    Approval-aware execution (decision now made by policy.engine):

    SAFE:
        Requires approval unless action contains approved=True.

    ASK_BEFORE_ACTION:
        Medium risk requires approval.

    AUTONOMOUS:
        Executes low and medium risk automatically.

    HIGH risk:
        Always blocked.
    """

    file_path = Path(action["path"])

    try:

        # ---------------------------------------------
        # VALIDATE FILE
        # ---------------------------------------------

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


        # ---------------------------------------------
        # POLICY DECISION (risk + approval, combined)
        # ---------------------------------------------

        decision = evaluate_file_action(
            action_type="COMPRESS",
            file_info=file_info,
            operation_mode=state.operation_mode,
            approved=approved,
        )

        if decision.denied:

            state.protected_paths.append(
                str(file_path)
            )

            state.record_failure(
                {
                    "action_type": "COMPRESS",
                    "path": str(file_path),
                    "risk_level": decision.risk_level,
                    "operation_mode": state.operation_mode,
                    "status": "BLOCKED",
                    "error": decision.reason,
                }
            )

            return state

        if decision.requires_approval:

            state.record_failure(
                {
                    "action_type": "COMPRESS",
                    "path": str(file_path),
                    "risk_level": decision.risk_level,
                    "operation_mode": state.operation_mode,
                    "status": "APPROVAL_REQUIRED",
                    "error": decision.reason,
                }
            )

            return state


        # ---------------------------------------------
        # COMPRESS
        # ---------------------------------------------

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



        # ---------------------------------------------
        # VERIFY COMPRESSION (hash-based, streaming)
        # ---------------------------------------------

        original_hash = calculate_hash(str(file_path))
        compressed_content_hash = _hash_of_gzip_contents(compressed)

        if compressed_content_hash != original_hash:

            raise RuntimeError(
                "Verification failed: "
                "compressed data does not match original."
            )



        compressed_size = compressed.stat().st_size


        recovered_bytes = max(
            0,
            original_size - compressed_size,
        )



        # ---------------------------------------------
        # QUARANTINE ORIGINAL
        # ---------------------------------------------

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
                "Original file was not moved to quarantine."
            )



        # ---------------------------------------------
        # SUCCESS
        # ---------------------------------------------

        state.record_success(
            {
                "action_type": "COMPRESS",
                "path": str(file_path),
                "output_path": str(compressed),
                "quarantine_path": str(quarantine),

                "risk_level": decision.risk_level,

                "operation_mode":
                    state.operation_mode,

                "storage_recovered_bytes":
                    recovered_bytes,

                "original_size_bytes":
                    original_size,

                "compressed_size_bytes":
                    compressed_size,

                "status":
                    "VERIFIED_AND_QUARANTINED",
            }
        )


        return state



    except Exception as error:


        state.record_failure(
            {
                "action_type": "COMPRESS",
                "path": str(file_path),

                "operation_mode":
                    state.operation_mode,

                "status": "FAILED",

                "error": str(error),
            }
        )


        return state