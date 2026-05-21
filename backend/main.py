from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import logging
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request, status, Body, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
import time
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.auth import decode_token, get_current_token, hash_password, issue_token, issue_tokens, security, verify_password
from backend.db import (
    DB_TYPE,
    consume_report_credit,
    create_order,
    create_report,
    create_user,
    get_admin_overview,
    get_dashboard_overview,
    get_recognition_by_id,
    get_recent_recognitions,
    get_recent_orders,
    get_recent_reports,
    get_report_by_id,
    get_user_by_email,
    get_user_by_id,
    init_db,
    list_custom_training_requests,
    redeem_recharge_code,
    save_custom_training_request,
    save_recognition,
    update_custom_training_request_status,
    utc_now,
    log_audit_action,
    save_user_calibration,
    get_user_calibration,
)
from backend.payment import PaymentProcessor, get_payment_config
from backend.api_management import APIManager
from backend.user_analytics import UserAnalytics
from backend.marketing import MarketingManager
from backend.inference import (
    build_ad_recommendation,
    build_companion_reply,
    build_emotion_report,
    build_sequence_summary,
    build_workplace_assessment,
    predict_micro_expression,
    predict_micro_expression_sequence,
    get_inference_engine,
    get_cached_inference_engine,
)


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class AuthPayload(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=6, max_length=128)


# 统一响应模型
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    error_code: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "操作成功",
                "data": {},
                "error_code": None
            }
        }


class APIError(BaseModel):
    success: bool = False
    message: str
    error_code: str
    details: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "操作失败",
                "error_code": "INVALID_REQUEST",
                "details": "详细错误信息"
            }
        }


class ForgotPasswordPayload(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)


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


class PurchasePayload(BaseModel):
    plan_name: str


class RechargePayload(BaseModel):
    code: str = Field(min_length=5, max_length=50)


class CustomTrainingPayload(BaseModel):
    industry: str = Field(min_length=2, max_length=30)
    description: str = Field(min_length=2, max_length=500)


class LeadStatusPayload(BaseModel):
    status: str = Field(min_length=2, max_length=20)


class PaymentPayload(BaseModel):
    amount: float = Field(gt=0)
    product_type: str = Field(min_length=2, max_length=100)


