"""SmartQA product API integration smoke tests."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def _assert_success_response(response, *, path: str) -> dict:
    assert response.status_code == 200, f"{path} failed: {response.text}"
    body = response.json()
    assert body["success"] is True, f"{path} returned non-success: {body}"
    assert "data" in body
    return body["data"]


class TestSmartQABossApis:
    def test_boss_dashboard_and_bi_pages_have_backend_data_contracts(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ) -> None:
        paths = [
            "/api/v1/smartqa/health/status",
            "/api/v1/smartqa/dashboard/boss-workbench",
            "/api/v1/smartqa/dashboard/staff-performance",
            "/api/v1/smartqa/dashboard/intent-customers",
            "/api/v1/smartqa/dashboard/product-opportunities",
            "/api/v1/smartqa/conversations/list",
            "/api/v1/smartqa/qc/results/list",
            "/api/v1/smartqa/qianniu/summary",
            "/api/v1/smartqa/sync/schedule",
        ]

        for path in paths:
            _assert_success_response(test_client.get(path, headers=auth_headers), path=path)

    def test_boss_workbench_contains_current_visual_dimensions(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ) -> None:
        data = _assert_success_response(
            test_client.get("/api/v1/smartqa/dashboard/boss-workbench", headers=auth_headers),
            path="/api/v1/smartqa/dashboard/boss-workbench",
        )

        labels = [item["label"] for item in data["dimensions"]]
        assert labels == ["综合表现", "响应效率", "服务态度", "专业能力", "问题解决", "需求挖掘", "成交推进"]
        assert set(data["status"]) >= {"rpa_fetch_time", "ai_finished_time", "analyzed_conversation_count", "system_status"}
        assert set(data["metrics"]) >= {
            "service_quality_score",
            "high_risk_conversation_count",
            "need_attention_staff_count",
            "high_intent_pending_count",
        }

    def test_data_config_buttons_are_wired_to_backend(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ) -> None:
        read_paths = [
            "/api/v1/smartqa/qc/tasks",
            "/api/v1/smartqa/qc/rules",
            "/api/v1/smartqa/qc/rules/prompt-templates",
            "/api/v1/smartqa/qc/rules/versions",
            "/api/v1/smartqa/staff-users",
            "/api/v1/smartqa/qianniu/batches",
        ]
        for path in read_paths:
            _assert_success_response(test_client.get(path, headers=auth_headers), path=path)

        sample_result = {
            "limit": 3,
            "execute": False,
            "selected_count": 0,
            "staff_count": 0,
            "covered_staff_count": 0,
            "expanded_for_staff_coverage": False,
            "conversation_ids": [],
            "staff_ids": [],
            "create_result": {
                "created": 0,
                "skipped": 0,
                "selected": 0,
                "task_ids": [],
                "model_name": "qwen3.7-plus",
                "rule_version": "smartqa-p0-20260625",
                "prompt_version": "smartqa-p0-prompt-20260625",
            },
        }
        with patch(
            "app.plugin.module_smartqa.pipeline.SmartQAPipeline.run_daily_qc_sample",
            return_value=sample_result,
        ) as daily_sample:
            data = _assert_success_response(
                test_client.post(
                    "/api/v1/smartqa/qc/tasks/daily-sample",
                    headers=auth_headers,
                    json={"limit": 3, "execute": False, "model_name": "qwen3.7-plus"},
                ),
                path="/api/v1/smartqa/qc/tasks/daily-sample",
            )

        daily_sample.assert_called_once()
        assert data["execute"] is False
        assert data["create_result"]["model_name"] == "qwen3.7-plus"
