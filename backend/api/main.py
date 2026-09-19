from dotenv import load_dotenv
load_dotenv()

from dataclasses import asdict
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.agent import create_mission_from_request
from agent.controller import run_mission as execute_mission
from agent.state import (
    SAFE_MODE,
    ASK_BEFORE_ACTION_MODE,
    AUTONOMOUS_MODE,
    MissionState,
)
from domains import router as domain_router
from memory import history as mission_history
from memory.history import get_mission_history, summarize_mission_history
from storage.database import save_mission, load_mission, list_missions

from tools.scanner import scan_directory
from tools.duplicates import find_duplicates
from tools.compression import compress_file
from tools.quarantine import quarantine_file
from tools.restore import restore_file
from tools.verification import verify_file


app = FastAPI(
    title="Synora API",
    description="AI-powered storage management agent",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class MissionRequest(BaseModel):
    user_request: str
    operation_mode: str = SAFE_MODE


class RunMissionRequest(BaseModel):
    user_request: str
    directory: str
    max_cycles: int = 10
    operation_mode: str = SAFE_MODE


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "synora-backend",
    }


# ---------------------------------------------------------
# STORAGE SCANNING
# ---------------------------------------------------------

@app.get("/scan")
def scan(directory: str):
    try:
        files = scan_directory(directory)

        return {
            "directory": directory,
            "file_count": len(files),
            "files": files,
        }

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except NotADirectoryError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
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

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except NotADirectoryError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# ---------------------------------------------------------
# FILE OPERATIONS
# ---------------------------------------------------------

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

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except FileExistsError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
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

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
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

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
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

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# ---------------------------------------------------------
# LEGACY / DASHBOARD MISSION API (kept for the current frontend)
# ---------------------------------------------------------

@app.post("/mission")
def start_mission(
    user_goal: str,
    target_storage_bytes: int,
    directory: str = "demo_data/demo_drive",
    max_cycles: int = 10,
):
    if target_storage_bytes <= 0:
        raise HTTPException(
            status_code=400,
            detail="target_storage_bytes must be greater than 0.",
        )

    if max_cycles <= 0:
        raise HTTPException(
            status_code=400,
            detail="max_cycles must be greater than 0.",
        )

    mission_id = f"mission-{uuid4().hex[:8]}"

    state = MissionState(
        mission_id=mission_id,
        user_goal=user_goal,
        target_storage_bytes=target_storage_bytes,
    )

    try:
        final_state = execute_mission(
            state,
            directory,
            max_cycles=max_cycles,
        )

        save_mission(asdict(final_state))

        return asdict(final_state)

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except NotADirectoryError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@app.get("/mission")
def get_mission():
    mission = load_mission()

    if mission is None:
        raise HTTPException(
            status_code=404,
            detail="No saved mission found.",
        )

    return mission


# ---------------------------------------------------------
# MISSION APPROVAL / RESUME (legacy, kept for current frontend)
# ---------------------------------------------------------

@app.post("/mission/approve")
def approve_mission(
    mission_id: str,
    directory: str = "demo_data/demo_drive",
    max_cycles: int = 10,
):
    mission = load_mission(mission_id=mission_id)

    if mission is None:
        # Fall back to "most recent mission" for old clients that never
        # pass a mission_id that this store recognizes as a key.
        mission = load_mission()

    if mission is None:
        raise HTTPException(
            status_code=404,
            detail="No saved mission found.",
        )

    if mission.get("mission_id") != mission_id:
        raise HTTPException(
            status_code=404,
            detail="Mission not found.",
        )

    if max_cycles <= 0:
        raise HTTPException(
            status_code=400,
            detail="max_cycles must be greater than 0.",
        )

    try:
        state = MissionState(**mission)

        if state.status != "WAITING_FOR_APPROVAL":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Mission is not waiting for approval."
                ),
            )

        approved = state.approve_pending_action()

        if not approved:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No pending action requires approval."
                ),
            )

        mission_history.record_approval_granted(state.mission_id, approved)

        save_mission(asdict(state))

        final_state = execute_mission(
            state,
            directory,
            max_cycles=max_cycles,
        )

        save_mission(asdict(final_state))

        return asdict(final_state)

    except HTTPException:
        raise

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except NotADirectoryError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ---------------------------------------------------------
# NEW MISSION API (mission-ID-aware)
# ---------------------------------------------------------

