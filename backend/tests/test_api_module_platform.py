"""
Retained platform API tests.

SmartQA keeps the menu model internally for dynamic routes, but the platform
menu management API is not part of the boss/staff P0 product surface.
"""

from fastapi.testclient import TestClient


class TestMenu:
    def test_platform_menu_management_api_is_not_exposed(self, test_client: TestClient, auth_headers: dict) -> None:
        response = test_client.get("/platform/menu/tree", headers=auth_headers)
        assert response.status_code == 404

    def test_user_info_still_carries_dynamic_smartqa_menus(self, test_client: TestClient, auth_headers: dict) -> None:
        response = test_client.get("/system/user/current/info", headers=auth_headers)
        assert response.status_code == 200, response.text
        titles = _flatten_titles(response.json()["data"].get("menus") or [])
        assert "SmartQA" in titles
        assert "工作台总览" in titles
        assert "客服账号" in titles
        assert "插件管理" not in titles
        assert "订单管理" not in titles


def _flatten_titles(items: list[dict]) -> set[str]:
    titles: set[str] = set()
    stack = list(items)
    while stack:
        item = stack.pop()
        title = item.get("title") or item.get("name")
        if title:
            titles.add(title)
        stack.extend(item.get("children") or [])
    return titles
