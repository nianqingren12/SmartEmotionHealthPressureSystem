"""Recognition, reports, companion, and data export routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from backend.db import (
    consume_report_credit,
    create_report,
    get_recognition_by_id,
    get_recent_recognitions,
    get_report_by_id,
    save_recognition,
)
from backend.inference import (
    build_companion_reply,
    build_emotion_report,
    build_sequence_summary,
    build_workplace_assessment,
    predict_micro_expression,
    predict_micro_expression_sequence,
)

router = APIRouter(tags=["Recognition"])


class RecognitionPayload(BaseModel):
    image_data_url: str = Field(min_length=20)
    source_type: str = "camera"


class SequenceRecognitionPayload(BaseModel):
    frames: list[str] = Field(min_length=2, max_length=12)
    source_type: str = "upload-video"


class WorkplacePayload(BaseModel):
    scenario: str = Field(min_length=2, max_length=50)


class CompanionPayload(BaseModel):
    emotion: str = Field(min_length=1, max_length=20)


# Import get_current_user lazily to avoid circular imports
def _get_current_user():
    from backend.routers.auth import get_current_user
    return get_current_user


@router.post("/api/recognition/realtime")
def realtime_recognition(
    payload: RecognitionPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    result = predict_micro_expression(payload.image_data_url)
    record = save_recognition(current_user["id"], payload.source_type, result)
    return {"record": record, "message": "识别成功，已写入个人历史记录。"}


@router.post("/api/recognition/sequence")
def sequence_recognition(
    payload: SequenceRecognitionPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    result = predict_micro_expression_sequence(payload.frames, payload.source_type)
    saved_records = []
    for frame in result["frames"]:
        saved_records.append(
            save_recognition(
                current_user["id"], payload.source_type,
                {
                    "label": frame["label"], "confidence": frame["confidence"],
                    "intensity": frame["intensity"], "duration_ms": frame["duration_ms"],
                    "secondary_label": frame["secondary_label"],
                    "engine": frame["engine"], "engine_version": frame["engine_version"],
                    "note": f"序列分析第 {frame['frame_index']} 帧",
                },
            )
        )
    return {
        "summary": build_sequence_summary(result),
        "sequence": result,
        "saved_count": len(saved_records),
    }


@router.get("/api/recognitions/{recognition_id}")
def recognition_detail(
    recognition_id: int,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    rec = get_recognition_by_id(current_user["id"], recognition_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="识别记录不存在")
    return rec


@router.post("/api/reports/generate")
def generate_report(
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    if not consume_report_credit(current_user["id"]):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="免费报告次数已用完，请升级会员")
    recognitions = get_recent_recognitions(current_user["id"], limit=20)
    if len(recognitions) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少完成 3 次识别后再生成深度报告")
    details = build_emotion_report(recognitions)
    report = create_report(current_user["id"], "emotion-insight", "情绪深度分析报告", details["summary"], details, paid=True)
    return {"report": report, "message": "报告生成完成。"}


@router.get("/api/reports/{report_id}")
def report_detail(
    report_id: int,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    report = get_report_by_id(current_user["id"], report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    return report


@router.post("/api/evaluations/workplace")
def workplace_assessment(
    payload: WorkplacePayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    recognitions = get_recent_recognitions(current_user["id"], limit=12)
    return build_workplace_assessment(recognitions, payload.scenario)


@router.post("/api/companion/respond")
def companion_reply(
    payload: CompanionPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    return {"message": build_companion_reply(payload.emotion), "user_id": current_user["id"]}


@router.get("/api/data/export")
def export_data(current_user: dict[str, Any] = Depends(_get_current_user())):
    recognitions = get_recent_recognitions(current_user["id"], limit=100)
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["时间", "微表情", "置信度", "强度", "持续时长(ms)", "引擎"])
    for item in recognitions:
        writer.writerow([
            item["created_at"], item["label"], item["confidence"],
            item["intensity"], item["duration_ms"], item["engine"],
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=emotion-export.csv; charset=utf-8-sig"},
    )
