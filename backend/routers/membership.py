"""Membership, payment, orders, courses, custom training, and ads routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.db import (
    create_order,
    get_dashboard_overview,
    get_recent_orders,
    redeem_recharge_code,
    save_custom_training_request,
)
from backend.inference import build_ad_recommendation
from backend.payment import PaymentProcessor, get_payment_config

router = APIRouter(tags=["Membership"])


class PurchasePayload(BaseModel):
    plan_name: str


class RechargePayload(BaseModel):
    code: str = Field(min_length=5, max_length=50)


class CustomTrainingPayload(BaseModel):
    industry: str = Field(min_length=2, max_length=30)
    description: str = Field(min_length=2, max_length=500)


class PaymentPayload(BaseModel):
    amount: float = Field(gt=0)
    product_type: str = Field(min_length=2, max_length=100)


def _get_current_user():
    from backend.routers.auth import get_current_user
    return get_current_user


@router.get("/api/dashboard/overview")
def dashboard_overview(current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    from backend.db import get_recent_recognitions, get_recent_reports
    return {
        **get_dashboard_overview(current_user["id"]),
        "recent_recognitions": get_recent_recognitions(current_user["id"]),
        "recent_reports": get_recent_reports(current_user["id"]),
        "recent_orders": get_recent_orders(current_user["id"]),
    }


@router.get("/api/membership/plans")
def membership_plans() -> list[dict[str, Any]]:
    return [
        {"name": "普通会员", "price": "9.9元/月", "amount": 9.9, "rights": ["每月 10 次报告", "基础陪伴互动", "识别历史存储"]},
        {"name": "高级会员", "price": "29.9元/月", "amount": 29.9, "rights": ["无限报告", "职场测评", "高级数据导出", "定制服务折扣"]},
        {"name": "企业会员", "price": "999元/年", "amount": 999.0, "rights": ["企业导出权限", "批量账号管理", "定制模型评估", "专属支持"]},
    ]


@router.post("/api/membership/purchase")
def purchase_membership(
    payload: PurchasePayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    plan_mapping = {
        "普通会员": ("普通会员", 9.9, 30), "basic": ("普通会员", 9.9, 30),
        "高级会员": ("高级会员", 29.9, 30), "pro": ("高级会员", 29.9, 30),
        "企业会员": ("企业会员", 999.0, 365), "enterprise": ("企业会员", 999.0, 365),
    }
    if payload.plan_name not in plan_mapping:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="会员类型不存在")
    product_type, amount, valid_days = plan_mapping[payload.plan_name]
    order = create_order(current_user["id"], product_type, amount, valid_days=valid_days)
    return {"order": order, "message": f"{product_type}开通成功。"}


@router.post("/api/membership/recharge")
def recharge_membership(
    payload: RechargePayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    result = redeem_recharge_code(current_user["id"], payload.code)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="激活码无效或已被使用")
    return {
        "message": f"成功激活{result['tier']}会员，增加 {result['credits']} 次报告额度",
        "result": result,
    }


@router.post("/api/payment/create-intent")
def create_payment_intent(
    payload: PaymentPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    return PaymentProcessor.create_payment_intent(current_user["id"], payload.amount, payload.product_type)


@router.post("/api/payment/webhook")
def payment_webhook(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return PaymentProcessor.handle_webhook(request)


@router.get("/api/payment/config")
def payment_config() -> dict[str, Any]:
    return get_payment_config()


@router.get("/api/orders/history")
def orders_history(current_user: dict[str, Any] = Depends(_get_current_user())) -> list[dict[str, Any]]:
    return get_recent_orders(current_user["id"])


@router.get("/api/courses")
def courses() -> list[dict[str, str]]:
    return [
        {"title": "微表情商业解读课", "type": "课程", "price": "59元", "description": "面向求职者、销售与管理者的高频场景解读训练。"},
        {"title": "情绪管理咨询", "type": "1对1咨询", "price": "199元", "description": "结合识别报告给出个性化表达优化建议。"},
        {"title": "企业沟通工作坊", "type": "企业服务", "price": "定制报价", "description": "面向 HR 与管理团队的团体培训方案。"},
    ]


@router.post("/api/custom-training/request")
def request_custom_training(
    payload: CustomTrainingPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    record = save_custom_training_request(current_user["id"], payload.industry, payload.description)
    return {"request": record, "message": "定制训练需求已提交，商务顾问将跟进评估。"}


@router.get("/api/ads/recommendation")
def ads_recommendation(current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    overview = get_dashboard_overview(current_user["id"])
    return build_ad_recommendation(overview["dominant_emotion"])
