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
        """Drop unsafe fingerprint unique keys and add ordinary indexes."""
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
                    boss_user_id = self._ensure_boss(cur)
                    role_ids = self._ensure_roles(cur)
                    self._bind_user_role(cur, boss_user_id, role_ids["boss"])
                    menu_result = self._ensure_smartqa_menus(cur)
                    self._bind_role_menus(cur, role_ids["boss"], menu_result["menu_ids"])
                    self._bind_role_menus(cur, role_ids["staff"], menu_result["menu_ids"])
                    rule_count = self._ensure_default_rules(cur)
                    staff_result = self._ensure_staff_users(cur, role_ids["staff"])
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            "boss_user_id": boss_user_id,
            "roles": role_ids,
            "menus": menu_result["changed"],
            "menu_ids": menu_result["menu_ids"],
            "rules": rule_count,
            **staff_result,
        }

    def create_qc_tasks(
        self,
        limit: int | None = None,
        only_pending: bool = False,
        model_name: str | None = None,
        rule_version: str = DEFAULT_RULE_VERSION,
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
                    if only_pending:
                        where += " AND c.qc_status IN ('pending','failed')"
                    sql = f"""
                        SELECT c.id, c.conversation_id, c.data_hash
                        FROM dwd_qn_conversation c
                        {where}
                        ORDER BY c.start_time, c.id
                    """
                    if limit:
                        sql += f" LIMIT {int(limit)}"
                    cur.execute(sql)
                    conversations = cur.fetchall()

                    inserted = 0
                    skipped = 0
                    now = datetime.now()
                    for conv in conversations:
                        task_id = f"task_{conv['conversation_id']}_{short_hash(rule_version + prompt_version, 8)}"
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
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {"created": inserted, "skipped": skipped, "selected": len(conversations), "model_name": model_name}

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

        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
        ok = 0
        failed = 0
        results: list[dict[str, Any]] = []

        with mysql_conn(self.target_config) as conn:
            with conn.cursor() as cur:
                if task_ids:
                    placeholders = ",".join(["%s"] * len(task_ids))
                    cur.execute(
                        f"SELECT * FROM qc_task WHERE id IN ({placeholders}) AND is_deleted=0 ORDER BY id",
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
                started_at, created_time, updated_time, uuid, is_deleted, tenant_id, created_id
            ) VALUES (%s,%s,'db','running',0,0,0,%s,%s,%s,%s,0,%s,%s)
            ON DUPLICATE KEY UPDATE status='running', started_at=VALUES(started_at), updated_time=VALUES(updated_time)
            """,
            (batch_id, SOURCE_SYSTEM, now, now, now, str(uuid4()), self.tenant_id, self.created_id),
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
                last_seen_batch_id, created_time, updated_time, uuid, is_deleted, tenant_id, created_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s)
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
                    str(uuid4()),
                    self.tenant_id,
                    self.created_id,
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
                created_time, updated_time, uuid, is_deleted, tenant_id, created_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s)
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
                    str(uuid4()),
                    self.tenant_id,
                    self.created_id,
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
                shop_key, source_system, shop_name, status, created_time, updated_time, uuid, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', LEFT(SHA2(shop_name, 256), 16)), %s, shop_name, 'active', NOW(), NOW(), UUID(), 0, %s
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
                created_time, updated_time, uuid, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', ds.id, '_', COALESCE(NULLIF(o.product_id, ''), SHA2(COALESCE(o.product_name, ''), 256))),
                   %s, ds.id, COALESCE(NULLIF(o.product_id, ''), CONCAT('name_', LEFT(SHA2(COALESCE(o.product_name, ''), 256), 16))),
                   MAX(NULLIF(o.product_name, '')), 'active', NOW(), NOW(), UUID(), 0, %s
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
                created_time, updated_time, uuid, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', LEFT(SHA2(seller_wangwang, 256), 16)),
                   CASE
                       WHEN LOCATE(':', seller_wangwang) > 0 THEN SUBSTRING_INDEX(seller_wangwang, ':', -1)
                       ELSE seller_wangwang
                   END,
                   seller_wangwang, %s, 'active', NOW(), NOW(), UUID(), 0, %s
            FROM (SELECT DISTINCT seller_wangwang FROM ods_qn_shop_record WHERE is_deleted=0 AND seller_wangwang <> '') s
            ON DUPLICATE KEY UPDATE staff_name=VALUES(staff_name), status='active', updated_time=VALUES(updated_time), is_deleted=0
            """,
            (SOURCE_SYSTEM, self.tenant_id),
        )
        cur.execute(
            """
            INSERT INTO dim_staff_account (
                staff_account_key, staff_id, shop_id, source_system, channel, account_name, status,
                created_time, updated_time, uuid, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', st.id, '_', sh.id),
                   st.id, sh.id, %s, 'qianniu', o.seller_wangwang, 'active',
                   NOW(), NOW(), UUID(), 0, %s
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
                first_seen_at, last_seen_at, status, created_time, updated_time, uuid, is_deleted, tenant_id
            )
            SELECT CONCAT('qianniu_', SHA2(x.customer_account, 256)),
                   x.customer_account,
                   MAX(NULLIF(x.buyer_wangwang, '')),
                   %s,
                   MIN(x.chat_time),
                   MAX(x.chat_time),
                   'active',
                   NOW(), NOW(), UUID(), 0, %s
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
                created_time, updated_time, uuid, is_deleted, tenant_id
            )
            SELECT id, 'taobao_account', primary_taobao_account, %s, 'high', 'active',
                   NOW(), NOW(), UUID(), 0, %s
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
                avg_response_seconds, qc_status, data_hash, created_time, updated_time, uuid, is_deleted, tenant_id
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
                NOW(), NOW(), UUID(), 0, %s
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
                created_time, updated_time, uuid, is_deleted, tenant_id
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
                NOW(), NOW(), UUID(), 0, %s
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
                last_conversation_at, conversation_count, created_time, updated_time, uuid, is_deleted, tenant_id
            )
            SELECT CONCAT('cust_', customer_id, '_staff_', staff_id, '_shop_', shop_id),
                   customer_id, staff_id, shop_id, MIN(start_time), MAX(start_time), COUNT(*),
                   NOW(), NOW(), UUID(), 0, %s
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

    def _ensure_smartqa_menus(self, cur: pymysql.cursors.DictCursor) -> dict[str, Any]:
        menus = [
            {
                "name": "SmartQA",
                "type": 1,
                "icon": "ri:customer-service-2-line",
                "order": 1,
                "permission": None,
                "route_name": "SmartQA",
                "route_path": "/smartqa",
                "component_path": None,
                "redirect": "/smartqa/dashboard",
                "children": [
                    ("工作台", "SmartQADashboard", "dashboard", "module_smartqa/dashboard/index", "ri:dashboard-line"),
                    ("千牛数据", "SmartQAQianniuData", "qianniu-data", "module_smartqa/qianniu-data/index", "ri:database-2-line"),
                    ("会话明细", "SmartQAConversations", "conversations", "module_smartqa/conversations/index", "ri:message-3-line"),
                    ("质检任务", "SmartQAQcTasks", "qc-tasks", "module_smartqa/qc-tasks/index", "ri:robot-2-line"),
                    ("质检结果", "SmartQAQcResults", "qc-results", "module_smartqa/qc-results/index", "ri:file-chart-line"),
                    ("客服账号", "SmartQAStaffUsers", "staff-users", "module_smartqa/staff-users/index", "ri:user-settings-line"),
                ],
            }
        ]
        changed = 0
        menu_ids: list[int] = []
        for root in menus:
            cur.execute("SELECT id FROM platform_menu WHERE route_name=%s AND is_deleted=0", (root["route_name"],))
            row = cur.fetchone()
            if row:
                root_id = row["id"]
                cur.execute("UPDATE platform_menu SET hidden=0, status=0, updated_time=NOW() WHERE id=%s", (root_id,))
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
            menu_ids.append(root_id)
            for idx, (name, route_name, route_path, component_path, icon) in enumerate(root["children"], start=1):
                cur.execute("SELECT id FROM platform_menu WHERE route_name=%s AND is_deleted=0", (route_name,))
                child = cur.fetchone()
                if child:
                    cur.execute("UPDATE platform_menu SET hidden=0, status=0, parent_id=%s, updated_time=NOW() WHERE id=%s", (root_id, child["id"]))
                    menu_ids.append(child["id"])
                    continue
                cur.execute(
                    """
                    INSERT INTO platform_menu (
                        name, type, `order`, permission, icon, route_name, route_path, component_path,
                        redirect, hidden, keep_alive, always_show, title, params, affix, client, link,
                        is_iframe, is_hide_tab, active_path, show_badge, show_text_badge, scope, status,
                        description, parent_id, created_time, updated_time, uuid, is_deleted
                    ) VALUES (%s,2,%s,%s,%s,%s,%s,%s,NULL,0,1,0,%s,NULL,0,'pc',NULL,0,0,NULL,0,NULL,'tenant',0,'SmartQA P0',%s,NOW(),NOW(),UUID(),0)
                    """,
                    (
                        name,
                        idx,
                        f"module_smartqa:{route_path}:query",
                        icon,
                        route_name,
                        route_path,
                        component_path,
                        name,
                        root_id,
                    ),
                )
                menu_ids.append(cur.lastrowid)
                changed += 1
        return {"changed": changed, "menu_ids": menu_ids}

    def _ensure_default_rules(self, cur: pymysql.cursors.DictCursor) -> int:
        prompt = (
            "请对以下千牛客服会话做质检。\n"
            "会话ID: {conversation_id}\n"
            "千牛状态: {qn_status}\n\n"
            "规则:\n{rules}\n\n"
            "聊天记录:\n{messages}\n\n"
            "请只输出 JSON，结构为: "
            "{\"score\":0-100,\"result_level\":\"pass|fail\",\"risk_level\":\"none|low|medium|high|critical\","
            "\"summary\":\"简要结论\",\"dimension_scores\":{},\"confidence\":0-1,"
            "\"issues\":[{\"rule_code\":\"\",\"severity\":\"low|medium|high|critical\",\"title\":\"\","
            "\"reason\":\"\",\"suggested_action\":\"\",\"suggested_reply\":\"\",\"deduction_score\":0,"
            "\"evidence_message_ids\":[\"msg_xxx\"]}]}"
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
            ("P0_SERVICE_ATTITUDE", "服务态度", "service", "客服不得辱骂、敷衍、冷漠、不耐烦；若明显伤害客户体验需扣分。", 20, "high"),
            ("P0_RESPONSE_DELAY", "响应时效", "response", "客户提出问题后，客服长时间未回应或连续忽略关键问题需扣分。", 10, "medium"),
            ("P0_ACCURACY", "信息准确", "accuracy", "客服不得给出明显错误、前后矛盾或无法兑现的承诺。", 20, "high"),
            ("P0_CONVERSION", "成交引导", "conversion", "在客户有购买意向时，应适度推进下单/付款，不应机械闲聊或错失明显机会。", 10, "medium"),
            ("P0_COMPLIANCE", "合规风险", "compliance", "不得诱导违规、承诺平台外交易、泄露隐私或作出高风险表述。", 30, "critical"),
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
        if "score" not in result_json:
            result_json["score"] = 100
        if "result_level" not in result_json:
            result_json["result_level"] = "pass"
        if "risk_level" not in result_json:
            result_json["risk_level"] = "none"
        issues = result_json.setdefault("issues", [])
        for issue in issues:
            ids = issue.get("evidence_message_ids") or []
            issue["evidence_message_ids"] = [msg_id for msg_id in ids if msg_id in existing_ids]

    def _save_qc_result(self, cur: pymysql.cursors.DictCursor, task: dict[str, Any], result_json: dict[str, Any], conversation_data: dict[str, Any]) -> None:
        result_id = f"res_{task['task_id']}"
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
                int(result_json.get("score") or 0),
                result_json.get("result_level") or "pass",
                result_json.get("risk_level") or "none",
                result_json.get("summary"),
                json.dumps(result_json.get("dimension_scores") or {}, ensure_ascii=False),
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
