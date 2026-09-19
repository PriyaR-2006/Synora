from pathlib import Path

from models.schemes import (
    VerificationResult,
    VERIFICATION_PASSED,
    VERIFICATION_FAILED,
    VERIFICATION_PARTIAL,
)
from tools.verification import calculate_hash


def verify_compression_action(action: dict) -> VerificationResult:
    """
    Goal-level verification for a completed COMPRESS action.

    Checks:
    1. The compressed output file actually exists on disk right now.
    2. The quarantined original actually exists on disk right now.
    3. The decompressed content of the output file still matches the
       original file's content hash (re-derived independently of
       whatever the executor itself recorded).
    4. The original path is no longer present at its old location
       (i.e. it was really moved to quarantine, not copied).
    """

    checks: list[str] = []
    evidence: dict = {}

    output_path = action.get("output_path")
    quarantine_path = action.get("quarantine_path")
    original_path = action.get("path")

    if not output_path or not quarantine_path or not original_path:
        return VerificationResult(
            result=VERIFICATION_FAILED,
            checks=["required_fields_present"],
            evidence={"action": action},
            message=(
                "Action record is missing output_path, quarantine_path "
                "or path; cannot verify."
            ),
        )

    output_exists = Path(output_path).exists()
    checks.append("compressed_output_exists")
    evidence["compressed_output_exists"] = output_exists

    quarantine_exists = Path(quarantine_path).exists()
    checks.append("quarantined_original_exists")
    evidence["quarantined_original_exists"] = quarantine_exists

    original_still_at_old_path = Path(original_path).exists()
    checks.append("original_path_cleared")
    evidence["original_still_at_old_path"] = original_still_at_old_path

    if not output_exists or not quarantine_exists:
        return VerificationResult(
            result=VERIFICATION_FAILED,
            checks=checks,
            evidence=evidence,
            message=(
                "Expected output/quarantine artifacts are missing from "
                "disk."
            ),
        )

    content_matches = None
    try:
        import gzip
        from hashlib import sha256

        hasher = sha256()
        with gzip.open(output_path, "rb") as compressed_file:
            while chunk := compressed_file.read(1024 * 1024):
                hasher.update(chunk)
        decompressed_hash = hasher.hexdigest()

        quarantined_hash = calculate_hash(quarantine_path)

        content_matches = decompressed_hash == quarantined_hash
    except Exception as error:
        checks.append("content_hash_comparable")
        evidence["content_hash_error"] = str(error)

        return VerificationResult(
            result=VERIFICATION_PARTIAL,
            checks=checks,
            evidence=evidence,
            message=(
                "Artifacts exist but content could not be independently "
                f"re-verified: {error}"
            ),
        )

    checks.append("content_hash_matches")
    evidence["content_hash_matches"] = content_matches

    if not content_matches:
        return VerificationResult(
            result=VERIFICATION_FAILED,
            checks=checks,
            evidence=evidence,
            message=(
                "Compressed output content does not match the "
                "quarantined original."
            ),
        )

    if original_still_at_old_path:
        return VerificationResult(
            result=VERIFICATION_PARTIAL,
            checks=checks,
            evidence=evidence,
            message=(
                "Compression and quarantine content verified, but a "
                "file still exists at the original path."
            ),
        )

    return VerificationResult(
        result=VERIFICATION_PASSED,
        checks=checks,
        evidence=evidence,
        message="Compression, quarantine and content integrity all verified.",
    )


def verify_storage_goal(state) -> VerificationResult:
    """
    Goal-level verification for the mission's overall storage-recovery
    target: has the mission actually recovered at least as many bytes
    as it claims, based on completed_actions rather than the running
    counter alone.
    """

    claimed_total = sum(
        action.get("storage_recovered_bytes", 0)
        for action in state.completed_actions
        if action.get("status") == "VERIFIED_AND_QUARANTINED"
    )

    checks = ["recomputed_total_matches_state", "target_reached"]

    evidence = {
        "claimed_total_bytes": claimed_total,
        "state_recovered_bytes": state.recovered_bytes,
        "target_storage_bytes": state.target_storage_bytes,
    }

    totals_match = claimed_total == state.recovered_bytes
    evidence["totals_match"] = totals_match

    target_reached = state.recovered_bytes >= state.target_storage_bytes
    evidence["target_reached"] = target_reached

    if not totals_match:
        return VerificationResult(
            result=VERIFICATION_PARTIAL,
            checks=checks,
            evidence=evidence,
            message=(
                "Recomputed recovered bytes from completed actions does "
                "not match the mission's running total."
            ),
        )

    if not target_reached:
        return VerificationResult(
            result=VERIFICATION_FAILED,
            checks=checks,
            evidence=evidence,
            message="Target storage recovery has not yet been reached.",
        )

    return VerificationResult(
        result=VERIFICATION_PASSED,
        checks=checks,
        evidence=evidence,
        message="Storage recovery target reached and totals reconcile.",
    )


def verify_no_prohibited_deletions(state, protected_paths_at_start: list[str]) -> VerificationResult:
    """
    Confirm that every path present (and expected to be protected) at
    the start of a mission still exists somewhere on disk - either at
    its original location or in quarantine - i.e. nothing was silently
    deleted outright. Synora never deletes files itself (only
    compresses + quarantines), so this should always pass; it exists as
    an explicit, checkable guarantee rather than an assumption.
    """

    checks = ["protected_path_recoverable"]
    evidence: dict = {"checked_paths": {}}

    all_missing = []

    for path in protected_paths_at_start:
        original_exists = Path(path).exists()

        quarantined_elsewhere = any(
            Path(action.get("quarantine_path", "")).exists()
            for action in state.completed_actions
            if action.get("path") == path
        )

        recoverable = original_exists or quarantined_elsewhere
        evidence["checked_paths"][path] = recoverable

        if not recoverable:
            all_missing.append(path)

    if all_missing:
        return VerificationResult(
            result=VERIFICATION_FAILED,
            checks=checks,
            evidence=evidence,
            message=f"{len(all_missing)} protected path(s) are no longer recoverable.",
        )

    return VerificationResult(
        result=VERIFICATION_PASSED,
        checks=checks,
        evidence=evidence,
        message="All protected paths remain recoverable (original or quarantined).",
    )