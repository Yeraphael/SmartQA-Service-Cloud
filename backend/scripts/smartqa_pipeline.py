"""SmartQA real-data operations.

Examples:
  python scripts/smartqa_pipeline.py counts
  python scripts/smartqa_pipeline.py sync --truncate-dwd
  python scripts/smartqa_pipeline.py seed
  python scripts/smartqa_pipeline.py create-tasks --limit 10
  python scripts/smartqa_pipeline.py daily-qc --limit 100
  python scripts/smartqa_pipeline.py run-ai --limit 1
  python scripts/smartqa_pipeline.py prune-db
  python scripts/smartqa_pipeline.py verify
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ENVIRONMENT", "dev")

from app.plugin.module_smartqa.pipeline import SmartQAPipeline, load_env_file


def print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    load_env_file(ROOT / "env" / ".env.dev")
    parser = argparse.ArgumentParser(description="SmartQA real-data pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("counts")
    sub.add_parser("fix-schema")

    sync_parser = sub.add_parser("sync")
    sync_parser.add_argument("--no-build", action="store_true", help="only sync ODS")
    sync_parser.add_argument("--no-seed", action="store_true", help="skip rules/menu/users seed")
    sync_parser.add_argument("--truncate-dwd", action="store_true", help="clear DIM/DWD/QC before rebuild")

    build_parser = sub.add_parser("build")
    build_parser.add_argument("--truncate-dwd", action="store_true", help="clear DIM/DWD/QC before rebuild")

    sub.add_parser("seed")
    sub.add_parser("prune-db")

    task_parser = sub.add_parser("create-tasks")
    task_parser.add_argument("--limit", type=int, default=10)
    task_parser.add_argument("--all", action="store_true", help="create tasks for all conversations")

    daily_parser = sub.add_parser("daily-qc")
    daily_parser.add_argument("--limit", type=int, default=100)
    daily_parser.add_argument("--execute", action="store_true", help="call Ali model immediately")

    ai_parser = sub.add_parser("run-ai")
    ai_parser.add_argument("--limit", type=int, default=1)

    short_parser = sub.add_parser("daily-qc-short")
    short_parser.add_argument("--limit", type=int, default=40)
    short_parser.add_argument("--max-messages", type=int, default=20)
    short_parser.add_argument("--execute", action="store_true", help="call Ali model immediately")

    staff_parser = sub.add_parser("qc-staff-short")
    staff_parser.add_argument("staff_ids", nargs="+", type=int)
    staff_parser.add_argument("--per-staff", type=int, default=1)
    staff_parser.add_argument("--max-messages", type=int, default=20)
    staff_parser.add_argument("--execute", action="store_true", help="call Ali model immediately")

    reset_parser = sub.add_parser("reset-running")
    reset_parser.add_argument("--minutes", type=int, default=30)
    reset_parser.add_argument("--all", action="store_true", help="reset all running tasks regardless of age")

    sub.add_parser("verify")

    args = parser.parse_args()
    pipeline = SmartQAPipeline()

    if args.command == "counts":
        print_json({"source": pipeline.source_exact_counts(), "target": pipeline.target_counts()})
    elif args.command == "fix-schema":
        print_json({"actions": pipeline.apply_schema_fixes()})
    elif args.command == "sync":
        sync_result = pipeline.full_sync()
        build_result = pipeline.rebuild_warehouse(sync_result["batch_id"], truncate_dwd=args.truncate_dwd) if not args.no_build else {}
        seed_result = pipeline.seed_defaults() if not args.no_seed else {}
        print_json({"sync": sync_result, "build": build_result, "seed": seed_result, "target": pipeline.target_counts()})
    elif args.command == "build":
        print_json({"build": pipeline.rebuild_warehouse(truncate_dwd=args.truncate_dwd), "target": pipeline.target_counts()})
    elif args.command == "seed":
        print_json({"seed": pipeline.seed_defaults(), "target": pipeline.target_counts()})
    elif args.command == "prune-db":
        print_json({"prune": pipeline.prune_retired_tables(), "target": pipeline.target_counts()})
    elif args.command == "create-tasks":
        print_json(pipeline.create_qc_tasks(limit=None if args.all else args.limit))
    elif args.command == "daily-qc":
        print_json(pipeline.run_daily_qc_sample(limit=args.limit, execute=args.execute))
    elif args.command == "run-ai":
        print_json(pipeline.execute_qc_tasks(limit=args.limit))
    elif args.command == "daily-qc-short":
        print_json(pipeline.run_short_qc_sample(limit=args.limit, max_messages=args.max_messages, execute=args.execute))
    elif args.command == "qc-staff-short":
        print_json(
            pipeline.run_staff_short_qc_sample(
                staff_ids=args.staff_ids,
                per_staff=args.per_staff,
                max_messages=args.max_messages,
                execute=args.execute,
            )
        )
    elif args.command == "reset-running":
        print_json({"reset": pipeline.reset_stale_running_tasks(minutes=args.minutes, all_running=args.all)})
    elif args.command == "verify":
        source = pipeline.source_exact_counts()
        target = pipeline.target_counts()
        checks = {
            "ods_chat_match": target["ods_qn_chat_record"] == source["chat_count"],
            "ods_shop_match": target["ods_qn_shop_record"] == source["shop_count"],
            "dwd_message_match": target["dwd_qn_message"] == source["chat_count"],
            "dwd_conversation_match": target["dwd_qn_conversation"] == source["shop_count"],
            "has_rules": target["qc_rule"] > 0 and target["qc_rule_version"] > 0,
        }
        print_json({"source": source, "target": target, "checks": checks, "ok": all(checks.values())})


if __name__ == "__main__":
    main()