app = FastAPI(
    title="微表情识别商业化原型",
    description="集用户注册、实时识别、报告生成、会员订阅和商业化功能于一体的可运行原型。",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加请求ID中间件用于追踪
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# 添加全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "服务器内部错误",
            "error_code": "INTERNAL_ERROR",
            "details": str(exc) if app.debug else None
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "details": None
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict[str, Any]:
    token = get_current_token(credentials)
    payload = decode_token(token)
    user = get_user_by_id(payload["user_id"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def ensure_admin_access(current_user: dict[str, Any]) -> None:
    if current_user["membership_tier"] == "enterprise" or current_user["email"].startswith("admin@"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号无企业管理权限")


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/api/system/status")
def get_system_status() -> dict[str, Any]:
    """获取系统状态信息"""
    try:
        engine = get_cached_inference_engine()
        return {
            "inference_engine": {
                "name": engine.name,
                "version": getattr(engine, 'version', 'unknown'),
                "model_loaded": getattr(engine, 'model_loaded', False) if hasattr(engine, 'model_loaded') else False,
                "is_real_model": getattr(engine, 'name', '').endswith('-Real'),
            },
            "database": {
                "type": DB_TYPE,
                "initialized": True
            },
            "version": "大学生面部微表情心理健康评估系统"
        }
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return {
            "inference_engine": {
                "name": "unknown",
                "version": "unknown",
                "model_loaded": False,
                "is_real_model": False,
                "error": str(e)
            },
            "database": {
                "type": DB_TYPE,
                "initialized": True
            },
            "version": "大学生面部微表情心理健康评估系统"
        }


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/auth/register")
def register(payload: AuthPayload) -> dict[str, Any]:
    existing_user = get_user_by_email(payload.email.lower())
    if existing_user:
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


@app.post("/api/auth/login")
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


@app.post("/api/auth/forgot-password")
def forgot_password(payload: ForgotPasswordPayload) -> dict[str, str]:
    return {"message": f"演示环境已为 {payload.email} 生成重置申请，请在正式环境接入邮件服务。"}


@app.get("/api/auth/me")
def me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    overview = get_dashboard_overview(current_user["id"])
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "can_manage_leads": current_user["membership_tier"] == "enterprise" or current_user["email"].startswith("admin@"),
        **overview,
    }


@app.get("/api/dashboard/overview")
def dashboard_overview(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {
        **get_dashboard_overview(current_user["id"]),
        "recent_recognitions": get_recent_recognitions(current_user["id"]),
        "recent_reports": get_recent_reports(current_user["id"]),
        "recent_orders": get_recent_orders(current_user["id"]),
    }


@app.post("/api/recognition/realtime")
def realtime_recognition(
    payload: RecognitionPayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    result = predict_micro_expression(payload.image_data_url)
    record = save_recognition(current_user["id"], payload.source_type, result)
    return {
        "record": record,
        "message": "识别成功，已写入个人历史记录。",
    }


@app.post("/api/recognition/sequence")
def sequence_recognition(
    payload: SequenceRecognitionPayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    result = predict_micro_expression_sequence(payload.frames, payload.source_type)
    saved_records = []
    for frame in result["frames"]:
        saved_records.append(
            save_recognition(
                current_user["id"],
                payload.source_type,
                {
                    "label": frame["label"],
                    "confidence": frame["confidence"],
                    "intensity": frame["intensity"],
                    "duration_ms": frame["duration_ms"],
                    "secondary_label": frame["secondary_label"],
                    "engine": frame["engine"],
                    "engine_version": frame["engine_version"],
                    "note": f"序列分析第 {frame['frame_index']} 帧",
                },
            )
        )
    return {
        "summary": build_sequence_summary(result),
        "sequence": result,
        "saved_count": len(saved_records),
    }


@app.post("/api/reports/generate")
def generate_report(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if not consume_report_credit(current_user["id"]):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="免费报告次数已用完，请升级会员")
    recognitions = get_recent_recognitions(current_user["id"], limit=20)
    if len(recognitions) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少完成 3 次识别后再生成深度报告")
    report_details = build_emotion_report(recognitions)
    report = create_report(
        current_user["id"],
        report_type="emotion-insight",
        title="情绪深度分析报告",
        summary=report_details["summary"],
        details=report_details,
        paid=True,
    )
    return {
        "report": report,
        "message": "报告生成完成。",
    }


@app.get("/api/reports/{report_id}")
def report_detail(report_id: int, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    report = get_report_by_id(current_user["id"], report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    return report


@app.get("/api/recognitions/{recognition_id}")
def recognition_detail(recognition_id: int, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    recognition = get_recognition_by_id(current_user["id"], recognition_id)
    if recognition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="识别记录不存在")
    return recognition


@app.post("/api/evaluations/workplace")
def workplace_assessment(
    payload: WorkplacePayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    recognitions = get_recent_recognitions(current_user["id"], limit=12)
    return build_workplace_assessment(recognitions, payload.scenario)


@app.post("/api/companion/respond")
def companion_reply(
    payload: CompanionPayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return {
        "message": build_companion_reply(payload.emotion),
        "user_id": current_user["id"],
    }


@app.get("/api/system/health")
def system_health() -> dict[str, Any]:
    engine = get_inference_engine()
    return {
        "status": "operational",
        "engine": engine.name,
        "version": engine.version,
        "model_loaded": engine.name != "DemoEngine",
        "db_type": DB_TYPE,
        "server_time": utc_now()
    }


@app.post("/api/health/calibrate")
def calibrate(payload: dict[str, Any], current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    save_user_calibration(current_user["id"], payload)
    log_audit_action(current_user["id"], "calibration", "health-profile", "success")
    return {"message": "基准校准已保存，AI 评估严谨度已提升。"}


@app.post("/api/health/assessment")
def health_assessment(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    recognitions = get_recent_recognitions(current_user["id"], limit=20)
    calibration = get_user_calibration(current_user["id"])
    engine = get_inference_engine()
    log_audit_action(current_user["id"], "generate", "health-assessment", "success")
    return engine.build_health_assessment(recognitions, calibration)


@app.get("/api/data/export")
def export_data(current_user: dict[str, Any] = Depends(get_current_user)):
    recognitions = get_recent_recognitions(current_user["id"], limit=100)
    import csv
    import io
    from starlette.responses import StreamingResponse
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["时间", "微表情", "置信度", "强度", "持续时长(ms)", "引擎"])
    for item in recognitions:
        writer.writerow([
            item['created_at'],
            item['label'],
            item['confidence'],
            item['intensity'],
            item['duration_ms'],
            item['engine']
        ])
    
    output.seek(0)
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=emotion-export.csv; charset=utf-8-sig"
        }
    )
    return response


@app.get("/api/membership/plans")
def membership_plans() -> list[dict[str, Any]]:
    return [
        {"name": "普通会员", "price": "9.9元/月", "amount": 9.9, "rights": ["每月 10 次报告", "基础陪伴互动", "识别历史存储"]},
        {"name": "高级会员", "price": "29.9元/月", "amount": 29.9, "rights": ["无限报告", "职场测评", "高级数据导出", "定制服务折扣"]},
        {"name": "企业会员", "price": "999元/年", "amount": 999.0, "rights": ["企业导出权限", "批量账号管理", "定制模型评估", "专属支持"]},
    ]


@app.post("/api/membership/purchase")
def purchase_membership(
    payload: PurchasePayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    plan_mapping = {
        "普通会员": ("普通会员", 9.9, 30),
        "basic": ("普通会员", 9.9, 30),
        "高级会员": ("高级会员", 29.9, 30),
        "pro": ("高级会员", 29.9, 30),
        "企业会员": ("企业会员", 999.0, 365),
        "enterprise": ("企业会员", 999.0, 365),
    }
    if payload.plan_name not in plan_mapping:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="会员类型不存在")
    product_type, amount, valid_days = plan_mapping[payload.plan_name]
    order = create_order(current_user["id"], product_type, amount, valid_days=valid_days)
    return {
        "order": order,
        "message": f"{product_type}开通成功。",
    }


@app.post("/api/membership/recharge")
def recharge_membership(
    payload: RechargePayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    result = redeem_recharge_code(current_user["id"], payload.code)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="激活码无效或已被使用")
    return {
        "message": f"成功激活{result['tier']}，增加 {result['added_credits']} 次报告额度，有效期至 {result['expires_at']}",
        "result": result
    }


@app.post("/api/payment/create-intent")
def create_payment_intent(
    payload: PaymentPayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    payment_data = PaymentProcessor.create_payment_intent(
        current_user["id"],
        payload.amount,
        payload.product_type
    )
    return payment_data


@app.post("/api/payment/webhook")
def payment_webhook(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
    result = PaymentProcessor.handle_webhook(request)
    return result


@app.get("/api/payment/config")
def payment_config() -> dict[str, Any]:
    return get_payment_config()


@app.get("/api/orders/history")
def orders_history(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    return get_recent_orders(current_user["id"])


@app.get("/api/courses")
def courses() -> list[dict[str, str]]:
    return [
        {"title": "微表情商业解读课", "type": "课程", "price": "59元", "description": "面向求职者、销售与管理者的高频场景解读训练。"},
        {"title": "情绪管理咨询", "type": "1对1咨询", "price": "199元", "description": "结合识别报告给出个性化表达优化建议。"},
        {"title": "企业沟通工作坊", "type": "企业服务", "price": "定制报价", "description": "面向 HR 与管理团队的团体培训方案。"},
    ]


@app.post("/api/custom-training/request")
def request_custom_training(
    payload: CustomTrainingPayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    request_record = save_custom_training_request(current_user["id"], payload.industry, payload.description)
    return {
        "request": request_record,
        "message": "定制训练需求已提交，商务顾问将跟进评估。",
    }


@app.get("/api/ads/recommendation")
def ads_recommendation(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    overview = get_dashboard_overview(current_user["id"])
    return build_ad_recommendation(overview["dominant_emotion"])


@app.patch("/api/admin/leads/{lead_id}")
def update_lead_status(
    lead_id: int,
    payload: LeadStatusPayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ensure_admin_access(current_user)
    update_custom_training_request_status(lead_id, payload.status)
    log_audit_action(current_user["id"], "update", f"lead:{lead_id}", "success")
    return {"message": "状态已更新"}


@app.get("/api/admin/audit-logs")
def get_audit_logs(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    ensure_admin_access(current_user)
    sql = "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


@app.get("/api/admin/overview")
def admin_overview(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    ensure_admin_access(current_user)
    return get_admin_overview()


@app.get("/api/admin/leads")
def admin_leads(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    ensure_admin_access(current_user)
    return list_custom_training_requests()


@app.post("/api/admin/leads/{request_id}")
def admin_update_lead(
    request_id: int,
    payload: LeadStatusPayload,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ensure_admin_access(current_user)
    updated = update_custom_training_request_status(request_id, payload.status)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="企业线索不存在")
    return updated


# API管理相关端点
@app.post("/api/api-keys/generate")
def generate_api_key(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    # 只允许企业用户生成API密钥
    if current_user["membership_tier"] != "enterprise" and not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有企业用户可以生成API密钥")
    
    api_key = APIManager.generate_api_key(current_user["id"])
    return {
        "api_key": api_key,
        "message": "API密钥生成成功，请妥善保管"
    }


@app.get("/api/api-keys")
def get_api_keys(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    keys = APIManager.get_user_api_keys(current_user["id"])
    return keys


@app.delete("/api/api-keys/{key_id}")
def revoke_api_key(key_id: int, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    success = APIManager.revoke_api_key(key_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API密钥不存在或无权限操作")
    return {"message": "API密钥已成功撤销"}


@app.get("/api/api-usage")
def get_api_usage(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    usage = APIManager.get_api_usage(current_user["id"])
    return usage


# 企业API端点（通过API密钥访问）
@app.post("/api/enterprise/recognize")
def enterprise_recognize(
    payload: RecognitionPayload,
    api_key: str = Header(None, alias="X-API-Key")
) -> dict[str, Any]:
    # 验证API密钥
    key_info = APIManager.validate_api_key(api_key)
    if not key_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的API密钥")
    
    # 记录API调用开始时间
    start_time = time.time()
    
    try:
        # 执行识别
        result = predict_micro_expression(payload.image_data_url)
        
        # 记录API调用
        response_time = time.time() - start_time
        APIManager.log_api_call(key_info["user_id"], "/api/enterprise/recognize", "success", response_time)
        
        return {
            "result": result,
            "api_key_id": key_info["id"]
        }
    except Exception as e:
        # 记录错误
        response_time = time.time() - start_time
        APIManager.log_api_call(key_info["user_id"], "/api/enterprise/recognize", "error", response_time)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 用户分析相关端点
@app.get("/api/analytics/behavior")
def get_behavior_analysis(
    days: int = 30,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    analysis = UserAnalytics.get_user_behavior_analysis(current_user["id"], days=days)
    return analysis


@app.get("/api/analytics/emotion")
def get_emotion_analysis(
    days: int = 30,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    analysis = UserAnalytics.get_emotion_analysis(current_user["id"], days=days)
    return analysis


@app.get("/api/analytics/segmentation")
def get_user_segmentation(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    segmentation = UserAnalytics.get_user_segmentation(current_user["id"])
    return segmentation


@app.get("/api/analytics/churn-risk")
def get_churn_risk(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    risk = UserAnalytics.predict_churn_risk(current_user["id"])
    return risk


# 营销工具相关端点
class CampaignPayload(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    template_id: str = Field(min_length=2, max_length=100)
    segment_criteria: dict[str, Any]
    scheduled_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


@app.post("/api/marketing/campaigns")
def create_campaign(
    payload: CampaignPayload,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    # 只允许管理员创建营销活动
    if not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员可以创建营销活动")
    
    campaign_id = MarketingManager.create_email_campaign(
        payload.name,
        payload.template_id,
        payload.segment_criteria,
        payload.scheduled_at
    )
    
    return {
        "campaign_id": campaign_id,
        "message": "营销活动创建成功"
    }


@app.get("/api/marketing/campaigns")
def get_campaigns(
    status: Optional[str] = None,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> list[dict[str, Any]]:
    # 只允许管理员查看营销活动
    if not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员可以查看营销活动")
    
    campaigns = MarketingManager.get_campaigns(status=status)
    return campaigns


@app.post("/api/marketing/test-email")
def send_test_email(
    email: str = Query(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="测试邮件地址"),
    template_id: str = Query(..., min_length=2, max_length=100, description="邮件模板ID"),
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    # 只允许管理员发送测试邮件
    if not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员可以发送测试邮件")
    
    # 创建临时用户ID（实际应该使用真实用户ID）
    # 这里为了测试，我们使用一个默认值
    test_user_id = 1
    
    success = MarketingManager.send_campaign_email(test_user_id, template_id)
    
    if success:
        return {"message": f"测试邮件已发送到 {email}"}
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="邮件发送失败")


@app.post("/api/marketing/segment-users")
def segment_users(
    criteria: dict[str, Any],
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    # 只允许管理员进行用户分群
    if not current_user["email"].startswith("admin@"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员可以进行用户分群")
    
    user_ids = MarketingManager.segment_users(criteria)
    
    return {
        "user_count": len(user_ids),
        "user_ids": user_ids
    }


# ==================== 心理评估模块 ====================
from backend.psych_assessment import PsychologicalAssessment


class ScaleAnswersPayload(BaseModel):
    answers: dict[str, int] = Field(description="量表答案，key为问题ID，value为1-4分")


@app.get("/api/assessment/scales/{scale_type}")
def get_scale_questions(
    scale_type: str,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """获取心理评估量表问题"""
    scale_type = scale_type.lower()
    if scale_type not in ["sas", "sds", "pss"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的量表类型")
    
    questions = PsychologicalAssessment.get_scale_questions(scale_type)
    
    scale_names = {
        "sas": "焦虑自评量表",
        "sds": "抑郁自评量表",
        "pss": "压力知觉量表"
    }
    
    return {
        "scale_type": scale_type,
        "scale_name": scale_names[scale_type],
        "question_count": len(questions),
        "questions": questions
    }


@app.post("/api/assessment/scales/{scale_type}/submit")
def submit_scale(
    scale_type: str,
    payload: ScaleAnswersPayload,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """提交心理评估量表"""
    scale_type = scale_type.lower()
    
    if scale_type == "sas":
        result = PsychologicalAssessment.calculate_sas_score(payload.answers)
    elif scale_type == "sds":
        result = PsychologicalAssessment.calculate_sds_score(payload.answers)
    elif scale_type == "pss":
        result = PsychologicalAssessment.calculate_pss_score(payload.answers)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的量表类型")
    
    return result


@app.post("/api/assessment/comprehensive")
def comprehensive_assessment(
    sas_answers: dict[str, int] = Body(...),
    sds_answers: dict[str, int] = Body(...),
    pss_answers: dict[str, int] = Body(...),
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """综合心理健康评估"""
    sas_result = PsychologicalAssessment.calculate_sas_score(sas_answers)
    sds_result = PsychologicalAssessment.calculate_sds_score(sds_answers)
    pss_result = PsychologicalAssessment.calculate_pss_score(pss_answers)
    
    return PsychologicalAssessment.calculate_comprehensive_score(sas_result, sds_result, pss_result)


# ==================== 视频流分析模块 ====================
from backend.video_analysis import video_analyzer


class VideoFramePayload(BaseModel):
    frame_base64: str = Field(description="视频帧的Base64编码")
    timestamp: float = Field(description="帧时间戳")


@app.post("/api/video/create-session")
def create_video_session(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """创建视频分析会话"""
    session_id = video_analyzer.create_session(current_user["id"])
    return {"session_id": session_id}


@app.post("/api/video/process-frame/{session_id}")
def process_video_frame(
    session_id: str,
    payload: VideoFramePayload,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """处理视频帧"""
    try:
        result = video_analyzer.process_frame(session_id, payload.frame_base64, payload.timestamp)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/video/session/{session_id}")
def get_session_summary(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """获取会话摘要"""
    try:
        summary = video_analyzer.get_session_summary(session_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/video/live/{session_id}")
def get_live_emotion(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """获取实时情绪状态"""
    try:
        live_state = video_analyzer.get_live_emotion(session_id)
        return live_state
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.delete("/api/video/session/{session_id}")
def close_video_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """关闭视频会话"""
    try:
        summary = video_analyzer.close_session(session_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== 生理指标模块 ====================
from backend.biometrics import BiometricIntegrator


class BiometricPayload(BaseModel):
    emotion: str = Field(description="情绪标签")
    intensity: float = Field(ge=0, le=1, description="情绪强度")
    base_hr: int = Field(default=72, description="基础心率")


@app.post("/api/biometrics/simulate")
def simulate_biometrics(
    payload: BiometricPayload,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """模拟生理指标"""
    result = BiometricIntegrator.simulate_biometrics(
        payload.emotion,
        payload.intensity,
        payload.base_hr
    )
    return result


@app.post("/api/biometrics/analyze-sequence")
def analyze_biometric_sequence(
    biometric_data: list[dict[str, Any]] = Body(...),
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """分析生理指标序列"""
    result = BiometricIntegrator.analyze_biometric_sequence(biometric_data)
    return result


@app.post("/api/biometrics/integrate")
def integrate_biometrics_with_emotion(
    emotion_result: dict[str, Any] = Body(...),
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """整合情绪识别与生理指标"""
    emotion = emotion_result.get("label", "平静")
    intensity = emotion_result.get("intensity", 0.0)
    
    biometrics = BiometricIntegrator.simulate_biometrics(emotion, intensity)
    
    return {
        "emotion_result": emotion_result,
        "biometric_data": biometrics,
        "combined_analysis": {
            "stress_level": biometrics["stress_level"],
            "overall_status": biometrics["blood_pressure"]["status"],
            "recommendation": BiometricIntegrator._get_health_advice(biometrics)
        }
    }


# ==================== 健康指标端点 ====================
@app.get("/api/health/biometrics")
def get_health_biometrics(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """获取用户健康指标"""
    recognitions = get_recent_recognitions(current_user["id"], limit=5)
    
    # 使用最近的情绪识别结果来生成生理指标
    if recognitions:
        latest_recognition = recognitions[0]
        emotion = latest_recognition["label"]
        intensity = latest_recognition["intensity"] / 100.0
    else:
        emotion = "平静"
        intensity = 0.3
    
    biometrics = BiometricIntegrator.simulate_biometrics(emotion, intensity)
    
    return {
        "heart_rate": biometrics["heart_rate"],
        "heart_rate_status": biometrics["heart_rate_status"],
        "hrv": biometrics["hrv"],
        "hrv_status": biometrics["hrv_status"],
        "breathing_rate": biometrics["breathing_rate"],
        "stress_percentage": biometrics["stress_level"],
        "health_advice": BiometricIntegrator._get_health_advice(biometrics)
    }


# ==================== 情绪日记模块 ====================
class MoodEntryPayload(BaseModel):
    mood: int = Field(ge=1, le=5, description="1-5级心情评分")
    note: str = Field(max_length=500, description="心情描述")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="日期")


@app.post("/api/mood/save")
def save_mood_entry(
    payload: MoodEntryPayload,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """保存心情记录"""
    # 模拟保存到数据库
    log_audit_action(current_user["id"], "save", "mood-entry", "success")
    return {
        "message": "心情记录已保存",
        "entry": {
            "user_id": current_user["id"],
            "mood": payload.mood,
            "note": payload.note,
            "date": payload.date,
            "created_at": utc_now()
        }
    }


@app.get("/api/mood/history")
def get_mood_history(
    days: int = 30,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """获取心情历史记录"""
    # 生成模拟数据
    import random
    records = []
    today = utc_now().split('T')[0]
    
    for i in range(min(days, 14)):
        date_parts = today.split('-')
        date = f"{date_parts[0]}-{date_parts[1]}-{str(int(date_parts[2]) - i).zfill(2)}"
        records.append({
            "date": date,
            "mood": random.randint(1, 5),
            "note": "" if random.random() > 0.3 else "今日心情记录"
        })
    
    return {"records": records}


# ==================== 专家咨询模块 ====================
class ConsultationPayload(BaseModel):
    type: str = Field(min_length=2, max_length=50, description="咨询类型")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="预约日期")


class AnonymousConsultPayload(BaseModel):
    message: str = Field(min_length=10, max_length=500, description="咨询内容")


@app.post("/api/consultation/book")
def book_consultation(
    payload: ConsultationPayload,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """预约专家咨询"""
    counselors = ["李医生", "王医生", "张医生", "陈医生"]
    import random
    counselor_name = random.choice(counselors)
    
    log_audit_action(current_user["id"], "book", "consultation", "success")
    
    return {
        "message": "预约成功",
        "appointment": {
            "type": payload.type,
            "scheduled_date": payload.date,
            "counselor_name": counselor_name,
            "status": "pending",
            "created_at": utc_now()
        }
    }


@app.post("/api/consultation/anonymous")
def anonymous_consultation(
    payload: AnonymousConsultPayload
) -> dict[str, Any]:
    """匿名咨询"""
    responses = [
        "感谢您的分享。您提到的情况很常见，很多人都会经历类似的困扰。建议您尝试：1）每天留出15分钟进行深呼吸练习；2）与信任的朋友或家人沟通；3）如果持续感到困扰，建议寻求专业心理咨询。请记住，您不是一个人在面对这些问题。",
        "我理解您现在可能感到很不容易。情绪的起伏是正常的，重要的是如何学会与它们相处。您可以尝试写情绪日记，记录每天的感受，这有助于更好地了解自己的情绪模式。同时，保持规律的作息和适度的运动也很重要。",
        "您的感受是真实且有意义的。面对压力和挑战时，感到焦虑或低落是正常的反应。建议您关注当下，尝试正念练习，帮助自己从纷乱的思绪中抽离出来。如果需要，随时可以再次与我交流。",
        "听到您的困扰，我感到很关心。请记住，寻求帮助不是软弱，而是勇敢的表现。您可以考虑与专业咨询师谈谈，他们能提供更具针对性的支持和指导。在此之前，试着对自己多一些宽容和理解。",
        "情绪就像天气一样，有晴天也有雨天。您现在可能正经历一段困难时期，但请相信这只是暂时的。试着做一些能让自己感到平静的事情，比如听音乐、散步或做一些深呼吸。照顾好自己最重要。"
    ]
    
    import random
    response = random.choice(responses)
    
    return {
        "response": response,
        "anonymous": True,
        "timestamp": utc_now()
    }


# ==================== 简化的评估端点（适配前端） ====================
@app.post("/api/assessment/{scale_type}")
def quick_assessment(
    scale_type: str,
    payload: ScaleAnswersPayload,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """简化的量表评估端点"""
    scale_type = scale_type.lower()
    
    if scale_type == "sas":
        result = PsychologicalAssessment.calculate_sas_score(payload.answers)
    elif scale_type == "sds":
        result = PsychologicalAssessment.calculate_sds_score(payload.answers)
    elif scale_type == "pss":
        result = PsychologicalAssessment.calculate_pss_score(payload.answers)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的量表类型")
    
    return result


# ==================== 视频流端点（适配前端） ====================
class LiveFramePayload(BaseModel):
    session_id: str = Field(description="会话ID")
    frame_base64: str = Field(description="视频帧Base64")
    timestamp: float = Field(description="时间戳")


@app.post("/api/video/process-frame")
def process_frame_simple(
    payload: LiveFramePayload,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """处理视频帧（简化版本）"""
    try:
        result = video_analyzer.process_frame(payload.session_id, payload.frame_base64, payload.timestamp)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/video/session-summary/{session_id}")
def get_session_summary_simple(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """获取会话摘要（简化版本）"""
    try:
        summary = video_analyzer.get_session_summary(session_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
