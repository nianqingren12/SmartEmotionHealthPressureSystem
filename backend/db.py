from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generator, Protocol, Union

import pymysql
import redis


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "app.db"

# 数据库配置
DB_TYPE = os.getenv("DB_TYPE", "sqlite") # 'sqlite' or 'mysql'
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "rootpassword")
MYSQL_DB = os.getenv("MYSQL_DB", "micro_expression")

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


class ConnectionProtocol(Protocol):
    def cursor(self) -> Any: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def get_connection() -> Any:
    if DB_TYPE == "mysql":
        conn = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        return conn
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        return connection


def get_redis_client():
    try:
        return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    except Exception:
        return None


def init_db() -> None:
    # 初始化API相关表
    try:
        from backend.api_management import init_api_tables
        init_api_tables()
    except ImportError:
        pass
    
    # 初始化营销相关表
    try:
        from backend.marketing import init_marketing_tables
        init_marketing_tables()
    except ImportError:
        pass
    
    # SQL 脚本兼容性处理
    scripts = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            membership_tier VARCHAR(50) NOT NULL DEFAULT 'free',
            membership_expires_at DATETIME,
            report_credits INTEGER NOT NULL DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS recognitions (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            label VARCHAR(50) NOT NULL,
            confidence FLOAT NOT NULL,
            intensity FLOAT NOT NULL,
            duration_ms INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            report_type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            summary TEXT NOT NULL,
            details_json TEXT NOT NULL,
            paid TINYINT NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            order_no VARCHAR(100) NOT NULL,
            product_type VARCHAR(100) NOT NULL,
            amount FLOAT NOT NULL,
            status VARCHAR(50) NOT NULL,
            created_at DATETIME NOT NULL,
            valid_until DATETIME
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS custom_training_requests (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            industry VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            status VARCHAR(50) NOT NULL,
            created_at DATETIME NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS recharge_codes (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            code VARCHAR(100) UNIQUE NOT NULL,
            membership_tier VARCHAR(50) NOT NULL,
            valid_days INTEGER NOT NULL,
            report_credits INTEGER NOT NULL,
            is_used TINYINT NOT NULL DEFAULT 0,
            used_by_user_id INTEGER,
            used_at DATETIME,
            created_at DATETIME NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER,
            action VARCHAR(100) NOT NULL,
            resource VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL,
            ip_address VARCHAR(50),
            created_at DATETIME NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            calibration_json TEXT,
            updated_at DATETIME NOT NULL
        )
        """
    ]

    if DB_TYPE == "sqlite":
        scripts = [s.replace("AUTO_INCREMENT", "AUTOINCREMENT").replace("DATETIME", "TEXT").replace("TINYINT", "INTEGER") for s in scripts]

    with get_connection() as conn:
        cursor = conn.cursor()
        for script in scripts:
            cursor.execute(script)
        
        check_sql = "SELECT COUNT(*) as count FROM recharge_codes" if DB_TYPE == "mysql" else "SELECT COUNT(*) FROM recharge_codes"
        cursor.execute(check_sql)
        row = cursor.fetchone()
        count = row["count"] if DB_TYPE == "mysql" else row[0]
        
        if count == 0:
            from backend.config import config
            codes = []
            for entry in config.activation_codes.split(","):
                parts = entry.strip().split(":")
                if len(parts) == 4:
                    codes.append((parts[0], parts[1], int(parts[2]), int(parts[3]), utc_now()))
            if codes:
                insert_sql = "INSERT INTO recharge_codes (code, membership_tier, valid_days, report_credits, created_at) VALUES (%s, %s, %s, %s, %s)" if DB_TYPE == "mysql" else "INSERT INTO recharge_codes (code, membership_tier, valid_days, report_credits, created_at) VALUES (?, ?, ?, ?, ?)"
                cursor.executemany(insert_sql, codes)
        conn.commit()


def create_user(email: str, password_hash: str) -> dict[str, Any]:
    now = utc_now()
    sql = "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (email, password_hash, now))
        user_id = cursor.lastrowid
        conn.commit()
        return get_user_by_id(user_id)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    sql = "SELECT * FROM users WHERE email = ?"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    sql = "SELECT * FROM users WHERE id = ?"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def save_recognition(user_id: int, source_type: str, result: dict[str, Any]) -> dict[str, Any]:
    payload_json = json.dumps(result, ensure_ascii=False)
    now = utc_now()
    sql = "INSERT INTO recognitions (user_id, created_at, source_type, label, confidence, intensity, duration_ms, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, now, source_type, result["label"], result["confidence"], result["intensity"], result["duration_ms"], payload_json))
        rec_id = cursor.lastrowid
        conn.commit()
        return {"id": rec_id, "created_at": now, **result}


def get_recent_recognitions(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    sql = "SELECT * FROM recognitions WHERE user_id = ? ORDER BY id DESC LIMIT ?"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, limit))
        rows = cursor.fetchall()
        results = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            results.append({"id": row["id"], "created_at": str(row["created_at"]), **payload})
        return results


def create_report(user_id: int, report_type: str, title: str, summary: str, details: dict[str, Any], paid: bool) -> dict[str, Any]:
    now = utc_now()
    sql = "INSERT INTO reports (user_id, created_at, report_type, title, summary, details_json, paid) VALUES (?, ?, ?, ?, ?, ?, ?)"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, now, report_type, title, summary, json.dumps(details, ensure_ascii=False), int(paid)))
        report_id = cursor.lastrowid
        conn.commit()
        return {"id": report_id, "created_at": now, "report_type": report_type, "title": title, "summary": summary, "details": details, "paid": paid}


def get_recent_reports(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    sql = "SELECT * FROM reports WHERE user_id = ? ORDER BY id DESC LIMIT ?"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, limit))
        rows = cursor.fetchall()
        return [{"id": row["id"], "created_at": str(row["created_at"]), "report_type": row["report_type"], "title": row["title"], "summary": row["summary"], "details": json.loads(row["details_json"]), "paid": bool(row["paid"])} for row in rows]


def log_audit_action(user_id: int | None, action: str, resource: str, status: str = "success", ip: str = "127.0.0.1") -> None:
    now = utc_now()
    sql = "INSERT INTO audit_logs (user_id, action, resource, status, ip_address, created_at) VALUES (?, ?, ?, ?, ?, ?)"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, action, resource, status, ip, now))
        conn.commit()


def save_user_calibration(user_id: int, calibration_data: dict[str, Any]) -> None:
    now = utc_now()
    cal_json = json.dumps(calibration_data)
    # SQLite uses INSERT OR REPLACE, MySQL uses ON DUPLICATE KEY UPDATE
    if DB_TYPE == "mysql":
        sql = "INSERT INTO user_settings (user_id, calibration_json, updated_at) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE calibration_json=%s, updated_at=%s"
        args = (user_id, cal_json, now, cal_json, now)
    else:
        sql = "INSERT OR REPLACE INTO user_settings (user_id, calibration_json, updated_at) VALUES (?, ?, ?)"
        args = (user_id, cal_json, now)
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, args)
        conn.commit()


def get_user_calibration(user_id: int) -> dict[str, Any] | None:
    sql = "SELECT calibration_json FROM user_settings WHERE user_id = ?"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id,))
        row = cursor.fetchone()
        if row:
            # row might be a dict or a tuple depending on DB type
            val = row["calibration_json"] if isinstance(row, dict) else row[0]
            return json.loads(val)
        return None


def redeem_recharge_code(user_id: int, code: str) -> dict[str, Any] | None:
    now = utc_now()
    
    # 1. 首先检查数据库中的正式密钥
    select_sql = "SELECT * FROM recharge_codes WHERE code = ? AND is_used = 0"
    if DB_TYPE == "mysql": select_sql = select_sql.replace("?", "%s")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(select_sql, (code,))
        row = cursor.fetchone()
        
        if row:
            # 更新正式密钥为已使用
            update_sql = "UPDATE recharge_codes SET is_used = 1, used_by_user_id = ?, used_at = ? WHERE id = ?"
            if DB_TYPE == "mysql": update_sql = update_sql.replace("?", "%s")
            cursor.execute(update_sql, (user_id, now, row["id"]))
            
            # 提升用户等级
            user_update_sql = "UPDATE users SET membership_tier = ?, report_credits = report_credits + ? WHERE id = ?"
            if DB_TYPE == "mysql": user_update_sql = user_update_sql.replace("?", "%s")
            cursor.execute(user_update_sql, (row["membership_tier"], row["report_credits"], user_id))
            
            conn.commit()
            log_audit_action(user_id, "redeem", f"code:{code}", "success")
            return {"tier": row["membership_tier"], "credits": row["report_credits"]}

    # 2. 增强型模拟：商业演示专用测试密钥校验
    # 规则：以 ME- 开头，后面跟着 12 位字符，且最后 4 位数字之和等于 10 (例如 ME-TEST-1234000)
    # 这里为了演示方便，只要是 ME- 开头且长度 > 10 的，我们也给一个基础会员，但记录在审计日志中
    if code.startswith("ME-") and len(code) >= 10:
        tier = "pro" if "PRO" in code.upper() else "basic"
        credits = 50 if tier == "pro" else 10
        
        with get_connection() as conn:
            cursor = conn.cursor()
            user_update_sql = "UPDATE users SET membership_tier = ?, report_credits = report_credits + ? WHERE id = ?"
            if DB_TYPE == "mysql": user_update_sql = user_update_sql.replace("?", "%s")
            cursor.execute(user_update_sql, (tier, credits, user_id))
            conn.commit()
            
        log_audit_action(user_id, "redeem_test_code", f"code:{code}", "success_demo")
        return {"tier": tier, "credits": credits, "is_demo": True}

    log_audit_action(user_id, "redeem", f"code:{code}", "failed_invalid")
    return None


def get_dashboard_overview(user_id: int) -> dict[str, Any]:
    recognitions = get_recent_recognitions(user_id, limit=50)
    reports = get_recent_reports(user_id, limit=10)
    user = get_user_by_id(user_id)
    emotion_distribution: dict[str, int] = {}
    for item in recognitions:
        emotion_distribution[item["label"]] = emotion_distribution.get(item["label"], 0) + 1
    dominant_emotion = max(emotion_distribution, key=emotion_distribution.get, default="平静")
    return {
        "membership_tier": user["membership_tier"] if user else "free",
        "membership_expires_at": str(user["membership_expires_at"]) if user and user["membership_expires_at"] else None,
        "report_credits": user["report_credits"] if user else 0,
        "recognition_count": len(recognitions),
        "report_count": len(reports),
        "dominant_emotion": dominant_emotion,
        "emotion_distribution": emotion_distribution,
    }


def get_recognition_by_id(user_id: int, recognition_id: int) -> dict[str, Any] | None:
    sql = "SELECT * FROM recognitions WHERE user_id = ? AND id = ?"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, recognition_id))
        row = cursor.fetchone()
        if row is None: return None
        return {"id": row["id"], "created_at": str(row["created_at"]), "source_type": row["source_type"], **json.loads(row["payload_json"])}


def get_report_by_id(user_id: int, report_id: int) -> dict[str, Any] | None:
    sql = "SELECT * FROM reports WHERE user_id = ? AND id = ?"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, report_id))
        row = cursor.fetchone()
        if row is None: return None
        return {"id": row["id"], "created_at": str(row["created_at"]), "report_type": row["report_type"], "title": row["title"], "summary": row["summary"], "details": json.loads(row["details_json"]), "paid": bool(row["paid"])}


def consume_report_credit(user_id: int) -> bool:
    select_sql = "SELECT * FROM users WHERE id = ?"
    update_sql = "UPDATE users SET report_credits = report_credits - 1 WHERE id = ?"
    if DB_TYPE == "mysql":
        select_sql, update_sql = [s.replace("?", "%s") for s in [select_sql, update_sql]]
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(select_sql, (user_id,))
        user = cursor.fetchone()
        if user is None: return False
        expires_at = str(user["membership_expires_at"]) if user["membership_expires_at"] else None
        if user["membership_tier"] != "free" and (not expires_at or expires_at > utc_now()): return True
        if user["report_credits"] <= 0: return False
        cursor.execute(update_sql, (user_id,))
        conn.commit()
        return True


def create_order(user_id: int, product_type: str, amount: float, valid_days: int | None = None) -> dict[str, Any]:
    now = utc_now()
    valid_until = (datetime.utcnow() + timedelta(days=valid_days)).isoformat(timespec="seconds") if valid_days else None
    order_no = f"ME-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{user_id}"
    sql_order = "INSERT INTO orders (user_id, order_no, product_type, amount, status, created_at, valid_until) VALUES (?, ?, ?, ?, ?, ?, ?)"
    sql_user = "UPDATE users SET membership_tier = ?, membership_expires_at = ?, report_credits = report_credits + 10 WHERE id = ?"
    if DB_TYPE == "mysql":
        sql_order, sql_user = [s.replace("?", "%s") for s in [sql_order, sql_user]]
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql_order, (user_id, order_no, product_type, amount, "paid", now, valid_until))
        order_id = cursor.lastrowid
        if valid_days:
            tier = "enterprise" if "企业" in product_type else "pro" if "高级" in product_type else "basic"
            cursor.execute(sql_user, (tier, valid_until, user_id))
        conn.commit()
        return {"id": order_id, "order_no": order_no, "product_type": product_type, "amount": amount, "status": "paid", "valid_until": valid_until}


def get_recent_orders(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    sql = "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, limit))
        rows = cursor.fetchall()
        return [{"id": row["id"], "order_no": row["order_no"], "product_type": row["product_type"], "amount": row["amount"], "status": row["status"], "created_at": str(row["created_at"]), "valid_until": str(row["valid_until"]) if row["valid_until"] else None} for row in rows]


def save_custom_training_request(user_id: int, industry: str, description: str) -> dict[str, Any]:
    now = utc_now()
    sql = "INSERT INTO custom_training_requests (user_id, industry, description, status, created_at) VALUES (?, ?, ?, ?, ?)"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, industry, description, "待评估", now))
        req_id = cursor.lastrowid
        conn.commit()
        return {"id": req_id, "industry": industry, "description": description, "status": "待评估", "created_at": now}


def list_custom_training_requests(limit: int = 50) -> list[dict[str, Any]]:
    sql = "SELECT r.*, u.email AS user_email FROM custom_training_requests r JOIN users u ON u.id = r.user_id ORDER BY r.id DESC LIMIT ?"
    if DB_TYPE == "mysql": sql = sql.replace("?", "%s")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        return [{"id": row["id"], "user_id": row["user_id"], "user_email": row["user_email"], "industry": row["industry"], "description": row["description"], "status": row["status"], "created_at": str(row["created_at"])} for row in rows]


def update_custom_training_request_status(request_id: int, status: str) -> dict[str, Any] | None:
    sql_upd = "UPDATE custom_training_requests SET status = ? WHERE id = ?"
    sql_sel = "SELECT * FROM custom_training_requests WHERE id = ?"
    if DB_TYPE == "mysql":
        sql_upd, sql_sel = [s.replace("?", "%s") for s in [sql_upd, sql_sel]]
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql_upd, (status, request_id))
        if cursor.rowcount == 0: return None
        conn.commit()
        cursor.execute(sql_sel, (request_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_admin_overview() -> dict[str, Any]:
    valid_tables = {"users", "recognitions", "reports", "orders", "custom_training_requests"}
    with get_connection() as conn:
        cursor = conn.cursor()
        def count_table(table):
            if table not in valid_tables:
                return 0
            sql = "SELECT COUNT(*) as count FROM {}".format(table) if DB_TYPE == "mysql" else "SELECT COUNT(*) FROM {}".format(table)
            cursor.execute(sql)
            row = cursor.fetchone()
            return row["count"] if DB_TYPE == "mysql" else row[0]
        return {"user_count": count_table("users"), "recognition_count": count_table("recognitions"), "report_count": count_table("reports"), "order_count": count_table("orders"), "lead_count": count_table("custom_training_requests")}
