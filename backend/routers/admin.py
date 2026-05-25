"""Admin routes: dashboard overview, lead management, audit logs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.db import (
    get_admin_overview,
    get_connection,
    get_dashboard_overview,
    list_custom_training_requests,
    log_audit_action,
    update_custom_training_request_status,
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class LeadStatusPayload(BaseModel):
    status: str = Field(min_length=2, max_length=20)


def _get_current_user():
    from backend.routers.auth import get_current_user
    return get_current_user


def _ensure_admin_access(current_user: dict[str, Any]) -> None:
    if current_user["membership_tier"] == "enterprise" or current_user["email"].startswith("admin@"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号无企业管理权限")


@router.get("/overview")
def admin_overview(current_user: dict[str, Any] = Depends(_get_current_user())) -> dict[str, Any]:
    _ensure_admin_access(current_user)
    return get_admin_overview()


@router.get("/leads")
def admin_leads(current_user: dict[str, Any] = Depends(_get_current_user())) -> list[dict[str, Any]]:
    _ensure_admin_access(current_user)
    return list_custom_training_requests()


@router.patch("/leads/{lead_id}")
def update_lead_status(
    lead_id: int,
    payload: LeadStatusPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    _ensure_admin_access(current_user)
    update_custom_training_request_status(lead_id, payload.status)
    log_audit_action(current_user["id"], "update", f"lead:{lead_id}", "success")
    return {"message": "状态已更新"}


@router.post("/leads/{request_id}")
def admin_update_lead(
    request_id: int,
    payload: LeadStatusPayload,
    current_user: dict[str, Any] = Depends(_get_current_user()),
) -> dict[str, Any]:
    _ensure_admin_access(current_user)
    updated = update_custom_training_request_status(request_id, payload.status)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="企业线索不存在")
    return updated


@router.get("/audit-logs")
def get_audit_logs(current_user: dict[str, Any] = Depends(_get_current_user())) -> list[dict[str, Any]]:
    _ensure_admin_access(current_user)
    from backend.db import DB_TYPE
    sql = "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50"
    if DB_TYPE == "mysql":
        sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
