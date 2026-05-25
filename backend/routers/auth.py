"""Authentication routes: register, login, profile."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth import (
    decode_token,
    get_current_token,
    hash_password,
    issue_token,
    security,
    verify_password,
)
from backend.db import (
    create_user,
    get_dashboard_overview,
    get_user_by_email,
    get_user_by_id,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class AuthPayload(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=6, max_length=128)


class ForgotPasswordPayload(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)


def get_current_user(credentials=Depends(security)) -> dict[str, Any]:
    token = get_current_token(credentials)
    payload = decode_token(token)
    user = get_user_by_id(payload["user_id"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


@router.post("/register")
def register(payload: AuthPayload) -> dict[str, Any]:
    existing = get_user_by_email(payload.email.lower())
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已注册")
    user = create_user(payload.email.lower(), hash_password(payload.password))
    return {
        "token": issue_token(user["id"], user["email"]),
        "user": {
            "id": user["id"],
            "email": user["email"],
            "membership_tier": user["membership_tier"],
            "report_credits": user["report_credits"],
        },
    }


@router.post("/login")
def login(payload: AuthPayload) -> dict[str, Any]:
    user = get_user_by_email(payload.email.lower())
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    return {
        "token": issue_token(user["id"], user["email"]),
        "user": {
            "id": user["id"],
            "email": user["email"],
            "membership_tier": user["membership_tier"],
            "report_credits": user["report_credits"],
        },
    }


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordPayload) -> dict[str, str]:
    return {"message": f"演示环境已为 {payload.email} 生成重置申请，请在正式环境接入邮件服务。"}


@router.get("/me")
def me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    overview = get_dashboard_overview(current_user["id"])
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "can_manage_leads": current_user["membership_tier"] == "enterprise"
        or current_user["email"].startswith("admin@"),
        **overview,
    }
