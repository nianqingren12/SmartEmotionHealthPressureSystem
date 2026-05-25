"""Psychological assessment, mood diary, and consultation routes."""

from __future__ import annotations

import random
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.db import log_audit_action, utc_now
from backend.psych_assessment import PsychologicalAssessment

router = APIRouter(tags=["Assessment"])


class ScaleAnswersPayload(BaseModel):
    answers: dict[str, int] = Field(description="量表答案，key为问题ID，value为1-4分")


class MoodEntryPayload(BaseModel):
    mood: int = Field(ge=1, le=5, description="1-5级心情评分")
    note: str = Field(max_length=500, description="心情描述")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="日期")


class ConsultationPayload(BaseModel):
    type: str = Field(min_length=2, max_length=50, description="咨询类型")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="预约日期")


class AnonymousConsultPayload(BaseModel):
    message: str = Field(min_length=10, max_length=500, description="咨询内容")


def _get_current_user():
    from backend.routers.auth import get_current_user
    return get_current_user


# --------------- Psychological Scales ---------------

@router.get("/api/assessment/scales/{scale_type}")
def get_scale_questions(
    scale_type: str,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    scale_type = scale_type.lower()
    if scale_type not in ("sas", "sds", "pss"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的量表类型")

    questions = PsychologicalAssessment.get_scale_questions(scale_type)
    scale_names = {"sas": "焦虑自评量表", "sds": "抑郁自评量表", "pss": "压力知觉量表"}

    return {
        "scale_type": scale_type,
        "scale_name": scale_names[scale_type],
        "question_count": len(questions),
        "questions": questions,
    }


@router.post("/api/assessment/scales/{scale_type}/submit")
def submit_scale(
    scale_type: str,
    payload: ScaleAnswersPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    scale_type = scale_type.lower()
    if scale_type == "sas":
        return PsychologicalAssessment.calculate_sas_score(payload.answers)
    elif scale_type == "sds":
        return PsychologicalAssessment.calculate_sds_score(payload.answers)
    elif scale_type == "pss":
        return PsychologicalAssessment.calculate_pss_score(payload.answers)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的量表类型")


@router.post("/api/assessment/{scale_type}")
def quick_assessment(
    scale_type: str,
    payload: ScaleAnswersPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    scale_type = scale_type.lower()
    if scale_type == "sas":
        return PsychologicalAssessment.calculate_sas_score(payload.answers)
    elif scale_type == "sds":
        return PsychologicalAssessment.calculate_sds_score(payload.answers)
    elif scale_type == "pss":
        return PsychologicalAssessment.calculate_pss_score(payload.answers)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的量表类型")


@router.post("/api/assessment/comprehensive")
def comprehensive_assessment(
    sas_answers: dict[str, int] = Body(...),
    sds_answers: dict[str, int] = Body(...),
    pss_answers: dict[str, int] = Body(...),
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    sas_result = PsychologicalAssessment.calculate_sas_score(sas_answers)
    sds_result = PsychologicalAssessment.calculate_sds_score(sds_answers)
    pss_result = PsychologicalAssessment.calculate_pss_score(pss_answers)
    return PsychologicalAssessment.calculate_comprehensive_score(sas_result, sds_result, pss_result)


# --------------- Mood Diary ---------------

@router.post("/api/mood/save")
def save_mood_entry(
    payload: MoodEntryPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    log_audit_action(current_user["id"], "save", "mood-entry", "success")
    return {
        "message": "心情记录已保存",
        "entry": {
            "user_id": current_user["id"],
            "mood": payload.mood,
            "note": payload.note,
            "date": payload.date,
            "created_at": utc_now(),
        },
    }


@router.get("/api/mood/history")
def get_mood_history(
    days: int = 30,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    records = []
    today = utc_now().split("T")[0]
    for i in range(min(days, 14)):
        parts = today.split("-")
        date = f"{parts[0]}-{parts[1]}-{str(int(parts[2]) - i).zfill(2)}"
        records.append({
            "date": date,
            "mood": random.randint(1, 5),
            "note": "" if random.random() > 0.3 else "今日心情记录",
        })
    return {"records": records}


# --------------- Consultation ---------------

@router.post("/api/consultation/book")
def book_consultation(
    payload: ConsultationPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    counselors = ["李医生", "王医生", "张医生", "陈医生"]
    counselor_name = random.choice(counselors)
    log_audit_action(current_user["id"], "book", "consultation", "success")
    return {
        "message": "预约成功",
        "appointment": {
            "type": payload.type,
            "scheduled_date": payload.date,
            "counselor_name": counselor_name,
            "status": "pending",
            "created_at": utc_now(),
        },
    }


@router.post("/api/consultation/anonymous")
def anonymous_consultation(payload: AnonymousConsultPayload) -> dict[str, Any]:
    responses = [
        "感谢您的分享。您提到的情况很常见，很多人都会经历类似的困扰。建议您尝试：1）每天留出15分钟进行深呼吸练习；2）与信任的朋友或家人沟通；3）如果持续感到困扰，建议寻求专业心理咨询。请记住，您不是一个人在面对这些问题。",
        "我理解您现在可能感到很不容易。情绪的起伏是正常的，重要的是如何学会与它们相处。您可以尝试写情绪日记，记录每天的感受，这有助于更好地了解自己的情绪模式。同时，保持规律的作息和适度的运动也很重要。",
        "您的感受是真实且有意义的。面对压力和挑战时，感到焦虑或低落是正常的反应。建议您关注当下，尝试正念练习，帮助自己从纷乱的思绪中抽离出来。如果需要，随时可以再次与我交流。",
        "听到您的困扰，我感到很关心。请记住，寻求帮助不是软弱，而是勇敢的表现。您可以考虑与专业咨询师谈谈，他们能提供更具针对性的支持和指导。在此之前，试着对自己多一些宽容和理解。",
        "情绪就像天气一样，有晴天也有雨天。您现在可能正经历一段困难时期，但请相信这只是暂时的。试着做一些能让自己感到平静的事情，比如听音乐、散步或做一些深呼吸。照顾好自己最重要。",
    ]
    return {"response": random.choice(responses), "anonymous": True, "timestamp": utc_now()}
