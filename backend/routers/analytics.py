"""User analytics, marketing, and API management routes."""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.api_management import APIManager
from backend.inference import predict_micro_expression
from backend.marketing import MarketingManager
from backend.user_analytics import UserAnalytics

router = APIRouter(tags=["Analytics & API"])


class CampaignPayload(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    template_id: str = Field(min_length=2, max_length=100)
    segment_criteria: dict[str, Any]
    scheduled_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


class RecognitionPayload(BaseModel):
    image_data_url: str = Field(min_length=20)
    source_type: str = "camera"


def _get_current_user():
    from backend.routers.auth import get_current_user
    return get_current_user


# --------------- User Analytics ---------------

@router.get("/api/analytics/behavior")
def get_behavior_analysis(
    days: int = 30,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    return UserAnalytics.get_user_behavior_analysis(current_user["id"], days=days)


@router.get("/api/analytics/emotion")
def get_emotion_analysis(
    days: int = 30,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    return UserAnalytics.get_emotion_analysis(current_user["id"], days=days)


@router.get("/api/analytics/segmentation")
def get_user_segmentation(
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    return UserAnalytics.get_user_segmentation(current_user["id"])


@router.get("/api/analytics/churn-risk")
def get_churn_risk(
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    return UserAnalytics.predict_churn_risk(current_user["id"])


# --------------- Marketing ---------------

@router.post("/api/marketing/campaigns")
def create_campaign(
    payload: CampaignPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    if not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员可以创建营销活动")
    campaign_id = MarketingManager.create_email_campaign(
        payload.name, payload.template_id, payload.segment_criteria, payload.scheduled_at
    )
    return {"campaign_id": campaign_id, "message": "营销活动创建成功"}


@router.get("/api/marketing/campaigns")
def get_campaigns(
    status: Optional[str] = None,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> list[dict[str, Any]]:
    if not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员可以查看营销活动")
    return MarketingManager.get_campaigns(status=status)


@router.post("/api/marketing/test-email")
def send_test_email(
    email: str = Query(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    template_id: str = Query(..., min_length=2, max_length=100),
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    if not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员可以发送测试邮件")
    success = MarketingManager.send_campaign_email(1, template_id)
    if success:
        return {"message": f"测试邮件已发送到 {email}"}
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="邮件发送失败")


@router.post("/api/marketing/segment-users")
def segment_users(
    criteria: dict[str, Any],
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    if not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员可以进行用户分群")
    user_ids = MarketingManager.segment_users(criteria)
    return {"user_count": len(user_ids), "user_ids": user_ids}


# --------------- API Key Management ---------------

@router.post("/api/api-keys/generate")
def generate_api_key(current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    if current_user["membership_tier"] != "enterprise" and not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有企业用户可以生成API密钥")
    api_key = APIManager.generate_api_key(current_user["id"])
    return {"api_key": api_key, "message": "API密钥生成成功，请妥善保管"}


@router.get("/api/api-keys")
def get_api_keys(current_user: dict[str, Any] = Depends(_get_current_user())) -> list[dict[str, Any]]:
    return APIManager.get_user_api_keys(current_user["id"])


@router.delete("/api/api-keys/{key_id}")
def revoke_api_key(key_id: int, current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    success = APIManager.revoke_api_key(key_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API密钥不存在或无权限操作")
    return {"message": "API密钥已成功撤销"}


@router.get("/api/api-usage")
def get_api_usage(current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    return APIManager.get_api_usage(current_user["id"])


# --------------- Enterprise API ---------------

@router.post("/api/enterprise/recognize")
def enterprise_recognize(
    payload: RecognitionPayload,
    api_key: str = Header(None, alias="X-API-Key"),
) -> dict[str, Any]:
    key_info = APIManager.validate_api_key(api_key)
    if not key_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的API密钥")
    start_time = time.time()
    try:
        result = predict_micro_expression(payload.image_data_url)
        response_time = time.time() - start_time
        APIManager.log_api_call(key_info["user_id"], "/api/enterprise/recognize", "success", response_time)
        return {"result": result, "api_key_id": key_info["id"]}
    except Exception as e:
        response_time = time.time() - start_time
        APIManager.log_api_call(key_info["user_id"], "/api/enterprise/recognize", "error", response_time)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
