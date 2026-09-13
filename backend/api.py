from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.controller import run_mission
from agent.state import MissionState
from storage.database import load_mission

from tools.scanner import scan_directory
from tools.duplicates import find_duplicates
from tools.compression import compress_file
from tools.quarantine import quarantine_file
from tools.restore import restore_file
from tools.verification import verify_file


app = FastAPI(
    title="Synora API",
    description="Storage optimization and file management backend",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Synora API is running",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.get("/scan")
def scan(directory: str):
    try:
        files = scan_directory(directory)

        return {
            "directory": directory,
            "file_count": len(files),
            "files": files,
        }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except NotADirectoryError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@app.get("/duplicates")
def duplicates(directory: str):
    try:
        files = scan_directory(directory)

        duplicate_groups = find_duplicates(files)

        return {
            "directory": directory,
            "duplicate_group_count": len(
                duplicate_groups
            ),
            "duplicates": duplicate_groups,
        }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except NotADirectoryError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@app.post("/compress")
def compress(
    file_path: str,
    output_directory: str,
):
    try:
        compressed_path = compress_file(
            file_path,
            output_directory,
        )

        return {
            "file": file_path,
            "compressed_file": compressed_path,
            "status": "success",
        }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except FileExistsError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@app.post("/quarantine")
def quarantine(
    file_path: str,
    quarantine_directory: str,
):
    try:
        quarantined_path = quarantine_file(
            file_path,
            quarantine_directory,
        )

        return {
            "file": file_path,
            "quarantined_file": quarantined_path,
            "status": "success",
        }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@app.post("/restore")
def restore(
    quarantined_file: str,
    restore_directory: str,
):
    try:
        restored_path = restore_file(
            quarantined_file,
            restore_directory,
        )

        return {
            "quarantined_file": quarantined_file,
            "restored_file": restored_path,
            "status": "success",
        }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@app.post("/verify")
def verify(
    file_path: str,
    expected_hash: str,
):
    try:
        verified = verify_file(
            file_path,
            expected_hash,
        )

        return {
            "file": file_path,
            "expected_hash": expected_hash,
            "verified": verified,
            "status": "success",
        }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@app.post("/mission")
def start_mission(
    user_goal: str,
    target_storage_bytes: int,
    directory: str = "demo_data/demo_drive",
    max_cycles: int = 10,
):
    """
    Start an autonomous Synora storage optimization mission.
    """

    if target_storage_bytes <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "target_storage_bytes must be "
                "greater than 0."
            ),
        )

    if max_cycles <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "max_cycles must be "
                "greater than 0."
            ),
        )

    mission_id = (
        f"mission-{uuid4().hex[:8]}"
    )

    state = MissionState(
        mission_id=mission_id,
        user_goal=user_goal,
        target_storage_bytes=target_storage_bytes,
    )

    try:
        final_state = run_mission(
            state,
            directory,
            max_cycles=max_cycles,
        )

        return {
            "mission_id": final_state.mission_id,
            "user_goal": final_state.user_goal,
            "target_storage_bytes": (
                final_state.target_storage_bytes
            ),
            "recovered_bytes": (
                final_state.recovered_bytes
            ),
            "status": final_state.status,
            "planned_actions": (
                final_state.planned_actions
            ),
            "completed_actions": (
                final_state.completed_actions
            ),
            "failed_actions": (
                final_state.failed_actions
            ),
            "protected_paths": (
                final_state.protected_paths
            ),
            "replanning_count": (
                final_state.replanning_count
            ),
        }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except NotADirectoryError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get("/mission")
def get_mission():
    """
    Return the most recently saved Synora mission.
    """

    mission = load_mission()

    if mission is None:
        raise HTTPException(
            status_code=404,
            detail="No saved mission found.",
        )

    return mission