@app.post("/missions")
def create_mission(request: MissionRequest):
    try:
        if request.operation_mode not in {
            SAFE_MODE,
            ASK_BEFORE_ACTION_MODE,
            AUTONOMOUS_MODE,
        }:
            raise ValueError(
                f"Invalid operation mode: "
                f"{request.operation_mode}"
            )

        state = create_mission_from_request(
            request.user_request
        )

        state.set_operation_mode(
            request.operation_mode
        )

        save_mission(asdict(state))

        return asdict(state)

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.post("/missions/run")
def run_mission(request: RunMissionRequest):
    try:
        if request.operation_mode not in {
            SAFE_MODE,
            ASK_BEFORE_ACTION_MODE,
            AUTONOMOUS_MODE,
        }:
            raise ValueError(
                f"Invalid operation mode: "
                f"{request.operation_mode}"
            )

        state = create_mission_from_request(
            request.user_request
        )

        state.set_operation_mode(
            request.operation_mode
        )

        save_mission(asdict(state))

        state = execute_mission(
            state,
            request.directory,
            max_cycles=request.max_cycles,
        )

        save_mission(asdict(state))

        return asdict(state)

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.get("/missions/latest")
def get_latest_mission():
    state = load_mission()

    if state is None:
        raise HTTPException(
            status_code=404,
            detail="No mission found.",
        )

    return state


@app.get("/missions")
def get_all_missions():
    return {"missions": list_missions()}


@app.get("/missions/{mission_id}")
def get_mission_by_id(mission_id: str):
    state = load_mission(mission_id=mission_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Mission '{mission_id}' not found.",
        )

    return state


@app.post("/missions/{mission_id}/run")
def continue_mission(mission_id: str, directory: str = "demo_data/demo_drive", max_cycles: int = 10):
    mission = load_mission(mission_id=mission_id)

    if mission is None:
        raise HTTPException(
            status_code=404,
            detail=f"Mission '{mission_id}' not found.",
        )

    try:
        state = MissionState(**mission)

        state = execute_mission(
            state,
            directory,
            max_cycles=max_cycles,
        )

        save_mission(asdict(state))

        return asdict(state)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@app.post("/missions/{mission_id}/approve")
def approve_mission_by_id(mission_id: str, directory: str = "demo_data/demo_drive", max_cycles: int = 10):
    mission = load_mission(mission_id=mission_id)

    if mission is None:
        raise HTTPException(
            status_code=404,
            detail=f"Mission '{mission_id}' not found.",
        )

    try:
        state = MissionState(**mission)

        if state.status != "WAITING_FOR_APPROVAL":
            raise HTTPException(
                status_code=400,
                detail="Mission is not waiting for approval.",
            )

        approved = state.approve_pending_action()

        if not approved:
            raise HTTPException(
                status_code=400,
                detail="No pending action requires approval.",
            )

        mission_history.record_approval_granted(state.mission_id, approved)

        save_mission(asdict(state))

        final_state = execute_mission(
            state,
            directory,
            max_cycles=max_cycles,
        )

        save_mission(asdict(final_state))

        return asdict(final_state)

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@app.get("/missions/{mission_id}/plan")
def get_mission_plan(mission_id: str):
    state = load_mission(mission_id=mission_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Mission '{mission_id}' not found.",
        )

    return {
        "mission_id": mission_id,
        "planned_actions": state.get("planned_actions", []),
        "completed_actions": state.get("completed_actions", []),
        "failed_actions": state.get("failed_actions", []),
    }


@app.get("/missions/{mission_id}/verification")
def get_mission_verification(mission_id: str):
    state = load_mission(mission_id=mission_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Mission '{mission_id}' not found.",
        )

    return {
        "mission_id": mission_id,
        "verification_results": state.get("verification_results", []),
    }


@app.get("/missions/{mission_id}/history")
def get_mission_history_endpoint(mission_id: str):
    return {
        "mission_id": mission_id,
        "history": get_mission_history(mission_id),
        "summary": summarize_mission_history(mission_id),
    }


# ---------------------------------------------------------
# DOMAINS
# ---------------------------------------------------------

@app.get("/domains")
def get_domains():
    return {"domains": domain_router.list_all_capabilities()}


@app.get("/domains/{domain_name}")
def get_domain(domain_name: str):
    try:
        return domain_router.get_capabilities(domain_name.upper())
    except domain_router.UnknownDomainError as error:
        raise HTTPException(status_code=404, detail=str(error))


# ---------------------------------------------------------
# WORKSPACE (read-only inspection, no mission started)
# ---------------------------------------------------------

@app.get("/workspace/inspect")
def inspect_workspace(directory: str):
    try:
        from domains.file import domain as file_domain

        return file_domain.inspect_workspace(directory)

    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except NotADirectoryError as error:
        raise HTTPException(status_code=400, detail=str(error))