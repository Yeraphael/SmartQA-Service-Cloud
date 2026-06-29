"""SmartQA real-data pipeline.

This module keeps the production data path in one place: source MySQL sync,
ODS->DIM/DWD build, default QC seed data, and lightweight verification helpers.
It intentionally uses batch SQL for the heavy import/build steps because the
source data is append/update oriented and the first version must stay simple
and fast.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import quote_plus
from uuid import uuid4

import pymysql

from app.config.setting import settings
from app.utils.hash_bcrpy_util import PwdUtil

SOURCE_SYSTEM = "qianniu"
DEFAULT_TENANT_ID = 1
DEFAULT_RULE_VERSION = "smartqa-p0-20260625"
DEFAULT_PROMPT_VERSION = "smartqa-p0-prompt-20260625"
DEFAULT_MODEL_NAME = "qwen3.7-plus"
SMARTQA_ALLOWED_TABLES = {
    "alembic_version",
    "platform_menu",
    "platform_tenant",
    "sys_param",
    "sys_role",
    "sys_role_menus",
    "sys_user",
    "sys_user_roles",
    "ods_import_batch",
    "ods_qn_chat_record",
    "ods_qn_shop_record",
    "dim_shop",
    "dim_product",
    "dim_staff",
    "dim_staff_account",
    "dim_customer",
    "dim_customer_identity",
    "dwd_qn_conversation",
    "dwd_qn_message",
    "dwd_customer_staff_relation",
    "qc_rule",
    "qc_prompt_template",
    "qc_rule_version",
    "qc_task",
    "qc_result",
    "qc_issue",
    "qc_issue_evidence",
    "model_call_log",
}
SMARTQA_BULK_TABLES = [
    "ods_import_batch",
    "ods_qn_chat_record",
    "ods_qn_shop_record",
    "dim_shop",
    "dim_product",
    "dim_staff",
    "dim_staff_account",
    "dim_customer",
    "dim_customer_identity",
    "dwd_qn_conversation",
    "dwd_qn_message",
    "dwd_customer_staff_relation",
]
SMARTQA_REQUIRED_PARAMS: dict[str, dict[str, Any]] = {
    "tenant_name": {
        "config_name": "系统名称",
        "config_value": "SmartQA Service Cloud",
        "description": "前端显示的系统名称",
    },
    "tenant_logo": {
        "config_name": "系统Logo",
        "config_value": "",
        "description": "前端显示的系统Logo地址",
    },
    "white_api_list_path": {
        "config_name": "接口白名单",
        "config_value": json.dumps(
            [
                "/api/v1/system/auth/login",
                "/api/v1/system/auth/token/refresh",
                "/api/v1/system/auth/captcha/get",
                "/api/v1/system/auth/logout",
                "/api/v1/system/config/info",
                "/common/health",
                "/common/health/ready",
                "/common/health/live",
                "/metrics",
            ],
            ensure_ascii=False,
        ),
        "description": "无需登录即可访问的接口列表",
    },
    "ip_white_list": {
        "config_name": "访问IP白名单",
        "config_value": "[]",
        "description": "写保护开启时允许写操作的IP列表",
    },
    "ip_black_list": {
        "config_name": "访问IP黑名单",
        "config_value": "[]",
        "description": "禁止访问的IP列表",
    },
    "write_guard_enable": {
        "config_name": "写保护开关",
        "config_value": "false",
        "description": "启用后非白名单IP禁止写操作",
    },
}


def load_env_file(path: str | Path = "env/.env.dev") -> None:
    """Load a local .env file when scripts run outside the FastAPI process."""
    env_path = Path(path)
    if not env_path.is_absolute():
        env_path = Path.cwd() / env_path
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def get_source_config() -> dict[str, Any]:
    return {
        "host": os.getenv("SMARTQA_SOURCE_DB_HOST") or settings.SMARTQA_SOURCE_DB_HOST,
        "port": int(os.getenv("SMARTQA_SOURCE_DB_PORT") or settings.SMARTQA_SOURCE_DB_PORT),
        "user": os.getenv("SMARTQA_SOURCE_DB_USER") or settings.SMARTQA_SOURCE_DB_USER,
        "password": os.getenv("SMARTQA_SOURCE_DB_PASSWORD") or settings.SMARTQA_SOURCE_DB_PASSWORD,
        "database": os.getenv("SMARTQA_SOURCE_DB_NAME") or settings.SMARTQA_SOURCE_DB_NAME,
    }


def get_target_config() -> dict[str, Any]:
    return {
        "host": os.getenv("DATABASE_HOST") or settings.DATABASE_HOST,
        "port": int(os.getenv("DATABASE_PORT") or settings.DATABASE_PORT),
        "user": os.getenv("DATABASE_USER") or settings.DATABASE_USER,
        "password": os.getenv("DATABASE_PASSWORD") or settings.DATABASE_PASSWORD,
        "database": os.getenv("DATABASE_NAME") or settings.DATABASE_NAME,
    }


def get_openai_config() -> dict[str, str]:
    return {
        "api_key": os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY,
        "base_url": os.getenv("OPENAI_BASE_URL") or settings.OPENAI_BASE_URL,
        "model": os.getenv("OPENAI_MODEL") or os.getenv("SMARTQA_ALI_MODEL_NAME") or settings.SMARTQA_ALI_MODEL_NAME or DEFAULT_MODEL_NAME,
    }


def mysql_conn(config: dict[str, Any]) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=config["host"],
        port=int(config.get("port", 3306)),
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=15,
        read_timeout=120,
        write_timeout=120,
    )


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def short_hash(value: str, length: int = 16) -> str:
    return sha256_hex(value)[:length]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def message_fingerprint(record: dict[str, Any]) -> str:
    content = normalize_text(record.get("chat_content")).strip()
    return sha256_hex(
        "|".join(
            [
                normalize_text(record.get("relation_id")),
                normalize_text(record.get("business_id")),
                normalize_text(record.get("chat_time")),
                normalize_text(record.get("chat_target")),
                content,
            ]
        )
    )


def chat_row_hash(record: dict[str, Any]) -> str:
    return sha256_hex(
        "|".join(
            [
                normalize_text(record.get("id")),
                normalize_text(record.get("relation_id")),
                normalize_text(record.get("business_id")),
                normalize_text(record.get("chat_target")),
                normalize_text(record.get("chat_content")),
                normalize_text(record.get("chat_time")),
                normalize_text(record.get("create_time")),
            ]
        )
    )


def shop_row_hash(record: dict[str, Any]) -> str:
    return sha256_hex(
        "|".join(
            [
                normalize_text(record.get("id")),
                normalize_text(record.get("relation_id")),
                normalize_text(record.get("business_id")),
                normalize_text(record.get("shop_name")),
                normalize_text(record.get("product_name")),
                normalize_text(record.get("product_id")),
                normalize_text(record.get("buyer_wangwang")),
                normalize_text(record.get("seller_wangwang")),
                normalize_text(record.get("status")),
                normalize_text(record.get("start_time")),
                normalize_text(record.get("end_time")),
                normalize_text(record.get("chat_content")),
            ]
        )
    )


def chunked(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


class SmartQAPipeline:
    """Operational pipeline used by scripts and HTTP endpoints."""

    def __init__(
        self,
        source_config: dict[str, Any] | None = None,
        target_config: dict[str, Any] | None = None,
        tenant_id: int = DEFAULT_TENANT_ID,
        created_id: int | None = None,
    ) -> None:
        self.source_config = source_config or get_source_config()
        self.target_config = target_config or get_target_config()
        self.tenant_id = tenant_id or DEFAULT_TENANT_ID
        self.created_id = created_id

    def source_exact_counts(self) -> dict[str, Any]:
        with mysql_conn(self.source_config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM qn_chat_record")
                chat_count = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(*) AS c FROM qn_shop_record")
                shop_count = cur.fetchone()["c"]
                cur.execute(
                    """
                    SELECT table_name, table_rows
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                      AND table_name IN ('qn_chat_record', 'qn_shop_record')
                    """
                )
                estimates = {row["table_name"]: row["table_rows"] for row in cur.fetchall()}
                cur.execute("SELECT MIN(chat_time) AS min_chat_time, MAX(chat_time) AS max_chat_time FROM qn_chat_record")
                time_range = cur.fetchone()
        return {
            "chat_count": chat_count,
            "shop_count": shop_count,
            "estimated_chat_rows": estimates.get("qn_chat_record"),
            "estimated_shop_rows": estimates.get("qn_shop_record"),
            **time_range,
        }

    def apply_schema_fixes(self) -> list[str]:
        """Drop unsafe indexes and unused bulk-table UUID columns."""
        actions: list[str] = []
        with mysql_conn(self.target_config) as conn:
            with conn.cursor() as cur:
                for table, unique_name, index_name in [
                    ("ods_qn_chat_record", "uq_ods_qn_chat_fingerprint", "ix_ods_qn_chat_fingerprint"),
                    ("dwd_qn_message", "uq_dwd_qn_message_fingerprint", "ix_dwd_qn_message_fingerprint"),
                ]:
                    cur.execute("SHOW INDEX FROM `{}` WHERE Key_name=%s".format(table), (unique_name,))
                    if cur.fetchall():
                        cur.execute(f"ALTER TABLE `{table}` DROP INDEX `{unique_name}`")
                        actions.append(f"drop {table}.{unique_name}")

                    cur.execute("SHOW INDEX FROM `{}` WHERE Key_name=%s".format(table), (index_name,))
                    if not cur.fetchall():
                        cur.execute(f"CREATE INDEX `{index_name}` ON `{table}` (`source_system`, `message_fingerprint`)")
                        actions.append(f"create {table}.{index_name}")

                for table in SMARTQA_BULK_TABLES:
                    for column in ("uuid", "created_id", "updated_id", "deleted_id"):
                        cur.execute("SHOW COLUMNS FROM `{}` LIKE %s".format(table), (column,))
                        if not cur.fetchone():
                            continue

                        cur.execute(
                            """
                            SELECT constraint_name
                            FROM information_schema.key_column_usage
                            WHERE table_schema = DATABASE()
                              AND table_name = %s
                              AND column_name = %s
                              AND referenced_table_name IS NOT NULL
                            """,
                            (table, column),
                        )
                        for constraint in cur.fetchall():
                            name = constraint.get("constraint_name")
                            if name:
                                cur.execute(f"ALTER TABLE `{table}` DROP FOREIGN KEY `{name}`")
                                actions.append(f"drop {table}.{name}")

                        cur.execute("SHOW INDEX FROM `{}` WHERE Column_name=%s".format(table), (column,))
                        for index in cur.fetchall():
                            key_name = index.get("Key_name")
                            if key_name and key_name != "PRIMARY":
                                cur.execute(f"ALTER TABLE `{table}` DROP INDEX `{key_name}`")
                                actions.append(f"drop {table}.{key_name}")

                        cur.execute(f"ALTER TABLE `{table}` DROP COLUMN `{column}`")
                        actions.append(f"drop {table}.{column}")
            conn.commit()
        return actions

    def full_sync(self, batch_id: str | None = None) -> dict[str, Any]:
        self.apply_schema_fixes()
        batch_id = batch_id or f"batch_qn_fullsync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started = perf_counter()
        now = datetime.now()

        with mysql_conn(self.source_config) as source_conn, mysql_conn(self.target_config) as target_conn:
            try:
                with source_conn.cursor() as source_cur, target_conn.cursor() as target_cur:
                    self._create_batch(target_cur, batch_id, now)

                    source_cur.execute("SELECT * FROM qn_chat_record ORDER BY id")
                    chat_rows = source_cur.fetchall()
                    chat_count = self._upsert_chat_rows(target_cur, batch_id, chat_rows)

                    source_cur.execute("SELECT * FROM qn_shop_record ORDER BY id")
                    shop_rows = source_cur.fetchall()
                    shop_count = self._upsert_shop_rows(target_cur, batch_id, shop_rows)

                    target_cur.execute(
                        """
                        SELECT COUNT(DISTINCT relation_id, business_id) AS c
                        FROM ods_qn_shop_record
                        WHERE source_system=%s AND is_deleted=0
                        """,
                        (SOURCE_SYSTEM,),
                    )
                    conversation_count = target_cur.fetchone()["c"]

                    target_cur.execute(
                        """
                        UPDATE ods_import_batch
                        SET chat_rows=%s, shop_rows=%s, conversation_count=%s,
                            status='success', finished_at=%s, updated_time=%s
                        WHERE batch_id=%s
                        """,
                        (chat_count, shop_count, conversation_count, datetime.now(), datetime.now(), batch_id),
                    )
                target_conn.commit()
            except Exception as exc:
                target_conn.rollback()
                with target_conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE ods_import_batch
                        SET status='failed', error_message=%s, finished_at=%s, updated_time=%s
                        WHERE batch_id=%s
                        """,
                        (str(exc)[:60000], datetime.now(), datetime.now(), batch_id),
                    )
                target_conn.commit()
                raise

        return {
            "batch_id": batch_id,
            "chat_rows": chat_count,
            "shop_rows": shop_count,
            "conversation_count": conversation_count,
            "elapsed_seconds": round(perf_counter() - started, 3),
        }

    def rebuild_warehouse(self, batch_id: str | None = None, truncate_dwd: bool = False) -> dict[str, Any]:
        self.apply_schema_fixes()
        started = perf_counter()
        with mysql_conn(self.target_config) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SET SESSION group_concat_max_len=1048576")
                    if truncate_dwd:
                        self._clear_warehouse(cur)
                    batch_id = batch_id or self._latest_success_batch_id(cur)

                    self._build_shops(cur)
                    self._build_products(cur)
                    self._build_staff(cur)
                    self._build_customers(cur)
                    self._build_conversations(cur)
                    self._build_messages(cur)
                    self._refresh_conversation_metrics(cur)
                    self._build_customer_staff_relations(cur)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        counts = self.target_counts()
        counts.update({"batch_id": batch_id, "elapsed_seconds": round(perf_counter() - started, 3)})
        return counts

    def seed_defaults(self) -> dict[str, Any]:
        with mysql_conn(self.target_config) as conn:
            try:
                with conn.cursor() as cur:
                    dropped_tables = self._drop_retired_template_tables(cur)
                    cleaned_params = self._cleanup_retired_params(cur)
                    tenant_result = self._ensure_tenant(cur)
                    boss_user_id = self._ensure_boss(cur)
                    role_ids = self._ensure_roles(cur)
                    self._bind_user_role(cur, boss_user_id, role_ids["boss"])
                    menu_result = self._ensure_smartqa_menus(cur)
                    deleted_menus = self._cleanup_template_menus(cur, menu_result["all_menu_ids"])
                    self._bind_role_menus(cur, role_ids["boss"], menu_result["boss_menu_ids"])
                    self._bind_role_menus(cur, role_ids["staff"], menu_result["staff_menu_ids"])
                    rule_count = self._ensure_default_rules(cur)
                    staff_result = self._ensure_staff_users(cur, role_ids["staff"])
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            "tenant": tenant_result,
            "boss_user_id": boss_user_id,
            "roles": role_ids,
            "menus": menu_result["changed"],
            "deleted_menus": deleted_menus,
            "dropped_tables": dropped_tables,
            "cleaned_params": cleaned_params,
            "boss_menu_ids": menu_result["boss_menu_ids"],
            "staff_menu_ids": menu_result["staff_menu_ids"],
            "rules": rule_count,
            **staff_result,
        }

    def prune_retired_tables(self) -> dict[str, Any]:
        """Drop database tables and parameters outside the SmartQA P0 scope."""

        with mysql_conn(self.target_config) as conn:
            try:
                with conn.cursor() as cur:
                    dropped_tables = self._drop_retired_template_tables(cur)
                    cleaned_params = self._cleanup_retired_params(cur)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            "dropped_tables": dropped_tables,
            "dropped_count": len(dropped_tables),
            "cleaned_params": cleaned_params,
        }

    def create_qc_tasks(
        self,
        limit: int | None = None,
        only_pending: bool = False,
        model_name: str | None = None,
        rule_version: str = DEFAULT_RULE_VERSION,
        conversation_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        model_name = model_name or get_openai_config()["model"] or DEFAULT_MODEL_NAME
        with mysql_conn(self.target_config) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT prompt_version FROM qc_rule_version WHERE rule_version=%s AND is_deleted=0", (rule_version,))
                    version = cur.fetchone()
                    if not version:
                        raise RuntimeError(f"Rule version not found: {rule_version}")
                    prompt_version = version["prompt_version"]

                    where = "WHERE c.is_deleted=0"
                    params: list[Any] = []
                    if only_pending:
                        where += " AND c.qc_status IN ('pending','failed')"
                    if conversation_ids:
                        placeholders = ",".join(["%s"] * len(conversation_ids))
                        where += f" AND c.id IN ({placeholders})"
                        params.extend(conversation_ids)
                    sql = f"""
                        SELECT c.id, c.conversation_id, c.data_hash
                        FROM dwd_qn_conversation c
                        {where}
                        ORDER BY c.start_time, c.id
                    """
                    if limit and not conversation_ids:
                        sql += f" LIMIT {int(limit)}"
                    cur.execute(sql, params)
                    conversations = cur.fetchall()

                    inserted = 0
                    skipped = 0
                    now = datetime.now()
                    for conv in conversations:
                        task_id = f"task_{conv['id']}_{short_hash(conv['conversation_id'] + conv['data_hash'] + rule_version + prompt_version, 16)}"
                        cur.execute(
                            """
                            INSERT INTO qc_task (
                                task_id, conversation_id, conversation_data_hash, rule_version, prompt_version,
                                model_name, status, created_time, updated_time, uuid, is_deleted, tenant_id, created_id
                            ) VALUES (%s,%s,%s,%s,%s,%s,'pending',%s,%s,%s,0,%s,%s)
                            ON DUPLICATE KEY UPDATE updated_time=VALUES(updated_time)
                            """,
                            (
                                task_id,
                                conv["id"],
                                conv["data_hash"],
                                rule_version,
                                prompt_version,
                                model_name,
                                now,
                                now,
                                str(uuid4()),
                                self.tenant_id,
                                self.created_id,
                            ),
                        )
                        if cur.rowcount == 1:
                            inserted += 1
                        else:
                            skipped += 1
                    task_ids: list[int] = []
                    if conversations:
                        ids = [conv["id"] for conv in conversations]
                        placeholders = ",".join(["%s"] * len(ids))
                        cur.execute(
                            f"""
                            SELECT t.id
                            FROM qc_task t
                            JOIN dwd_qn_conversation c ON c.id=t.conversation_id
                            WHERE t.conversation_id IN ({placeholders})
                              AND t.conversation_data_hash=c.data_hash
                              AND t.rule_version=%s
                              AND t.prompt_version=%s
                              AND t.is_deleted=0
                            ORDER BY FIELD(t.conversation_id, {placeholders})
                            """,
                            [*ids, rule_version, prompt_version, *ids],
                        )
                        task_ids = [row["id"] for row in cur.fetchall()]
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            "created": inserted,
            "skipped": skipped,
            "selected": len(conversations),
            "task_ids": task_ids,
            "model_name": model_name,
            "rule_version": rule_version,
            "prompt_version": prompt_version,
        }

    def run_daily_qc_sample(
        self,
        limit: int = 100,
        execute: bool = True,
        model_name: str | None = None,
        rule_version: str = DEFAULT_RULE_VERSION,
    ) -> dict[str, Any]:
        """Create and optionally execute a daily QC sample covering every staff member."""

        sample = self.select_daily_qc_sample(limit=limit, rule_version=rule_version)
        create_result = self.create_qc_tasks(
            conversation_ids=sample["conversation_ids"],
            model_name=model_name,
            rule_version=rule_version,
        )
        execute_result: dict[str, Any] = {}
        task_ids = create_result.get("task_ids") or []
        if execute and task_ids:
            execute_result = self.execute_qc_tasks(limit=len(task_ids), task_ids=task_ids)
        return {
            "limit": limit,
            "execute": execute,
            "selected_count": len(sample["conversation_ids"]),
            "staff_count": sample["staff_count"],
            "covered_staff_count": sample["covered_staff_count"],
            "expanded_for_staff_coverage": sample["expanded_for_staff_coverage"],
            "conversation_ids": sample["conversation_ids"],
            "staff_ids": sample["staff_ids"],
            "create_result": create_result,
            "execute_result": execute_result,
        }

    def run_short_qc_sample(
        self,
        limit: int = 40,
        max_messages: int = 20,
        execute: bool = True,
        model_name: str | None = None,
        rule_version: str = DEFAULT_RULE_VERSION,
    ) -> dict[str, Any]:
        """Run a real QC sample on shorter conversations while covering every staff."""

        sample = self.select_short_qc_sample(limit=limit, max_messages=max_messages, rule_version=rule_version)
        create_result = self.create_qc_tasks(
            conversation_ids=sample["conversation_ids"],
            model_name=model_name,
            rule_version=rule_version,
        )
        execute_result: dict[str, Any] = {}
        task_ids = create_result.get("task_ids") or []
        if execute and task_ids:
            execute_result = self.execute_qc_tasks(limit=len(task_ids), task_ids=task_ids)
        return {
            "limit": limit,
            "max_messages": max_messages,
            "execute": execute,
            "selected_count": len(sample["conversation_ids"]),
            "staff_count": sample["staff_count"],
            "covered_staff_count": sample["covered_staff_count"],
            "expanded_for_staff_coverage": sample["expanded_for_staff_coverage"],
            "conversation_ids": sample["conversation_ids"],
            "staff_ids": sample["staff_ids"],
            "create_result": create_result,
            "execute_result": execute_result,
        }

    def run_staff_short_qc_sample(
        self,
        staff_ids: list[int],
        per_staff: int = 1,
        max_messages: int = 20,
        execute: bool = True,
        model_name: str | None = None,
        rule_version: str = DEFAULT_RULE_VERSION,
    ) -> dict[str, Any]:
        """Run short real conversations for specific staff ids."""

        conversation_ids = self.select_staff_short_conversations(
            staff_ids=staff_ids,
            per_staff=per_staff,
            max_messages=max_messages,
            rule_version=rule_version,
        )
        create_result = self.create_qc_tasks(conversation_ids=conversation_ids, model_name=model_name, rule_version=rule_version)
        execute_result: dict[str, Any] = {}
        task_ids = create_result.get("task_ids") or []
        if execute and task_ids:
            execute_result = self.execute_qc_tasks(limit=len(task_ids), task_ids=task_ids)
        return {
            "staff_ids": staff_ids,
            "per_staff": per_staff,
            "max_messages": max_messages,
            "execute": execute,
            "conversation_ids": conversation_ids,
            "create_result": create_result,
            "execute_result": execute_result,
        }

    def select_daily_qc_sample(self, limit: int = 100, rule_version: str = DEFAULT_RULE_VERSION) -> dict[str, Any]:
        """Pick a daily QC sample. First pass covers each staff, second pass fills by recency."""

        limit = max(1, int(limit or 100))
        with mysql_conn(self.target_config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT prompt_version FROM qc_rule_version WHERE rule_version=%s AND is_deleted=0", (rule_version,))
                version = cur.fetchone()
                if not version:
                    raise RuntimeError(f"Rule version not found: {rule_version}")
                prompt_version = version["prompt_version"]

                def fetch_candidates(exclude_success: bool) -> list[dict[str, Any]]:
                    success_filter = ""
                    if exclude_success:
                        success_filter = """
                            AND NOT EXISTS (
                                SELECT 1
                                FROM qc_task t
                                WHERE t.conversation_id=c.id
                                  AND t.conversation_data_hash=c.data_hash
                                  AND t.rule_version=%s
                                  AND t.prompt_version=%s
                                  AND t.status='success'
                                  AND t.is_deleted=0
                            )
                        """
                    sql = f"""
                        SELECT c.id, c.staff_id, c.start_time, c.message_count
                        FROM dwd_qn_conversation c
                        WHERE c.is_deleted=0
                          AND c.staff_id IS NOT NULL
                          {success_filter}
                        ORDER BY c.start_time DESC, c.id DESC
                    """
                    params = (rule_version, prompt_version) if exclude_success else ()
                    cur.execute(sql, params)
                    return list(cur.fetchall())

                candidates = fetch_candidates(exclude_success=True)
                if not candidates:
                    candidates = fetch_candidates(exclude_success=False)

        staff_ids = sorted({row["staff_id"] for row in candidates if row.get("staff_id") is not None})
        effective_limit = max(limit, len(staff_ids))
        selected: list[dict[str, Any]] = []
        selected_ids: set[int] = set()
        covered_staff: set[int] = set()

        for row in candidates:
            staff_id = row.get("staff_id")
            if staff_id is None or staff_id in covered_staff:
                continue
            selected.append(row)
            selected_ids.add(row["id"])
            covered_staff.add(staff_id)

        for row in candidates:
            if len(selected) >= effective_limit:
                break
            if row["id"] in selected_ids:
                continue
            selected.append(row)
            selected_ids.add(row["id"])

        return {
            "conversation_ids": [row["id"] for row in selected],
            "staff_ids": staff_ids,
            "staff_count": len(staff_ids),
            "covered_staff_count": len(covered_staff),
            "expanded_for_staff_coverage": effective_limit > limit,
        }

    def select_short_qc_sample(self, limit: int = 40, max_messages: int = 20, rule_version: str = DEFAULT_RULE_VERSION) -> dict[str, Any]:
        """Pick shorter real conversations, first covering every staff, then filling by recency."""

        limit = max(1, int(limit or 40))
        max_messages = max(2, int(max_messages or 20))
        with mysql_conn(self.target_config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT prompt_version FROM qc_rule_version WHERE rule_version=%s AND is_deleted=0", (rule_version,))
                version = cur.fetchone()
                if not version:
                    raise RuntimeError(f"Rule version not found: {rule_version}")
                prompt_version = version["prompt_version"]
                cur.execute(
                    """
                    SELECT c.id, c.staff_id, c.start_time, c.message_count
                    FROM dwd_qn_conversation c
                    WHERE c.is_deleted=0
                      AND c.staff_id IS NOT NULL
                      AND c.message_count BETWEEN 2 AND %s
                      AND NOT EXISTS (
                          SELECT 1
                          FROM qc_task t
                          WHERE t.conversation_id=c.id
                            AND t.conversation_data_hash=c.data_hash
                            AND t.rule_version=%s
                            AND t.prompt_version=%s
                            AND t.status='success'
                            AND t.is_deleted=0
                      )
                    ORDER BY c.message_count ASC, c.start_time DESC, c.id DESC
                    """,
                    (max_messages, rule_version, prompt_version),
                )
                candidates = list(cur.fetchall())

        staff_ids = sorted({row["staff_id"] for row in candidates if row.get("staff_id") is not None})
        effective_limit = max(limit, len(staff_ids))
        selected: list[dict[str, Any]] = []
        selected_ids: set[int] = set()
        covered_staff: set[int] = set()

        for row in candidates:
            staff_id = row.get("staff_id")
            if staff_id is None or staff_id in covered_staff:
                continue
            selected.append(row)
            selected_ids.add(row["id"])
            covered_staff.add(staff_id)

        for row in candidates:
            if len(selected) >= effective_limit:
                break
            if row["id"] in selected_ids:
                continue
            selected.append(row)
            selected_ids.add(row["id"])

        return {
            "conversation_ids": [row["id"] for row in selected],
            "staff_ids": staff_ids,
            "staff_count": len(staff_ids),
            "covered_staff_count": len(covered_staff),
            "expanded_for_staff_coverage": effective_limit > limit,
        }

    def select_staff_short_conversations(
        self,
        staff_ids: list[int],
        per_staff: int = 1,
        max_messages: int = 20,
        rule_version: str = DEFAULT_RULE_VERSION,
    ) -> list[int]:
        """Pick short, not-yet-successful conversations for specific staff."""

        staff_ids = sorted({int(staff_id) for staff_id in staff_ids if staff_id})
        if not staff_ids:
            return []
        per_staff = max(1, int(per_staff or 1))
        max_messages = max(2, int(max_messages or 20))
        with mysql_conn(self.target_config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT prompt_version FROM qc_rule_version WHERE rule_version=%s AND is_deleted=0", (rule_version,))
                version = cur.fetchone()
                if not version:
                    raise RuntimeError(f"Rule version not found: {rule_version}")
                prompt_version = version["prompt_version"]
                selected: list[int] = []
                for staff_id in staff_ids:
                    cur.execute(
                        """
                        SELECT c.id
                        FROM dwd_qn_conversation c
                        WHERE c.is_deleted=0
                          AND c.staff_id=%s
                          AND c.message_count BETWEEN 2 AND %s
                          AND NOT EXISTS (
                              SELECT 1
                              FROM qc_task t
                              WHERE t.conversation_id=c.id
                                AND t.conversation_data_hash=c.data_hash
                                AND t.rule_version=%s
                                AND t.prompt_version=%s
                                AND t.status='success'
                                AND t.is_deleted=0
                          )
                        ORDER BY c.message_count ASC, c.start_time DESC, c.id DESC
                        LIMIT %s
                        """,
                        (staff_id, max_messages, rule_version, prompt_version, per_staff),
                    )
                    selected.extend(row["id"] for row in cur.fetchall())
        return selected

    def execute_qc_tasks(self, limit: int = 1, task_ids: list[int] | None = None) -> dict[str, Any]:
        """Execute QC tasks against Ali/OpenAI-compatible endpoint."""
        from openai import OpenAI

        cfg = get_openai_config()
        if not cfg["api_key"]:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if not cfg["base_url"]:
            raise RuntimeError("OPENAI_BASE_URL is not configured")

        for logger_name in ["openai", "httpx", "httpcore"]:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

        self.reset_stale_running_tasks(minutes=30)

        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=90.0)
        ok = 0
        failed = 0
        results: list[dict[str, Any]] = []

        with mysql_conn(self.target_config) as conn:
            with conn.cursor() as cur:
                if task_ids:
                    placeholders = ",".join(["%s"] * len(task_ids))
                    cur.execute(
                        f"SELECT * FROM qc_task WHERE id IN ({placeholders}) AND status IN ('pending','failed') AND is_deleted=0 ORDER BY id",
                        task_ids,
                    )
                else:
                    cur.execute(
                        "SELECT * FROM qc_task WHERE status IN ('pending','failed') AND is_deleted=0 ORDER BY id LIMIT %s",
                        (limit,),
                    )
                tasks = cur.fetchall()

            for task in tasks:
                try:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE qc_task SET status='running', started_at=%s, updated_time=%s WHERE id=%s", (datetime.now(), datetime.now(), task["id"]))
                    conn.commit()

                    with conn.cursor() as cur:
                        conversation_data = self._conversation_payload(cur, task["conversation_id"])
                        prompt = self._render_prompt(cur, task, conversation_data)
                        call_id = f"call_{task['task_id']}_{int(datetime.now().timestamp())}"
                        cur.execute(
                            """
                            INSERT INTO model_call_log (
                                call_id, task_id, model_name, request_payload, success,
                                created_time, updated_time, uuid, is_deleted, tenant_id, created_id
                            ) VALUES (%s,%s,%s,%s,0,%s,%s,%s,0,%s,%s)
                            """,
                            (
                                call_id,
                                task["id"],
                                task["model_name"],
                                json.dumps({"conversation_id": conversation_data["conversation_id"], "message_count": len(conversation_data["messages"])}, ensure_ascii=False),
                                datetime.now(),
                                datetime.now(),
                                str(uuid4()),
                                self.tenant_id,
                                self.created_id,
                            ),
                        )
                        call_log_id = cur.lastrowid
                    conn.commit()

                    response = client.chat.completions.create(
                        model=task["model_name"],
                        messages=[
                            {
                                "role": "system",
                                "content": "你是专业客服质检助手。只输出合法 JSON，不输出 Markdown。",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.2,
                        max_tokens=3000,
                        response_format={"type": "json_object"},
                    )
                    raw_text = response.choices[0].message.content or "{}"
                    result_json = json.loads(raw_text)
                    self._validate_qc_result(result_json, conversation_data)

                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE model_call_log
                            SET response_payload=%s, raw_response_text=%s, input_tokens=%s, output_tokens=%s,
                                success=1, updated_time=%s
                            WHERE id=%s
                            """,
                            (
                                json.dumps(result_json, ensure_ascii=False),
                                raw_text,
                                response.usage.prompt_tokens if response.usage else None,
                                response.usage.completion_tokens if response.usage else None,
                                datetime.now(),
                                call_log_id,
                            ),
                        )
                        self._save_qc_result(cur, task, result_json, conversation_data)
                        cur.execute(
                            "UPDATE qc_task SET status='success', response_json=%s, finished_at=%s, updated_time=%s WHERE id=%s",
                            (json.dumps(result_json, ensure_ascii=False), datetime.now(), datetime.now(), task["id"]),
                        )
                    conn.commit()
                    ok += 1
                    results.append({"task_id": task["id"], "status": "success"})
                except Exception as exc:
                    conn.rollback()
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE qc_task SET status='failed', error_message=%s, finished_at=%s, updated_time=%s WHERE id=%s",
                            (str(exc)[:60000], datetime.now(), datetime.now(), task["id"]),
                        )
                        try:
                            cur.execute(
                                """
                                UPDATE model_call_log
                                SET success=0, error_message=%s, updated_time=%s
                                WHERE task_id=%s
                                ORDER BY id DESC LIMIT 1
                                """,
                                (str(exc)[:60000], datetime.now(), task["id"]),
                            )
                        except Exception:
                            pass
                    conn.commit()
                    failed += 1
                    results.append({"task_id": task["id"], "status": "failed", "error": str(exc)})

        return {"success": ok, "failed": failed, "results": results}

    def reset_stale_running_tasks(self, minutes: int = 30, all_running: bool = False) -> int:
        """Recover interrupted model tasks so the next batch can retry them."""

        minutes = max(int(minutes or 30), 1)
        time_filter = "" if all_running else "AND TIMESTAMPDIFF(MINUTE, updated_time, NOW()) >= %s"
        params: tuple[Any, ...] = () if all_running else (minutes,)
        with mysql_conn(self.target_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE qc_task
                    SET status='pending',
                        error_message=CONCAT(COALESCE(error_message, ''), '\n自动恢复超时运行任务'),
                        updated_time=NOW()
                    WHERE is_deleted=0
                      AND status='running'
                      {time_filter}
                    """,
                    params,
                )
                changed = cur.rowcount
            conn.commit()
        return changed

    def target_counts(self) -> dict[str, int]:
        tables = [
            "ods_qn_chat_record",
            "ods_qn_shop_record",
            "dim_shop",
            "dim_product",
            "dim_staff",
            "dim_staff_account",
            "dim_customer",
            "dwd_qn_conversation",
            "dwd_qn_message",
            "qc_rule",
            "qc_prompt_template",
            "qc_rule_version",
            "qc_task",
            "qc_result",
            "qc_issue",
            "qc_issue_evidence",
            "model_call_log",
        ]
        counts: dict[str, int] = {}
        with mysql_conn(self.target_config) as conn:
            with conn.cursor() as cur:
                for table in tables:
                    cur.execute(f"SELECT COUNT(*) AS c FROM `{table}` WHERE is_deleted=0" if table != "qc_task" else f"SELECT COUNT(*) AS c FROM `{table}` WHERE is_deleted=0")
                    counts[table] = cur.fetchone()["c"]
        return counts

    def _create_batch(self, cur: pymysql.cursors.DictCursor, batch_id: str, now: datetime) -> None:
        cur.execute(
            """
            INSERT INTO ods_import_batch (
                batch_id, source_system, source_type, status, chat_rows, shop_rows, conversation_count,
                started_at, created_time, updated_time, is_deleted, tenant_id
            ) VALUES (%s,%s,'db','running',0,0,0,%s,%s,%s,0,%s)
            ON DUPLICATE KEY UPDATE status='running', started_at=VALUES(started_at), updated_time=VALUES(updated_time)
            """,
            (batch_id, SOURCE_SYSTEM, now, now, now, self.tenant_id),
        )

    def _upsert_chat_rows(self, cur: pymysql.cursors.DictCursor, batch_id: str, rows: list[dict[str, Any]]) -> int:
        cur.execute(
            """
            SELECT source_id, row_hash
            FROM ods_qn_chat_record
            WHERE source_system=%s AND is_deleted=0
            """,
            (SOURCE_SYSTEM,),
        )
        existing_hashes = {str(row["source_id"]): row["row_hash"] for row in cur.fetchall()}

        sql = """
            INSERT INTO ods_qn_chat_record (
                batch_id, source_system, source_id, relation_id, business_id, chat_target, chat_content,
                chat_time, source_create_time, message_fingerprint, row_hash, first_seen_batch_id,
                last_seen_batch_id, created_time, updated_time, is_deleted, tenant_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s)
            ON DUPLICATE KEY UPDATE
                batch_id=VALUES(batch_id),
                relation_id=VALUES(relation_id),
                business_id=VALUES(business_id),
                chat_target=VALUES(chat_target),
                chat_content=VALUES(chat_content),
                chat_time=VALUES(chat_time),
                source_create_time=VALUES(source_create_time),
                message_fingerprint=VALUES(message_fingerprint),
                row_hash=VALUES(row_hash),
                last_seen_batch_id=VALUES(last_seen_batch_id),
                updated_time=VALUES(updated_time),
                is_deleted=0
        """
        now = datetime.now()
        values = []
        valid_count = 0
        for row in rows:
            if not row.get("id") or not row.get("relation_id") or not row.get("business_id") or row.get("chat_time") is None:
                continue
            valid_count += 1
            source_id = str(row["id"])
            row_hash = chat_row_hash(row)
            if existing_hashes.get(source_id) == row_hash:
                continue
            values.append(
                (
                    batch_id,
                    SOURCE_SYSTEM,
                    source_id,
                    str(row["relation_id"]),
                    str(row["business_id"]),
                    normalize_text(row.get("chat_target")),
                    normalize_text(row.get("chat_content")),
                    row.get("chat_time"),
                    row.get("create_time"),
                    message_fingerprint(row),
                    row_hash,
                    batch_id,
                    batch_id,
                    now,
                    now,
                    self.tenant_id,
                )
            )
        for batch in chunked(values, 1000):
            cur.executemany(sql, batch)
        return valid_count

    def _upsert_shop_rows(self, cur: pymysql.cursors.DictCursor, batch_id: str, rows: list[dict[str, Any]]) -> int:
        cur.execute(
            """
            SELECT relation_id, business_id, row_hash
            FROM ods_qn_shop_record
            WHERE source_system=%s AND is_deleted=0
            """,
            (SOURCE_SYSTEM,),
        )
        existing_hashes = {
            (str(row["relation_id"]), str(row["business_id"])): row["row_hash"]
            for row in cur.fetchall()
        }

        sql = """
            INSERT INTO ods_qn_shop_record (
                batch_id, source_system, source_id, relation_id, business_id, shop_name, product_name,
                product_id, buyer_wangwang, seller_wangwang, status, start_time, end_time, chat_content,
                source_create_time, row_hash, first_seen_batch_id, last_seen_batch_id,
                created_time, updated_time, is_deleted, tenant_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s)
            ON DUPLICATE KEY UPDATE
                batch_id=VALUES(batch_id),
                source_id=VALUES(source_id),
                shop_name=VALUES(shop_name),
                product_name=VALUES(product_name),
                product_id=VALUES(product_id),
                buyer_wangwang=VALUES(buyer_wangwang),
                seller_wangwang=VALUES(seller_wangwang),
                status=VALUES(status),
                start_time=VALUES(start_time),
                end_time=VALUES(end_time),
                chat_content=VALUES(chat_content),
                source_create_time=VALUES(source_create_time),
                row_hash=VALUES(row_hash),
                last_seen_batch_id=VALUES(last_seen_batch_id),
                updated_time=VALUES(updated_time),
                is_deleted=0
        """
        now = datetime.now()
        values = []
        valid_count = 0
        for row in rows:
            if not row.get("relation_id") or not row.get("business_id"):
                continue
            valid_count += 1
            relation_id = str(row["relation_id"])
            business_id = str(row["business_id"])
            row_hash = shop_row_hash(row)
            if existing_hashes.get((relation_id, business_id)) == row_hash:
                continue
            values.append(
                (
                    batch_id,
                    SOURCE_SYSTEM,
                    str(row.get("id") or ""),
                    relation_id,
                    business_id,
                    normalize_text(row.get("shop_name")),
                    normalize_text(row.get("product_name")),
                    normalize_text(row.get("product_id")),
                    normalize_text(row.get("buyer_wangwang")),
                    normalize_text(row.get("seller_wangwang")),
                    normalize_text(row.get("status")),
                    row.get("start_time"),
                    row.get("end_time"),
                    normalize_text(row.get("chat_content")),
                    row.get("create_time"),
                    row_hash,
                    batch_id,
                    batch_id,
                    now,
                    now,
                    self.tenant_id,
                )
            )
        for batch in chunked(values, 1000):
            cur.executemany(sql, batch)
        return valid_count

    def _latest_success_batch_id(self, cur: pymysql.cursors.DictCursor) -> str | None:
        cur.execute("SELECT batch_id FROM ods_import_batch WHERE status='success' AND is_deleted=0 ORDER BY created_time DESC, id DESC LIMIT 1")
        row = cur.fetchone()
        return row["batch_id"] if row else None

    def _clear_warehouse(self, cur: pymysql.cursors.DictCursor) -> None:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        for table in [
            "qc_issue_evidence",
            "qc_issue",
            "qc_result",
            "qc_task",
            "model_call_log",
            "dwd_customer_staff_relation",
            "dwd_qn_message",
            "dwd_qn_conversation",
            "dim_customer_identity",
            "dim_customer",
            "dim_staff_account",
            "dim_staff",
            "dim_product",
            "dim_shop",
        ]:
            cur.execute(f"TRUNCATE TABLE `{table}`")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")

    def _build_shops(self, cur: pymysql.cursors.DictCursor) -> None:
        cur.execute(
            """
            INSERT INTO dim_shop (
                shop_key, source_system, shop_name, status, created_time, updated_time, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', LEFT(SHA2(shop_name, 256), 16)), %s, shop_name, 'active', NOW(), NOW(), 0, %s
            FROM (SELECT DISTINCT shop_name FROM ods_qn_shop_record WHERE is_deleted=0 AND shop_name <> '') s
            ON DUPLICATE KEY UPDATE status='active', updated_time=VALUES(updated_time), is_deleted=0
            """,
            (SOURCE_SYSTEM, self.tenant_id),
        )

    def _build_products(self, cur: pymysql.cursors.DictCursor) -> None:
        cur.execute(
            """
            INSERT INTO dim_product (
                product_key, source_system, shop_id, product_id, product_name, status,
                created_time, updated_time, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', ds.id, '_', COALESCE(NULLIF(o.product_id, ''), SHA2(COALESCE(o.product_name, ''), 256))),
                   %s, ds.id, COALESCE(NULLIF(o.product_id, ''), CONCAT('name_', LEFT(SHA2(COALESCE(o.product_name, ''), 256), 16))),
                   MAX(NULLIF(o.product_name, '')), 'active', NOW(), NOW(), 0, %s
            FROM ods_qn_shop_record o
            JOIN dim_shop ds ON ds.source_system=%s AND ds.shop_name=o.shop_name AND ds.is_deleted=0
            WHERE o.is_deleted=0 AND (COALESCE(o.product_id, '') <> '' OR COALESCE(o.product_name, '') <> '')
            GROUP BY ds.id, COALESCE(NULLIF(o.product_id, ''), CONCAT('name_', LEFT(SHA2(COALESCE(o.product_name, ''), 256), 16)))
            ON DUPLICATE KEY UPDATE product_name=VALUES(product_name), status='active', updated_time=VALUES(updated_time), is_deleted=0
            """,
            (SOURCE_SYSTEM, self.tenant_id, SOURCE_SYSTEM),
        )

    def _build_staff(self, cur: pymysql.cursors.DictCursor) -> None:
        cur.execute(
            """
            INSERT INTO dim_staff (
                staff_key, staff_name, primary_account, source_system, status,
                created_time, updated_time, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', LEFT(SHA2(seller_wangwang, 256), 16)),
                   CASE
                       WHEN LOCATE(':', seller_wangwang) > 0 THEN SUBSTRING_INDEX(seller_wangwang, ':', -1)
                       ELSE seller_wangwang
                   END,
                   seller_wangwang, %s, 'active', NOW(), NOW(), 0, %s
            FROM (SELECT DISTINCT seller_wangwang FROM ods_qn_shop_record WHERE is_deleted=0 AND seller_wangwang <> '') s
            ON DUPLICATE KEY UPDATE staff_name=VALUES(staff_name), status='active', updated_time=VALUES(updated_time), is_deleted=0
            """,
            (SOURCE_SYSTEM, self.tenant_id),
        )
        cur.execute(
            """
            INSERT INTO dim_staff_account (
                staff_account_key, staff_id, shop_id, source_system, channel, account_name, status,
                created_time, updated_time, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', st.id, '_', sh.id),
                   st.id, sh.id, %s, 'qianniu', o.seller_wangwang, 'active',
                   NOW(), NOW(), 0, %s
            FROM (
                SELECT DISTINCT seller_wangwang, shop_name
                FROM ods_qn_shop_record
                WHERE is_deleted=0 AND seller_wangwang <> '' AND shop_name <> ''
            ) o
            JOIN dim_staff st ON st.source_system=%s AND st.primary_account=o.seller_wangwang AND st.is_deleted=0
            JOIN dim_shop sh ON sh.source_system=%s AND sh.shop_name=o.shop_name AND sh.is_deleted=0
            ON DUPLICATE KEY UPDATE staff_id=VALUES(staff_id), shop_id=VALUES(shop_id), status='active', updated_time=VALUES(updated_time), is_deleted=0
            """,
            (SOURCE_SYSTEM, self.tenant_id, SOURCE_SYSTEM, SOURCE_SYSTEM),
        )

    def _build_customers(self, cur: pymysql.cursors.DictCursor) -> None:
        cur.execute(
            """
            INSERT INTO dim_customer (
                customer_key, primary_taobao_account, buyer_wangwang_masked, first_source,
                first_seen_at, last_seen_at, status, created_time, updated_time, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', SHA2(x.customer_account, 256)),
                   x.customer_account,
                   MAX(NULLIF(x.buyer_wangwang, '')),
                   %s,
                   MIN(x.chat_time),
                   MAX(x.chat_time),
                   'active',
                   NOW(), NOW(), 0, %s
            FROM (
                SELECT c.chat_target AS customer_account, s.buyer_wangwang, c.chat_time
                FROM ods_qn_chat_record c
                JOIN ods_qn_shop_record s
                  ON s.source_system=c.source_system
                 AND s.relation_id=c.relation_id
                 AND s.business_id=c.business_id
                 AND s.is_deleted=0
                WHERE c.is_deleted=0
                  AND COALESCE(c.chat_target, '') <> ''
                  AND c.chat_target <> s.seller_wangwang
            ) x
            GROUP BY x.customer_account
            ON DUPLICATE KEY UPDATE
                buyer_wangwang_masked=COALESCE(NULLIF(VALUES(buyer_wangwang_masked), ''), buyer_wangwang_masked),
                first_seen_at=LEAST(COALESCE(first_seen_at, VALUES(first_seen_at)), VALUES(first_seen_at)),
                last_seen_at=GREATEST(COALESCE(last_seen_at, VALUES(last_seen_at)), VALUES(last_seen_at)),
                status='active',
                updated_time=VALUES(updated_time),
                is_deleted=0
            """,
            (SOURCE_SYSTEM, self.tenant_id),
        )
        cur.execute(
            """
            INSERT INTO dim_customer_identity (
                customer_id, identity_type, identity_value, source_system, confidence, status,
                created_time, updated_time, is_deleted, tenant_id
            )
            SELECT id, 'taobao_account', primary_taobao_account, %s, 'high', 'active',
                   NOW(), NOW(), 0, %s
            FROM dim_customer
            WHERE first_source=%s AND is_deleted=0
            ON DUPLICATE KEY UPDATE customer_id=VALUES(customer_id), status='active', updated_time=VALUES(updated_time), is_deleted=0
            """,
            (SOURCE_SYSTEM, self.tenant_id, SOURCE_SYSTEM),
        )

    def _build_conversations(self, cur: pymysql.cursors.DictCursor) -> None:
        cur.execute(
            """
            INSERT INTO dwd_qn_conversation (
                conversation_key, conversation_id, source_system, relation_id, business_id,
                shop_id, product_id, staff_id, customer_id, qn_status, start_time, end_time,
                message_count, customer_message_count, staff_message_count, first_response_seconds,
                avg_response_seconds, qc_status, data_hash, created_time, updated_time, is_deleted, tenant_id
            )
            SELECT
                CONCAT('qianniu|', s.relation_id, '|', s.business_id),
                CONCAT('conv_', LEFT(SHA2(CONCAT('qianniu|', s.relation_id, '|', s.business_id), 256), 16)),
                %s,
                s.relation_id,
                s.business_id,
                sh.id,
                dp.id,
                st.id,
                dc.id,
                s.status,
                COALESCE(s.start_time, MIN(c.chat_time)),
                COALESCE(s.end_time, MAX(c.chat_time)),
                COUNT(c.id),
                SUM(CASE WHEN c.chat_target <> s.seller_wangwang THEN 1 ELSE 0 END),
                SUM(CASE WHEN c.chat_target = s.seller_wangwang THEN 1 ELSE 0 END),
                NULL,
                NULL,
                'pending',
                SHA2(GROUP_CONCAT(CONCAT(c.source_id, ':', c.row_hash) ORDER BY c.chat_time, c.id SEPARATOR '|'), 256),
                NOW(), NOW(), 0, %s
            FROM ods_qn_shop_record s
            JOIN ods_qn_chat_record c
              ON c.source_system=s.source_system
             AND c.relation_id=s.relation_id
             AND c.business_id=s.business_id
             AND c.is_deleted=0
            LEFT JOIN dim_shop sh ON sh.source_system=%s AND sh.shop_name=s.shop_name AND sh.is_deleted=0
            LEFT JOIN dim_staff st ON st.source_system=%s AND st.primary_account=s.seller_wangwang AND st.is_deleted=0
            LEFT JOIN dim_customer dc ON dc.first_source=%s AND dc.primary_taobao_account=(
                SELECT c2.chat_target
                FROM ods_qn_chat_record c2
                WHERE c2.source_system=s.source_system
                  AND c2.relation_id=s.relation_id
                  AND c2.business_id=s.business_id
                  AND c2.is_deleted=0
                  AND c2.chat_target <> s.seller_wangwang
                  AND COALESCE(c2.chat_target, '') <> ''
                ORDER BY c2.chat_time, c2.id
                LIMIT 1
            ) AND dc.is_deleted=0
            LEFT JOIN dim_product dp
              ON dp.source_system=%s
             AND dp.shop_id=sh.id
             AND dp.product_id=COALESCE(NULLIF(s.product_id, ''), CONCAT('name_', LEFT(SHA2(COALESCE(s.product_name, ''), 256), 16)))
             AND dp.is_deleted=0
            WHERE s.is_deleted=0
            GROUP BY s.relation_id, s.business_id, sh.id, dp.id, st.id, dc.id, s.status, s.start_time, s.end_time
            ON DUPLICATE KEY UPDATE
                shop_id=VALUES(shop_id),
                product_id=VALUES(product_id),
                staff_id=VALUES(staff_id),
                customer_id=VALUES(customer_id),
                qn_status=VALUES(qn_status),
                start_time=VALUES(start_time),
                end_time=VALUES(end_time),
                message_count=VALUES(message_count),
                customer_message_count=VALUES(customer_message_count),
                staff_message_count=VALUES(staff_message_count),
                data_hash=VALUES(data_hash),
                updated_time=VALUES(updated_time),
                is_deleted=0,
                qc_status=IF(data_hash <> VALUES(data_hash), 'pending', qc_status)
            """,
            (SOURCE_SYSTEM, self.tenant_id, SOURCE_SYSTEM, SOURCE_SYSTEM, SOURCE_SYSTEM, SOURCE_SYSTEM),
        )

    def _build_messages(self, cur: pymysql.cursors.DictCursor) -> None:
        cur.execute(
            """
            INSERT INTO dwd_qn_message (
                message_id, conversation_id, source_system, source_message_id, message_fingerprint,
                speaker_account, speaker_type, content_text, message_time, message_hash,
                created_time, updated_time, is_deleted, tenant_id
            )
            SELECT
                CONCAT('msg_', LEFT(SHA2(c.source_id, 256), 16)),
                conv.id,
                c.source_system,
                c.source_id,
                c.message_fingerprint,
                c.chat_target,
                CASE
                    WHEN c.chat_target = s.seller_wangwang THEN 'staff'
                    WHEN COALESCE(c.chat_target, '') <> '' THEN 'customer'
                    ELSE 'unknown'
                END,
                c.chat_content,
                c.chat_time,
                SHA2(COALESCE(c.chat_content, ''), 256),
                NOW(), NOW(), 0, %s
            FROM ods_qn_chat_record c
            JOIN ods_qn_shop_record s
              ON s.source_system=c.source_system
             AND s.relation_id=c.relation_id
             AND s.business_id=c.business_id
             AND s.is_deleted=0
            JOIN dwd_qn_conversation conv
              ON conv.source_system=c.source_system
             AND conv.relation_id=c.relation_id
             AND conv.business_id=c.business_id
             AND conv.is_deleted=0
            WHERE c.is_deleted=0
            ON DUPLICATE KEY UPDATE
                conversation_id=VALUES(conversation_id),
                message_fingerprint=VALUES(message_fingerprint),
                speaker_account=VALUES(speaker_account),
                speaker_type=VALUES(speaker_type),
                content_text=VALUES(content_text),
                message_time=VALUES(message_time),
                message_hash=VALUES(message_hash),
                updated_time=VALUES(updated_time),
                is_deleted=0
            """,
            (self.tenant_id,),
        )

    def _refresh_conversation_metrics(self, cur: pymysql.cursors.DictCursor) -> None:
        cur.execute(
            """
            SELECT conversation_id, speaker_type, message_time, source_message_id
            FROM dwd_qn_message
            WHERE is_deleted=0
            ORDER BY conversation_id, message_time, id
            """
        )
        rows = cur.fetchall()
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[row["conversation_id"]].append(row)

        updates = []
        for conversation_pk, messages in grouped.items():
            total = len(messages)
            customer_count = sum(1 for msg in messages if msg["speaker_type"] == "customer")
            staff_count = sum(1 for msg in messages if msg["speaker_type"] == "staff")
            first_response = None
            response_times = []
            waiting_customer_time = None
            for msg in messages:
                if msg["speaker_type"] == "customer":
                    waiting_customer_time = msg["message_time"]
                elif msg["speaker_type"] == "staff" and waiting_customer_time:
                    seconds = int((msg["message_time"] - waiting_customer_time).total_seconds())
                    if seconds >= 0:
                        response_times.append(seconds)
                        if first_response is None:
                            first_response = seconds
                    waiting_customer_time = None
            avg_response = int(sum(response_times) / len(response_times)) if response_times else None
            updates.append((total, customer_count, staff_count, first_response, avg_response, datetime.now(), conversation_pk))

        if updates:
            cur.executemany(
                """
                UPDATE dwd_qn_conversation
                SET message_count=%s, customer_message_count=%s, staff_message_count=%s,
                    first_response_seconds=%s, avg_response_seconds=%s, updated_time=%s
                WHERE id=%s
                """,
                updates,
            )

    def _build_customer_staff_relations(self, cur: pymysql.cursors.DictCursor) -> None:
        cur.execute(
            """
            INSERT INTO dwd_customer_staff_relation (
                relation_key, customer_id, staff_id, shop_id, first_conversation_at,
                last_conversation_at, conversation_count, created_time, updated_time, is_deleted, tenant_id
            )
            SELECT CONCAT('cust_', customer_id, '_staff_', staff_id, '_shop_', shop_id),
                   customer_id, staff_id, shop_id, MIN(start_time), MAX(start_time), COUNT(*),
                   NOW(), NOW(), 0, %s
            FROM dwd_qn_conversation
            WHERE is_deleted=0 AND customer_id IS NOT NULL AND staff_id IS NOT NULL AND shop_id IS NOT NULL
            GROUP BY customer_id, staff_id, shop_id
            ON DUPLICATE KEY UPDATE
                first_conversation_at=VALUES(first_conversation_at),
                last_conversation_at=VALUES(last_conversation_at),
                conversation_count=VALUES(conversation_count),
                updated_time=VALUES(updated_time),
                is_deleted=0
            """,
            (self.tenant_id,),
        )

    def _ensure_boss(self, cur: pymysql.cursors.DictCursor) -> int:
        username = os.getenv("SMARTQA_BOSS_USERNAME") or settings.SMARTQA_BOSS_USERNAME or "boss"
        password = os.getenv("SMARTQA_BOSS_INITIAL_PASSWORD") or settings.SMARTQA_BOSS_INITIAL_PASSWORD or "SmartQA@123456"
        cur.execute("SELECT id FROM sys_user WHERE username=%s AND tenant_id=%s AND is_deleted=0", (username, self.tenant_id))
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE sys_user
                SET is_superuser=0, status=0, name=%s, description=%s, updated_time=NOW()
                WHERE id=%s
                """,
                ("老板", "SmartQA 初始老板账号", row["id"]),
            )
            return row["id"]
        cur.execute(
            """
            INSERT INTO sys_user (
                username, password, name, gender, is_superuser, status, description,
                created_time, updated_time, uuid, is_deleted, tenant_id
            ) VALUES (%s,%s,%s,'2',0,0,%s,NOW(),NOW(),UUID(),0,%s)
            """,
            (username, PwdUtil.hash_password(password), "老板", "SmartQA 初始老板账号", self.tenant_id),
        )
        return cur.lastrowid

    def _ensure_roles(self, cur: pymysql.cursors.DictCursor) -> dict[str, int]:
        roles = {
            "boss": ("SmartQA老板", "smartqa_boss", 4),
            "staff": ("SmartQA客服", "smartqa_staff", 1),
        }
        result: dict[str, int] = {}
        for key, (name, code, data_scope) in roles.items():
            cur.execute("SELECT id FROM sys_role WHERE tenant_id=%s AND code=%s AND is_deleted=0", (self.tenant_id, code))
            row = cur.fetchone()
            if row:
                result[key] = row["id"]
                continue
            cur.execute(
                """
                INSERT INTO sys_role (
                    name, code, `order`, status, description, data_scope,
                    created_time, updated_time, uuid, is_deleted, tenant_id
                ) VALUES (%s,%s,%s,0,%s,%s,NOW(),NOW(),UUID(),0,%s)
                """,
                (name, code, 1 if key == "boss" else 2, "SmartQA 默认角色", data_scope, self.tenant_id),
            )
            result[key] = cur.lastrowid
        return result

    def _bind_user_role(self, cur: pymysql.cursors.DictCursor, user_id: int, role_id: int) -> None:
        cur.execute("INSERT IGNORE INTO sys_user_roles (user_id, role_id) VALUES (%s,%s)", (user_id, role_id))

    def _ensure_tenant(self, cur: pymysql.cursors.DictCursor) -> dict[str, Any]:
        cur.execute(
            """
            SELECT id
            FROM platform_tenant
            WHERE id=%s OR code='system'
            ORDER BY id=%s DESC, id ASC
            LIMIT 1
            """,
            (self.tenant_id, self.tenant_id),
        )
        row = cur.fetchone()
        values = (
            "SmartQA",
            "system",
            "SmartQA Service Cloud",
            "1.1.0",
            "Copyright © 2026 SmartQA",
            "https://github.com/Yeraphael/SmartQA-Service-Cloud",
        )
        if row:
            cur.execute(
                """
                UPDATE platform_tenant
                SET name=%s, code=%s, description=%s, version=%s, copyright=%s,
                    git_code=%s, status=0, updated_time=NOW(), is_deleted=0
                WHERE id=%s
                """,
                (*values, row["id"]),
            )
            return {"tenant_id": row["id"], "created": False, "version": "1.1.0"}

        cur.execute(
            """
            INSERT INTO platform_tenant (
                id, name, code, description, version, copyright, git_code, status,
                created_time, updated_time, uuid, is_deleted
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,0,NOW(),NOW(),UUID(),0)
            """,
            (self.tenant_id, *values),
        )
        return {"tenant_id": self.tenant_id, "created": True, "version": "1.1.0"}

    def _ensure_staff_users(self, cur: pymysql.cursors.DictCursor, role_id: int) -> dict[str, int]:
        cur.execute("SELECT * FROM dim_staff WHERE is_deleted=0 AND status='active' ORDER BY id")
        staff_rows = cur.fetchall()
        created = 0
        bound = 0
        for staff in staff_rows:
            username = f"staff_{short_hash(staff['primary_account'], 10)}"
            cur.execute("SELECT id FROM sys_user WHERE tenant_id=%s AND username=%s AND is_deleted=0", (self.tenant_id, username))
            user = cur.fetchone()
            if not user:
                cur.execute(
                    """
                    INSERT INTO sys_user (
                        username, password, name, gender, is_superuser, status, description,
                        created_time, updated_time, uuid, is_deleted, tenant_id
                    ) VALUES (%s,%s,%s,'2',0,0,'SmartQA 客服账号',NOW(),NOW(),UUID(),0,%s)
                    """,
                    (username, PwdUtil.hash_password("SmartQA@123456"), staff["staff_name"], self.tenant_id),
                )
                user_id = cur.lastrowid
                created += 1
            else:
                user_id = user["id"]
            cur.execute("INSERT IGNORE INTO sys_user_roles (user_id, role_id) VALUES (%s,%s)", (user_id, role_id))
            cur.execute("UPDATE dim_staff SET sys_user_id=%s, updated_time=NOW() WHERE id=%s", (user_id, staff["id"]))
            bound += 1
        return {"staff_users_created": created, "staff_users_bound": bound}

    def _bind_role_menus(self, cur: pymysql.cursors.DictCursor, role_id: int, menu_ids: list[int]) -> None:
        if menu_ids:
            placeholders = ",".join(["%s"] * len(menu_ids))
            cur.execute(
                f"DELETE FROM sys_role_menus WHERE role_id=%s AND menu_id NOT IN ({placeholders})",
                [role_id, *menu_ids],
            )
        for menu_id in menu_ids:
            cur.execute("INSERT IGNORE INTO sys_role_menus (role_id, menu_id) VALUES (%s,%s)", (role_id, menu_id))

    def _drop_retired_template_tables(self, cur: pymysql.cursors.DictCursor) -> list[str]:
        cur.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA=DATABASE()
              AND TABLE_TYPE='BASE TABLE'
            """
        )
        tables = [
            row["TABLE_NAME"]
            for row in cur.fetchall()
            if row["TABLE_NAME"] not in SMARTQA_ALLOWED_TABLES
        ]
        dropped: list[str] = []
        for table in tables:
            cur.execute(
                """
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
                """,
                (table,),
            )
            if not cur.fetchone():
                continue
            cur.execute(
                """
                SELECT TABLE_NAME, CONSTRAINT_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA=DATABASE()
                  AND REFERENCED_TABLE_SCHEMA=DATABASE()
                  AND REFERENCED_TABLE_NAME=%s
                  AND CONSTRAINT_NAME <> 'PRIMARY'
                """,
                (table,),
            )
            for fk in cur.fetchall():
                cur.execute(f"ALTER TABLE `{fk['TABLE_NAME']}` DROP FOREIGN KEY `{fk['CONSTRAINT_NAME']}`")
            cur.execute(f"DROP TABLE IF EXISTS `{table}`")
            dropped.append(table)
        return dropped

    def _cleanup_retired_params(self, cur: pymysql.cursors.DictCursor) -> dict[str, Any]:
        actions: list[str] = []
        for config_key, payload in SMARTQA_REQUIRED_PARAMS.items():
            cur.execute(
                """
                SELECT id
                FROM sys_param
                WHERE tenant_id=%s AND config_key=%s
                ORDER BY is_deleted ASC, id ASC
                LIMIT 1
                """,
                (self.tenant_id, config_key),
            )
            row = cur.fetchone()
            update_values = (
                payload["config_name"],
                payload["config_value"],
                payload["description"],
            )
            if row:
                cur.execute(
                    """
                    UPDATE sys_param
                    SET config_name=%s,
                        config_value=%s,
                        config_type=1,
                        status=0,
                        description=%s,
                        updated_time=NOW(),
                        is_deleted=0
                    WHERE id=%s
                    """,
                    (*update_values, row["id"]),
                )
                cur.execute(
                    """
                    DELETE FROM sys_param
                    WHERE tenant_id=%s AND config_key=%s AND id<>%s
                    """,
                    (self.tenant_id, config_key, row["id"]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO sys_param (
                        config_name, config_key, config_value, config_type, status, description,
                        created_time, updated_time, uuid, is_deleted, tenant_id
                    ) VALUES (%s,%s,%s,1,0,%s,NOW(),NOW(),UUID(),0,%s)
                    """,
                    (
                        payload["config_name"],
                        config_key,
                        payload["config_value"],
                        payload["description"],
                        self.tenant_id,
                    ),
                )

        keep_keys = sorted(SMARTQA_REQUIRED_PARAMS)
        placeholders = ",".join(["%s"] * len(keep_keys))
        cur.execute(
            f"""
            DELETE FROM sys_param
            WHERE tenant_id=%s AND config_key NOT IN ({placeholders})
            """,
            [self.tenant_id, *keep_keys],
        )
        if cur.rowcount:
            actions.append(f"deleted non-SmartQA sys_param rows: {cur.rowcount}")
        return {"actions": actions}

    def _cleanup_template_menus(self, cur: pymysql.cursors.DictCursor, keep_menu_ids: list[int]) -> int:
        if not keep_menu_ids:
            return 0
        placeholders = ",".join(["%s"] * len(keep_menu_ids))
        cur.execute(
            f"""
            UPDATE platform_menu
            SET is_deleted=1, status=1, hidden=1, deleted_time=NOW(), updated_time=NOW()
            WHERE is_deleted=0 AND id NOT IN ({placeholders})
            """,
            keep_menu_ids,
        )
        deleted = cur.rowcount
        cur.execute(
            """
            DELETE rm
            FROM sys_role_menus rm
            LEFT JOIN platform_menu m ON rm.menu_id=m.id
            WHERE m.id IS NULL OR m.is_deleted=1
            """
        )
        return deleted

    def _ensure_smartqa_menus(self, cur: pymysql.cursors.DictCursor) -> dict[str, Any]:
        root = {
            "name": "SmartQA",
            "type": 1,
            "icon": "ri:customer-service-2-line",
            "order": 1,
            "permission": None,
            "route_name": "SmartQA",
            "route_path": "/smartqa",
            "component_path": None,
            "redirect": "/smartqa/dashboard",
        }
        boss_children = [
            ("工作台总览", "SmartQADashboard", "dashboard", "smartqa/dashboard/index", "ri:dashboard-line"),
            ("客服表现", "SmartQAStaffPerformance", "staff-performance", "smartqa/staff-performance/index", "ri:bar-chart-grouped-line"),
            ("客户商机", "SmartQACustomerOpportunities", "customer-opportunities", "smartqa/customer-opportunities/index", "ri:user-search-line"),
            ("商品机会", "SmartQAProductOpportunities", "product-opportunities", "smartqa/product-opportunities/index", "ri:shopping-bag-3-line"),
            ("会话复盘", "SmartQAConversations", "conversations", "smartqa/conversations/index", "ri:message-3-line"),
            ("客服管理", "SmartQAStaffUsers", "staff-users", "smartqa/staff-users/index", "ri:user-settings-line"),
        ]
        data_config = {
            "name": "数据与配置",
            "type": 1,
            "icon": "ri:settings-5-line",
            "order": 7,
            "permission": "smartqa:data-config:query",
            "route_name": "SmartQADataConfig",
            "route_path": "data-config",
            "component_path": None,
            "redirect": "/smartqa/data-config/qc-tasks",
        }
        data_config_children = [
            ("AI分析任务", "SmartQAQcTasks", "qc-tasks", "smartqa/qc-tasks/index", "ri:robot-2-line"),
            ("每日数据批次", "SmartQAQianniuData", "qianniu-data", "smartqa/qianniu-data/index", "ri:database-2-line"),
            ("规则配置", "SmartQAQcRules", "qc-rules", "smartqa/qc-rules/index", "ri:survey-line"),
        ]
        staff_children = [
            ("我的工作台", "SmartQAMyDashboard", "my-dashboard", "smartqa/my-dashboard/index", "ri:home-smile-line"),
            ("客户跟进", "SmartQAMyConversations", "my-conversations", "smartqa/my-conversations/index", "ri:user-follow-line"),
            ("会话复盘", "SmartQAMyQcResults", "my-qc-results", "smartqa/my-qc-results/index", "ri:file-list-3-line"),
            ("个人账号", "SmartQAMyAccount", "my-account", "account/profile/index", "ri:user-line"),
        ]
        changed = 0
        boss_menu_ids: list[int] = []
        staff_menu_ids: list[int] = []
        all_menu_ids: list[int] = []

        cur.execute("SELECT id FROM platform_menu WHERE route_name=%s AND is_deleted=0", (root["route_name"],))
        row = cur.fetchone()
        if row:
            root_id = row["id"]
            cur.execute(
                """
                UPDATE platform_menu
                SET name=%s, title=%s, type=%s, `order`=%s, permission=%s, icon=%s,
                    route_path=%s, component_path=%s, redirect=%s, hidden=0, status=0,
                    always_show=1, parent_id=NULL, updated_time=NOW()
                WHERE id=%s
                """,
                (
                    root["name"],
                    root["name"],
                    root["type"],
                    root["order"],
                    root["permission"],
                    root["icon"],
                    root["route_path"],
                    root["component_path"],
                    root["redirect"],
                    root_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO platform_menu (
                    name, type, `order`, permission, icon, route_name, route_path, component_path,
                    redirect, hidden, keep_alive, always_show, title, params, affix, client, link,
                    is_iframe, is_hide_tab, active_path, show_badge, show_text_badge, scope, status,
                    description, parent_id, created_time, updated_time, uuid, is_deleted
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,1,1,%s,NULL,0,'pc',NULL,0,0,NULL,0,NULL,'tenant',0,'SmartQA P0',NULL,NOW(),NOW(),UUID(),0)
                """,
                (
                    root["name"],
                    root["type"],
                    root["order"],
                    root["permission"],
                    root["icon"],
                    root["route_name"],
                    root["route_path"],
                    root["component_path"],
                    root["redirect"],
                    root["name"],
                ),
            )
            root_id = cur.lastrowid
            changed += 1

        boss_menu_ids.append(root_id)
        staff_menu_ids.append(root_id)
        all_menu_ids.append(root_id)

        def ensure_group(item: dict[str, Any], parent_id: int) -> int:
            nonlocal changed
            cur.execute("SELECT id FROM platform_menu WHERE route_name=%s AND is_deleted=0", (item["route_name"],))
            group = cur.fetchone()
            if group:
                group_id = group["id"]
                cur.execute(
                    """
                    UPDATE platform_menu
                    SET name=%s, title=%s, type=%s, `order`=%s, permission=%s, icon=%s,
                        route_path=%s, component_path=%s, redirect=%s, hidden=0, status=0,
                        always_show=1, parent_id=%s, updated_time=NOW()
                    WHERE id=%s
                    """,
                    (
                        item["name"],
                        item["name"],
                        item["type"],
                        item["order"],
                        item["permission"],
                        item["icon"],
                        item["route_path"],
                        item["component_path"],
                        item["redirect"],
                        parent_id,
                        group_id,
                    ),
                )
                return group_id

            cur.execute(
                """
                INSERT INTO platform_menu (
                    name, type, `order`, permission, icon, route_name, route_path, component_path,
                    redirect, hidden, keep_alive, always_show, title, params, affix, client, link,
                    is_iframe, is_hide_tab, active_path, show_badge, show_text_badge, scope, status,
                    description, parent_id, created_time, updated_time, uuid, is_deleted
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,1,1,%s,NULL,0,'pc',NULL,0,0,NULL,0,NULL,'tenant',0,'SmartQA P0',%s,NOW(),NOW(),UUID(),0)
                """,
                (
                    item["name"],
                    item["type"],
                    item["order"],
                    item["permission"],
                    item["icon"],
                    item["route_name"],
                    item["route_path"],
                    item["component_path"],
                    item["redirect"],
                    item["name"],
                    parent_id,
                ),
            )
            changed += 1
            return cur.lastrowid

        def ensure_child(idx: int, item: tuple[str, str, str, str, str], parent_id: int) -> int:
            nonlocal changed
            name, route_name, route_path, component_path, icon = item
            permission = f"smartqa:{route_path}:query"
            cur.execute("SELECT id FROM platform_menu WHERE route_name=%s AND is_deleted=0", (route_name,))
            child = cur.fetchone()
            if child:
                child_id = child["id"]
                cur.execute(
                    """
                    UPDATE platform_menu
                    SET name=%s, title=%s, type=2, `order`=%s, permission=%s, icon=%s, route_path=%s,
                        component_path=%s, redirect=NULL, hidden=0, status=0, always_show=0,
                        parent_id=%s, updated_time=NOW()
                    WHERE id=%s
                    """,
                    (name, name, idx, permission, icon, route_path, component_path, parent_id, child_id),
                )
                return child_id
            cur.execute(
                """
                INSERT INTO platform_menu (
                    name, type, `order`, permission, icon, route_name, route_path, component_path,
                    redirect, hidden, keep_alive, always_show, title, params, affix, client, link,
                    is_iframe, is_hide_tab, active_path, show_badge, show_text_badge, scope, status,
                    description, parent_id, created_time, updated_time, uuid, is_deleted
                ) VALUES (%s,2,%s,%s,%s,%s,%s,%s,NULL,0,1,0,%s,NULL,0,'pc',NULL,0,0,NULL,0,NULL,'tenant',0,'SmartQA P0',%s,NOW(),NOW(),UUID(),0)
                """,
                (name, idx, permission, icon, route_name, route_path, component_path, name, parent_id),
            )
            changed += 1
            return cur.lastrowid

        for idx, item in enumerate(boss_children, start=1):
            menu_id = ensure_child(idx, item, root_id)
            boss_menu_ids.append(menu_id)
            all_menu_ids.append(menu_id)

        data_config_id = ensure_group(data_config, root_id)
        boss_menu_ids.append(data_config_id)
        all_menu_ids.append(data_config_id)
        for idx, item in enumerate(data_config_children, start=1):
            menu_id = ensure_child(idx, item, data_config_id)
            boss_menu_ids.append(menu_id)
            all_menu_ids.append(menu_id)

        for idx, item in enumerate(staff_children, start=len(boss_children) + 2):
            menu_id = ensure_child(idx, item, root_id)
            staff_menu_ids.append(menu_id)
            all_menu_ids.append(menu_id)

        return {
            "changed": changed,
            "boss_menu_ids": boss_menu_ids,
            "staff_menu_ids": staff_menu_ids,
            "all_menu_ids": sorted(set(all_menu_ids)),
        }

    def _ensure_default_rules(self, cur: pymysql.cursors.DictCursor) -> int:
        prompt = (
            "请对以下千牛客服会话做客服质检和客户意向分析。你必须按 SmartQA 客服质检与客户意向 BI 开发规则执行。\n"
            "会话ID: {conversation_id}\n"
            "千牛状态: {qn_status}\n\n"
            "规则:\n{rules}\n\n"
            "聊天记录:\n{messages}\n\n"
            "业务口径：先服务，再承接；能留资是加分；只留资不服务才扣分。不要把客服询问微信/电话/手机号判为违规。\n"
            "请只输出合法 JSON，不输出 Markdown。结构必须为："
            "{"
            "\"conversation_id\":\"{conversation_id}\","
            "\"staff_quality\":{\"score\":0-100,\"level\":\"excellent|pass|fail\","
            "\"risk_level\":\"none|low|medium|high|critical\",\"dimension_scores\":{}},"
            "\"customer_intent_detail\":{\"customer_id\":\"\",\"intent_score\":0-100,"
            "\"intent_tier\":\"H1|H2|H3|H4|L\",\"lifecycle_stage\":\"CL01|CL02|CL03|CL04|CL05|CL06|CL07|CL08|CL09|CL10\","
            "\"need_type\":\"normal|custom|bulk|after_sale|quote|unknown\",\"need_summary\":\"\","
            "\"intent_reasons\":[{\"reason_code\":\"\",\"reason_text\":\"\",\"evidence_message_ids\":[\"msg_xxx\"]}],"
            "\"missing_infos\":[],\"tags\":[],"
            "\"contact_status\":{\"contact_requested\":false,\"contact_provided\":false,\"contact_type\":null,"
            "\"xianfa_handoff_status\":\"none|asked|provided|ready|matched|converted|failed\","
            "\"request_message_ids\":[],\"provided_message_ids\":[]},"
            "\"next_action\":\"\",\"suggested_reply\":\"\"},"
            "\"issues\":[{\"rule_code\":\"\",\"severity\":\"low|medium|high|critical\",\"deduction_score\":0,"
            "\"title\":\"\",\"reason\":\"\",\"customer_impact\":\"\",\"evidence_message_ids\":[\"msg_xxx\"],"
            "\"suggested_action\":\"\",\"suggested_reply\":\"\"}],"
            "\"summary\":\"\",\"confidence\":0-1}"
            "证据要求：每个扣分问题、H1/H2 判断、意向原因、联系方式询问/提供都必须绑定真实 message_id；无证据不要强判。"
        )
        cur.execute(
            """
            INSERT INTO qc_prompt_template (
                prompt_version, name, template_content, output_schema_version, status,
                created_time, updated_time, uuid, is_deleted, tenant_id
            ) VALUES (%s,'千牛客服质检P0模板',%s,'smartqa-qc-v1','active',NOW(),NOW(),UUID(),0,%s)
            ON DUPLICATE KEY UPDATE template_content=VALUES(template_content), status='active', updated_time=NOW(), is_deleted=0
            """,
            (DEFAULT_PROMPT_VERSION, prompt, self.tenant_id),
        )
        rules = [
            ("SQ01_RESPONSE_TIMELY", "响应及时性", "staff_quality", "首响、平均响应、关键问题是否超时；长时间未回复或连续忽略需扣分。", 12, "medium"),
            ("SQ02_RECEPTION_COMPLETE", "接待完整度", "staff_quality", "检查开场、承接、收尾、下一步是否完整；只发模板或客户问完就断需扣分。", 8, "medium"),
            ("SQ03_NEED_PROBE", "需求识别与追问", "staff_quality", "客户有定制/批量/场景需求时，应追问商品、场景、尺寸、数量、预算、时间。", 14, "medium"),
            ("SQ04_PRODUCT_PROFESSIONAL", "商品与方案专业度", "staff_quality", "规格、材质、承重、物流、定制、替代方案解释要专业，含糊或只发链接需扣分。", 14, "medium"),
            ("SQ05_SOLUTION_COMPLETE", "问题解决完成度", "staff_quality", "客户核心问题必须正面回答；价格、尺寸、物流等未答到点需扣分。", 14, "high"),
            ("SQ06_CONVERSION_CONTACT", "转化推进与留资承接", "staff_quality", "高意向客户应报价、引导下单、自然询问联系方式或安排先发承接；合理留资是加分。", 16, "high"),
            ("SQ07_ATTITUDE_WARMTH", "情绪态度与沟通温度", "staff_quality", "礼貌、耐心、自然，不冷漠不攻击；敷衍、不耐烦、冲突需扣分。", 8, "medium"),
            ("SQ08_OBJECTION_HANDLING", "异议处理能力", "staff_quality", "客户说贵、再看看、不放心、比价时，应共情、解释价值、给选择。", 6, "medium"),
            ("SQ09_COMPLIANCE_RISK", "合规与风险控制", "staff_quality", "不得虚假承诺、绝对化表达、隐私过采、冲突升级；询问联系方式本身不是违规。", 6, "critical"),
            ("SQ10_HANDOFF_RECORD", "数据记录与交接", "staff_quality", "客户给联系方式后应确认、记录并进入承接；未确认未交接需扣分。", 2, "medium"),
            ("CI01_NEED_CLARITY", "需求明确度", "customer_intent", "客户明确要买、定制、某规格、数量等为高意向信号。", 18, "low"),
            ("CI02_USAGE_SCENE", "场景用途清晰度", "customer_intent", "阳台、露台、庭院、工程、店铺、装修等清晰场景提高意向分。", 10, "low"),
            ("CI03_SPEC_QUANTITY", "规格数量完整度", "customer_intent", "尺寸、数量、材质、承重、图片、图纸越明确意向越高。", 12, "low"),
            ("CI04_BUDGET_PRICE", "预算与价格接受度", "customer_intent", "明确预算、接受报价、报价后继续问加分；只砍价或预算不匹配减分。", 15, "low"),
            ("CI05_URGENCY", "时间紧迫度", "customer_intent", "今天、明天、本周、装修、开业、工期等近期节点提高优先级。", 10, "low"),
            ("CI06_INTERACTION_DEPTH", "互动投入度", "customer_intent", "多轮追问、主动发图、主动回复、问细节说明投入高。", 10, "low"),
            ("CI07_TRUST_SIGNAL", "信任与品牌认可", "customer_intent", "认可质量、款式、评价、朋友推荐等提高意向；强不信任减分。", 8, "low"),
            ("CI08_CONTACT_WILLINGNESS", "联系方式/微信承接意愿", "customer_intent", "主动留微信/电话、同意加微信属于强意向；拒绝沟通则降低。", 10, "low"),
            ("CI09_ORDER_SIGNAL", "成交动作信号", "customer_intent", "问怎么拍、发货、运费、地址、发票、付款等为成交信号。", 7, "low"),
        ]
        for code, name, category, standard, score, severity in rules:
            cur.execute(
                """
                INSERT INTO qc_rule (
                    rule_code, rule_name, category, judgment_standard, deduction_score, severity, status,
                    created_time, updated_time, uuid, is_deleted, tenant_id
                ) VALUES (%s,%s,%s,%s,%s,%s,'active',NOW(),NOW(),UUID(),0,%s)
                ON DUPLICATE KEY UPDATE
                    rule_name=VALUES(rule_name), category=VALUES(category), judgment_standard=VALUES(judgment_standard),
                    deduction_score=VALUES(deduction_score), severity=VALUES(severity), status='active', updated_time=NOW(), is_deleted=0
                """,
                (code, name, category, standard, score, severity, self.tenant_id),
            )
        rule_codes = [rule[0] for rule in rules]
        placeholders = ",".join(["%s"] * len(rule_codes))
        cur.execute(
            f"""
            UPDATE qc_rule
            SET status='retired', is_deleted=1, deleted_time=NOW(), updated_time=NOW()
            WHERE tenant_id=%s AND is_deleted=0 AND rule_code NOT IN ({placeholders})
            """,
            (self.tenant_id, *rule_codes),
        )
        rule_snapshot = {
            code: {
                "rule_name": name,
                "category": category,
                "judgment_standard": standard,
                "deduction_score": score,
                "severity": severity,
            }
            for code, name, category, standard, score, severity in rules
        }
        cur.execute(
            """
            INSERT INTO qc_rule_version (
                rule_version, prompt_version, rule_codes, rule_snapshot, status, published_at,
                created_time, updated_time, uuid, is_deleted, tenant_id
            ) VALUES (%s,%s,%s,%s,'active',NOW(),NOW(),NOW(),UUID(),0,%s)
            ON DUPLICATE KEY UPDATE
                prompt_version=VALUES(prompt_version), rule_codes=VALUES(rule_codes),
                rule_snapshot=VALUES(rule_snapshot), status='active', updated_time=NOW(), is_deleted=0
            """,
            (
                DEFAULT_RULE_VERSION,
                DEFAULT_PROMPT_VERSION,
                json.dumps([rule[0] for rule in rules], ensure_ascii=False),
                json.dumps(rule_snapshot, ensure_ascii=False),
                self.tenant_id,
            ),
        )
        return len(rules)

    def _conversation_payload(self, cur: pymysql.cursors.DictCursor, conversation_pk: int) -> dict[str, Any]:
        cur.execute(
            """
            SELECT c.*, s.shop_name, st.staff_name, st.primary_account AS staff_account,
                   cu.primary_taobao_account AS customer_account, p.product_name
            FROM dwd_qn_conversation c
            LEFT JOIN dim_shop s ON c.shop_id=s.id
            LEFT JOIN dim_staff st ON c.staff_id=st.id
            LEFT JOIN dim_customer cu ON c.customer_id=cu.id
            LEFT JOIN dim_product p ON c.product_id=p.id
            WHERE c.id=%s AND c.is_deleted=0
            """,
            (conversation_pk,),
        )
        conv = cur.fetchone()
        if not conv:
            raise RuntimeError("conversation not found")
        cur.execute(
            """
            SELECT id, message_id, source_message_id, speaker_type, speaker_account, content_text, message_time
            FROM dwd_qn_message
            WHERE conversation_id=%s AND is_deleted=0
            ORDER BY message_time, id
            """,
            (conversation_pk,),
        )
        messages = cur.fetchall()
        return {
            "pk": conversation_pk,
            "conversation_id": conv["conversation_id"],
            "qn_status": conv["qn_status"],
            "shop_name": conv.get("shop_name"),
            "staff_account": conv.get("staff_account"),
            "customer_account": conv.get("customer_account"),
            "messages": [
                {
                    "pk": msg["id"],
                    "message_id": msg["message_id"],
                    "source_message_id": msg["source_message_id"],
                    "speaker_type": msg["speaker_type"],
                    "speaker_account": msg["speaker_account"],
                    "content": msg["content_text"] or "",
                    "time": msg["message_time"].strftime("%Y-%m-%d %H:%M:%S") if msg["message_time"] else "",
                }
                for msg in messages
            ],
        }

    def _render_prompt(self, cur: pymysql.cursors.DictCursor, task: dict[str, Any], conversation_data: dict[str, Any]) -> str:
        cur.execute("SELECT * FROM qc_prompt_template WHERE prompt_version=%s AND is_deleted=0", (task["prompt_version"],))
        template = cur.fetchone()
        cur.execute("SELECT * FROM qc_rule_version WHERE rule_version=%s AND is_deleted=0", (task["rule_version"],))
        version = cur.fetchone()
        if not template or not version:
            raise RuntimeError("QC prompt/rule version missing")

        snapshot = version["rule_snapshot"]
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        messages = "\n".join(
            f"[{msg['message_id']}][{msg['time']}][{msg['speaker_type']}][{msg['speaker_account']}] {msg['content']}"
            for msg in conversation_data["messages"]
        )
        rules = "\n".join(
            f"- {code}: {info['rule_name']} (扣分: {info['deduction_score']}, 严重程度: {info['severity']})\n  判断标准: {info['judgment_standard']}"
            for code, info in snapshot.items()
        )
        return (
            template["template_content"]
            .replace("{conversation_id}", conversation_data["conversation_id"])
            .replace("{qn_status}", conversation_data.get("qn_status") or "")
            .replace("{messages}", messages)
            .replace("{rules}", rules)
        )

    def _validate_qc_result(self, result_json: dict[str, Any], conversation_data: dict[str, Any]) -> None:
        existing_ids = {msg["message_id"] for msg in conversation_data["messages"]}
        staff_quality = result_json.setdefault("staff_quality", {})
        if "score" not in staff_quality:
            staff_quality["score"] = result_json.get("score", 100)
        if "level" not in staff_quality:
            staff_quality["level"] = result_json.get("result_level", "pass")
        if "risk_level" not in staff_quality:
            staff_quality["risk_level"] = result_json.get("risk_level", "none")
        result_json["score"] = staff_quality["score"]
        result_json["result_level"] = staff_quality["level"]
        result_json["risk_level"] = staff_quality["risk_level"]
        intent = result_json.setdefault("customer_intent_detail", {})
        if "intent_score" not in intent:
            intent["intent_score"] = 0
        if "intent_tier" not in intent:
            intent["intent_tier"] = self._intent_tier(intent.get("intent_score") or 0)
        contact = intent.setdefault("contact_status", {})
        contact.setdefault("contact_requested", False)
        contact.setdefault("contact_provided", False)
        contact.setdefault("xianfa_handoff_status", "none")
        issues = result_json.setdefault("issues", [])
        for issue in issues:
            ids = issue.get("evidence_message_ids") or []
            issue["evidence_message_ids"] = [msg_id for msg_id in ids if msg_id in existing_ids]

    @staticmethod
    def _intent_tier(score: int | float) -> str:
        score = int(score or 0)
        if score >= 85:
            return "H1"
        if score >= 70:
            return "H2"
        if score >= 50:
            return "H3"
        if score >= 30:
            return "H4"
        return "L"

    def _save_qc_result(self, cur: pymysql.cursors.DictCursor, task: dict[str, Any], result_json: dict[str, Any], conversation_data: dict[str, Any]) -> None:
        result_id = f"res_{task['task_id']}"
        staff_quality = result_json.get("staff_quality") or {}
        score = int(staff_quality.get("score", result_json.get("score") or 0))
        result_level = staff_quality.get("level") or result_json.get("result_level") or "pass"
        risk_level = staff_quality.get("risk_level") or result_json.get("risk_level") or "none"
        dimension_scores = staff_quality.get("dimension_scores") or result_json.get("dimension_scores") or {}
        cur.execute("SELECT id FROM qc_result WHERE task_id=%s AND is_deleted=0", (task["id"],))
        old = cur.fetchone()
        if old:
            cur.execute("DELETE FROM qc_issue_evidence WHERE issue_id IN (SELECT id FROM qc_issue WHERE result_id=%s)", (old["id"],))
            cur.execute("DELETE FROM qc_issue WHERE result_id=%s", (old["id"],))
            cur.execute("DELETE FROM qc_result WHERE id=%s", (old["id"],))
        cur.execute(
            """
            INSERT INTO qc_result (
                result_id, task_id, conversation_id, score, result_level, risk_level,
                summary, dimension_scores, confidence, created_time, updated_time, uuid, is_deleted, tenant_id, created_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW(),UUID(),0,%s,%s)
            """,
            (
                result_id,
                task["id"],
                task["conversation_id"],
                score,
                result_level,
                risk_level,
                result_json.get("summary"),
                json.dumps(dimension_scores, ensure_ascii=False),
                result_json.get("confidence"),
                self.tenant_id,
                self.created_id,
            ),
        )
        result_pk = cur.lastrowid
        msg_pk_map = {msg["message_id"]: msg["pk"] for msg in conversation_data["messages"]}
        for idx, issue in enumerate(result_json.get("issues") or [], start=1):
            issue_id = f"{result_id}_{issue.get('rule_code') or idx}_{idx}"
            cur.execute(
                """
                INSERT INTO qc_issue (
                    issue_id, result_id, rule_code, severity, title, reason,
                    suggested_action, suggested_reply, deduction_score,
                    created_time, updated_time, uuid, is_deleted, tenant_id, created_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW(),UUID(),0,%s,%s)
                """,
                (
                    issue_id,
                    result_pk,
                    issue.get("rule_code") or "UNKNOWN",
                    issue.get("severity") or "medium",
                    issue.get("title") or "质检问题",
                    issue.get("reason"),
                    issue.get("suggested_action"),
                    issue.get("suggested_reply"),
                    int(issue.get("deduction_score") or 0),
                    self.tenant_id,
                    self.created_id,
                ),
            )
            issue_pk = cur.lastrowid
            for msg_id in issue.get("evidence_message_ids") or []:
                msg_pk = msg_pk_map.get(msg_id)
                if not msg_pk:
                    continue
                cur.execute(
                    """
                    INSERT INTO qc_issue_evidence (
                        evidence_id, issue_id, message_id, evidence_text,
                        created_time, updated_time, uuid, is_deleted, tenant_id, created_id
                    ) VALUES (%s,%s,%s,%s,NOW(),NOW(),UUID(),0,%s,%s)
                    ON DUPLICATE KEY UPDATE evidence_text=VALUES(evidence_text), updated_time=NOW(), is_deleted=0
                    """,
                    (f"{issue_id}_{msg_id}", issue_pk, msg_pk, None, self.tenant_id, self.created_id),
                )
        cur.execute("UPDATE dwd_qn_conversation SET qc_status='completed', updated_time=NOW() WHERE id=%s", (task["conversation_id"],))


def build_sqlalchemy_url(config: dict[str, Any], async_driver: bool = True) -> str:
    driver = "mysql+asyncmy" if async_driver else "mysql+pymysql"
    return f"{driver}://{config['user']}:{quote_plus(config['password'])}@{config['host']}:{config['port']}/{config['database']}?charset=utf8mb4"
