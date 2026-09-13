from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ai.agent import (
    create_mission_from_request,
    run_ai_mission,
)
from agent.state import (
    SAFE_MODE,
    ASK_BEFORE_ACTION_MODE,
    AUTONOMOUS_MODE,
)
from storage.database import save_mission, load_mission


app = FastAPI(
    title="Synora API",
    description="AI-powered storage management agent",
    version="1.0.0",
)


class MissionRequest(BaseModel):
    user_request: str
    operation_mode: str = SAFE_MODE


class RunMissionRequest(BaseModel):
    user_request: str
    directory: str
    max_cycles: int = 10
    operation_mode: str = SAFE_MODE


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "synora-backend",
    }


@app.post("/missions")
def create_mission(request: MissionRequest):
    try:
        if request.operation_mode not in {
            SAFE_MODE,
            ASK_BEFORE_ACTION_MODE,
            AUTONOMOUS_MODE,
        }:
            raise ValueError(
                f"Invalid operation mode: {request.operation_mode}"
            )

        state = create_mission_from_request(
            request.user_request
        )

        state.set_operation_mode(request.operation_mode)

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
                f"Invalid operation mode: {request.operation_mode}"
            )

        state = create_mission_from_request(
            request.user_request
        )

        state.set_operation_mode(request.operation_mode)

        save_mission(asdict(state))

        from agent.controller import run_mission as execute_mission

        state = execute_mission(
            state,
            request.directory,
            max_cycles=request.max_cycles,
        )

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