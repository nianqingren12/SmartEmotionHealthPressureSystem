"""Health, calibration, biometrics, and video analysis routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.biometrics import BiometricIntegrator
from backend.db import (
    get_recent_recognitions,
    get_user_calibration,
    log_audit_action,
    save_user_calibration,
)
from backend.inference import get_inference_engine
from backend.video_analysis import video_analyzer

router = APIRouter(tags=["Health"])


class BiometricPayload(BaseModel):
    emotion: str = Field(description="情绪标签")
    intensity: float = Field(ge=0, le=1, description="情绪强度")
    base_hr: int = Field(default=72, description="基础心率")


class VideoFramePayload(BaseModel):
    frame_base64: str = Field(description="视频帧的Base64编码")
    timestamp: float = Field(description="帧时间戳")


class LiveFramePayload(BaseModel):
    session_id: str = Field(description="会话ID")
    frame_base64: str = Field(description="视频帧Base64")
    timestamp: float = Field(description="时间戳")


def _get_current_user():
    from backend.routers.auth import get_current_user
    return get_current_user


# --------------- Calibration & Health Assessment ---------------

@router.post("/api/health/calibrate")
def calibrate(payload: dict[str, Any], current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    save_user_calibration(current_user["id"], payload)
    log_audit_action(current_user["id"], "calibration", "health-profile", "success")
    return {"message": "基准校准已保存，AI 评估严谨度已提升。"}


@router.post("/api/health/assessment")
def health_assessment(current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    recognitions = get_recent_recognitions(current_user["id"], limit=20)
    calibration = get_user_calibration(current_user["id"])
    engine = get_inference_engine()
    log_audit_action(current_user["id"], "generate", "health-assessment", "success")
    return engine.build_health_assessment(recognitions, calibration)


@router.get("/api/health/biometrics")
def get_health_biometrics(current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    recognitions = get_recent_recognitions(current_user["id"], limit=5)
    if recognitions:
        latest = recognitions[0]
        emotion = latest["label"]
        intensity = latest["intensity"] / 100.0
    else:
        emotion = "平静"
        intensity = 0.3
    bm = BiometricIntegrator.simulate_biometrics(emotion, intensity)
    return {
        "heart_rate": bm["heart_rate"], "heart_rate_status": bm["heart_rate_status"],
        "hrv": bm["hrv"], "hrv_status": bm["hrv_status"],
        "breathing_rate": bm["breathing_rate"],
        "stress_percentage": bm["stress_level"],
        "health_advice": BiometricIntegrator._get_health_advice(bm),
    }


# --------------- Biometrics ---------------

@router.post("/api/biometrics/simulate")
def simulate_biometrics(
    payload: BiometricPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    return BiometricIntegrator.simulate_biometrics(payload.emotion, payload.intensity, payload.base_hr)


@router.post("/api/biometrics/analyze-sequence")
def analyze_biometric_sequence(
    biometric_data: list[dict[str, Any]] = Body(...),
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    return BiometricIntegrator.analyze_biometric_sequence(biometric_data)


@router.post("/api/biometrics/integrate")
def integrate_biometrics_with_emotion(
    emotion_result: dict[str, Any] = Body(...),
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    emotion = emotion_result.get("label", "平静")
    intensity = emotion_result.get("intensity", 0.0)
    biometrics = BiometricIntegrator.simulate_biometrics(emotion, intensity)
    return {
        "emotion_result": emotion_result,
        "biometric_data": biometrics,
        "combined_analysis": {
            "stress_level": biometrics["stress_level"],
            "overall_status": biometrics["blood_pressure"]["status"],
            "recommendation": BiometricIntegrator._get_health_advice(biometrics),
        },
    }


# --------------- Video Stream ---------------

@router.post("/api/video/create-session")
def create_video_session(current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    session_id = video_analyzer.create_session(current_user["id"])
    return {"session_id": session_id}


@router.post("/api/video/process-frame/{session_id}")
def process_video_frame(
    session_id: str,
    payload: VideoFramePayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    try:
        return video_analyzer.process_frame(session_id, payload.frame_base64, payload.timestamp)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/api/video/process-frame")
def process_frame_simple(
    payload: LiveFramePayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    try:
        return video_analyzer.process_frame(payload.session_id, payload.frame_base64, payload.timestamp)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/api/video/session/{session_id}")
def get_session_summary(
    session_id: str,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    try:
        return video_analyzer.get_session_summary(session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/api/video/session-summary/{session_id}")
def get_session_summary_simple(
    session_id: str,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    try:
        return video_analyzer.get_session_summary(session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/api/video/live/{session_id}")
def get_live_emotion(
    session_id: str,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    try:
        return video_analyzer.get_live_emotion(session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/api/video/session/{session_id}")
def close_video_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    try:
        return video_analyzer.close_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
