"""SQLite persistence, password hashing, RBAC helpers, and audit trail for LeadLens AI.

This is an assessment-grade single-instance prototype. For multi-instance production,
replace SQLite with managed PostgreSQL and add an enterprise identity provider.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = os.getenv("LEADLENS_DB", str(Path("data") / "leadlens.db"))
ROLES = ("Admin", "Sales", "Analyst")
STATUSES = (
    "New", "Contacted", "Discovery Scheduled", "Qualified", "Proposal", "Won", "Lost", "On Hold"
)
PRIORITIES = ("High", "Medium", "Low")
PBKDF2_ITERATIONS = 310_000


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    db = str(db_path or DEFAULT_DB)
    if db != ":memory:":
        Path(db).expanduser().parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("Password must be at least 12 characters long.")
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    try:
        _salt, candidate = hash_password(password, salt_hex)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, digest_hex)


def init_db(db_path: str | Path | None = None, demo_mode: bool | None = None) -> None:
    if demo_mode is None:
        demo_mode = os.getenv("LEADLENS_DEMO_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}
    with _connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('Admin','Sales','Analyst')),
                salt_hex TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                company TEXT NOT NULL DEFAULT '',
                contact_email TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'Website inquiry',
                inquiry TEXT NOT NULL,
                category TEXT NOT NULL,
                score INTEGER NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'New',
                assigned_to TEXT NOT NULL DEFAULT '',
                follow_up_date TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                analysis_json TEXT NOT NULL,
                duplicate_key TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
            CREATE INDEX IF NOT EXISTS idx_leads_category ON leads(category);
            CREATE INDEX IF NOT EXISTS idx_leads_duplicate_key ON leads(duplicate_key);
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                lead_id INTEGER,
                detail TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE SET NULL
            );
            """
        )
        if not demo_mode:
            # Never leave the publicly documented demo credentials active in non-demo mode.
            conn.execute("DELETE FROM users WHERE lower(username) IN ('demo_admin', 'demo_sales', 'demo_analyst')")
        count = int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        if demo_mode and count == 0:
            demo_accounts = [
                ("demo_admin", "Demo Administrator", "Admin", "AdminDemo!2026"),
                ("demo_sales", "Demo Sales", "Sales", "SalesDemo!2026"),
                ("demo_analyst", "Demo Analyst", "Analyst", "AnalystDemo!2026"),
            ]
            for username, display_name, role, password in demo_accounts:
                salt, digest = hash_password(password)
                conn.execute(
                    "INSERT INTO users(username,display_name,role,salt_hex,password_hash,is_active,created_at) VALUES(?,?,?,?,?,1,?)",
                    (username, display_name, role, salt, digest, now_iso()),
                )
        conn.commit()


def user_count(db_path: str | Path | None = None) -> int:
    init_db(db_path)
    with _connect(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])


def get_user(username: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT id,username,display_name,role,salt_hex,password_hash,is_active,created_at,last_login FROM users WHERE username=? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
        return dict(row) if row else None


def authenticate(username: str, password: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    user = get_user(username, db_path)
    if not user or not user["is_active"]:
        # Make username enumeration less informative at the UI level.
        return None
    if not verify_password(password, user["salt_hex"], user["password_hash"]):
        return None
    with _connect(db_path) as conn:
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (now_iso(), user["id"]))
        conn.commit()
    return {k: user[k] for k in ("id", "username", "display_name", "role")}


def create_user(username: str, display_name: str, role: str, password: str, actor: str = "system", db_path: str | Path | None = None) -> int:
    username = username.strip()
    display_name = display_name.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        raise ValueError("Username must be 3–32 characters and contain only letters, numbers, dot, underscore, or hyphen.")
    if not display_name or len(display_name) > 80:
        raise ValueError("Display name is required and must be 80 characters or fewer.")
    if role not in ROLES:
        raise ValueError("Select a valid role.")
    if not is_demo_mode() and username.lower() in {"demo_admin", "demo_sales", "demo_analyst"}:
        raise ValueError("That username is reserved for the public demo accounts.")
    salt, digest = hash_password(password)
    init_db(db_path)
    try:
        with _connect(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO users(username,display_name,role,salt_hex,password_hash,is_active,created_at) VALUES(?,?,?,?,?,1,?)",
                (username, display_name, role, salt, digest, now_iso()),
            )
            conn.execute(
                "INSERT INTO audit_events(created_at,actor,action,detail) VALUES(?,?,?,?)",
                (now_iso(), actor, "USER_CREATED", json.dumps({"username": username, "role": role})),
            )
            conn.commit()
            return int(cur.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError("That username already exists.") from exc


def update_user_password(username: str, password: str, actor: str | None = None, db_path: str | Path | None = None) -> None:
    salt, digest = hash_password(password)
    init_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute("UPDATE users SET salt_hex=?,password_hash=? WHERE username=? COLLATE NOCASE", (salt, digest, username.strip()))
        if cur.rowcount != 1:
            raise ValueError("User not found.")
        if actor:
            conn.execute("INSERT INTO audit_events(created_at,actor,action,detail) VALUES(?,?,?,?)", (now_iso(), actor, "PASSWORD_RESET", json.dumps({"username": username})))
        conn.commit()


def change_user_status(username: str, is_active: bool, actor: str, db_path: str | Path | None = None) -> None:
    init_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute("UPDATE users SET is_active=? WHERE username=? COLLATE NOCASE", (int(is_active), username.strip()))
        if cur.rowcount != 1:
            raise ValueError("User not found.")
        conn.execute("INSERT INTO audit_events(created_at,actor,action,detail) VALUES(?,?,?,?)", (now_iso(), actor, "USER_ACTIVATED" if is_active else "USER_DEACTIVATED", json.dumps({"username": username})))
        conn.commit()


def list_users(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    with _connect(db_path) as conn:
        return [dict(r) for r in conn.execute("SELECT id,username,display_name,role,is_active,created_at,last_login FROM users ORDER BY username COLLATE NOCASE").fetchall()]


def duplicate_key(company: str, contact_email: str, inquiry: str) -> str:
    email = contact_email.strip().lower()
    org = re.sub(r"[^a-z0-9]+", " ", company.lower()).strip()
    msg = re.sub(r"\W+", " ", inquiry.lower()).strip()
    # The exact normalized inquiry prevents obvious re-submissions; don't claim semantic deduplication.
    raw = f"email:{email}|company:{org}|inquiry:{msg}" if email else f"company:{org}|inquiry:{msg}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def find_duplicates(company: str, contact_email: str, inquiry: str, db_path: str | Path | None = None, exclude_id: int | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    key = duplicate_key(company, contact_email, inquiry)
    sql = "SELECT id,created_at,company,contact_email,category,status FROM leads WHERE duplicate_key=?"
    params: list[Any] = [key]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    sql += " ORDER BY id DESC LIMIT 5"
    with _connect(db_path) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def create_lead(inquiry: str, result: dict[str, Any], company: str = "", contact_email: str = "", source: str = "Website inquiry", actor: str = "system", assigned_to: str = "", follow_up_date: str = "", db_path: str | Path | None = None) -> int:
    company, contact_email, source = company.strip(), contact_email.strip(), source.strip() or "Website inquiry"
    if len(company) > 120 or len(contact_email) > 254 or len(source) > 80:
        raise ValueError("Company, contact email, or source exceeds the allowed length.")
    if contact_email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact_email):
        raise ValueError("Enter a valid email address or leave it blank.")
    if follow_up_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", follow_up_date):
        raise ValueError("Follow-up date must use YYYY-MM-DD format.")
    category = result.get("fields", {}).get("service_category", "Unclear / discovery needed")
    score = int(result.get("score", {}).get("score", 0))
    priority = result.get("score", {}).get("priority", "Low")
    if priority not in PRIORITIES or not 0 <= score <= 100:
        raise ValueError("Invalid scoring output.")
    key = duplicate_key(company, contact_email, inquiry)
    stamp = now_iso()
    init_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO leads(created_at,updated_at,created_by,company,contact_email,source,inquiry,category,score,priority,status,assigned_to,follow_up_date,analysis_json,duplicate_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (stamp, stamp, actor, company, contact_email, source[:80], inquiry[:6000], category, score, priority, "New", assigned_to, follow_up_date, json.dumps(result, ensure_ascii=False), key),
        )
        lead_id = int(cur.lastrowid)
        conn.execute("INSERT INTO audit_events(created_at,actor,action,lead_id,detail) VALUES(?,?,?,?,?)", (stamp, actor, "LEAD_CREATED", lead_id, json.dumps({"category": category, "score": score, "source": source})))
        conn.commit()
        return lead_id


def list_leads(limit: int = 1000, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    limit = max(1, min(int(limit), 5000))
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT id,created_at,updated_at,created_by,company,contact_email,source,inquiry,category,score,priority,status,assigned_to,follow_up_date,notes,analysis_json FROM leads ORDER BY id DESC LIMIT {limit}"
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["analysis"] = json.loads(item.pop("analysis_json"))
            except (json.JSONDecodeError, TypeError):
                item["analysis"] = {}
            result.append(item)
        return result


def get_lead(lead_id: int, db_path: str | Path | None = None) -> dict[str, Any] | None:
    return next((x for x in list_leads(limit=5000, db_path=db_path) if x["id"] == int(lead_id)), None)


def update_lead(lead_id: int, actor: str, status: str, assigned_to: str = "", follow_up_date: str = "", notes: str = "", category: str | None = None, db_path: str | Path | None = None) -> None:
    if status not in STATUSES:
        raise ValueError("Invalid pipeline status.")
    if follow_up_date:
        try:
            date.fromisoformat(follow_up_date)
        except ValueError as exc:
            raise ValueError("Invalid follow-up date.") from exc
    if len(notes) > 3000:
        raise ValueError("Notes must be 3,000 characters or fewer.")
    init_db(db_path)
    with _connect(db_path) as conn:
        before = conn.execute("SELECT status,assigned_to,follow_up_date,notes,category FROM leads WHERE id=?", (int(lead_id),)).fetchone()
        if before is None:
            raise ValueError("Lead not found.")
        new_category = category or before["category"]
        conn.execute("UPDATE leads SET updated_at=?,status=?,assigned_to=?,follow_up_date=?,notes=?,category=? WHERE id=?", (now_iso(), status, assigned_to, follow_up_date, notes, new_category, int(lead_id)))
        changed = {k: {"from": before[k], "to": v} for k, v in {"status": status, "assigned_to": assigned_to, "follow_up_date": follow_up_date, "notes": notes, "category": new_category}.items() if before[k] != v}
        if changed:
            conn.execute("INSERT INTO audit_events(created_at,actor,action,lead_id,detail) VALUES(?,?,?,?,?)", (now_iso(), actor, "LEAD_UPDATED", int(lead_id), json.dumps(changed, ensure_ascii=False)))
        conn.commit()


def delete_lead(lead_id: int, actor: str, db_path: str | Path | None = None) -> None:
    init_db(db_path)
    with _connect(db_path) as conn:
        exists = conn.execute("SELECT id FROM leads WHERE id=?", (int(lead_id),)).fetchone()
        if not exists:
            raise ValueError("Lead not found.")
        conn.execute("INSERT INTO audit_events(created_at,actor,action,lead_id,detail) VALUES(?,?,?,?,?)", (now_iso(), actor, "LEAD_DELETED", int(lead_id), "Explicit admin deletion"))
        conn.execute("DELETE FROM leads WHERE id=?", (int(lead_id),))
        conn.commit()


def log_event(actor: str, action: str, detail: str = "", lead_id: int | None = None, db_path: str | Path | None = None) -> None:
    init_db(db_path)
    with _connect(db_path) as conn:
        conn.execute("INSERT INTO audit_events(created_at,actor,action,lead_id,detail) VALUES(?,?,?,?,?)", (now_iso(), actor, action[:80], lead_id, detail[:1000]))
        conn.commit()


def list_events(limit: int = 300, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    limit = max(1, min(int(limit), 2000))
    with _connect(db_path) as conn:
        return [dict(r) for r in conn.execute(f"SELECT id,created_at,actor,action,lead_id,detail FROM audit_events ORDER BY id DESC LIMIT {limit}").fetchall()]


def set_own_password(username: str, current_password: str, new_password: str, db_path: str | Path | None = None) -> None:
    user = get_user(username, db_path)
    if not user or not verify_password(current_password, user["salt_hex"], user["password_hash"]):
        raise ValueError("Current password is incorrect.")
    update_user_password(username, new_password, actor=username, db_path=db_path)


def is_demo_mode() -> bool:
    return os.getenv("LEADLENS_DEMO_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}
