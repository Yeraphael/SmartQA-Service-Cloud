"""
SmartQA system API smoke tests.

These tests intentionally cover only the retained P0 system surface: login,
current user, role-scoped menus, and password maintenance.
"""

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str, password: str = "SmartQA@123456") -> dict:
    response = client.post(
        "/system/auth/login",
        data={"username": username, "password": password, "login_type": "PC端"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    def test_boss_login_returns_token_without_tenant_switch_payload(self, test_client: TestClient) -> None:
        data = _login(test_client, "boss")
        assert data["access_token"]
        assert data["refresh_token"]
        assert "tenants" not in data
        assert data["user_info"]["username"] == "boss"

    def test_refresh_and_logout_routes_exist(self, test_client: TestClient, auth_headers: dict) -> None:
        refresh = test_client.post("/system/auth/token/refresh", json={"refresh_token": "invalid"})
        assert refresh.status_code != 404

        logout = test_client.post("/system/auth/logout", headers=auth_headers, json={"token": "invalid"})
        assert logout.status_code != 404


class TestCurrentUser:
    def test_boss_current_info_uses_boss_menu(self, test_client: TestClient, auth_headers: dict) -> None:
        response = test_client.get("/system/user/current/info", headers=auth_headers)
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["username"] == "boss"

        menu_titles = _flatten_menu_titles(data.get("menus") or [])
        assert "工作台总览" in menu_titles
        assert "客服表现" in menu_titles
        assert "客户商机" in menu_titles
        assert "商品机会" in menu_titles
        assert "客服管理" in menu_titles
        assert "数据与配置" in menu_titles
        assert _child_titles(data.get("menus") or [], "SmartQA") >= {
            "工作台总览",
            "客服表现",
            "客户商机",
            "商品机会",
            "会话复盘",
            "客服管理",
            "数据与配置",
        }
        assert _child_titles(data.get("menus") or [], "数据与配置") == {"AI分析任务", "每日数据批次", "规则配置"}
        assert "我的工作台" not in menu_titles

    def test_staff_current_info_uses_staff_menu_when_staff_exists(self, test_client: TestClient) -> None:
        staff_username = _first_staff_username(test_client)
        data = _login(test_client, staff_username)

        response = test_client.get(
            "/system/user/current/info",
            headers=_auth_headers(data["access_token"]),
        )
        assert response.status_code == 200, response.text
        body = response.json()["data"]
        assert body["username"] == staff_username

        menu_titles = _flatten_menu_titles(body.get("menus") or [])
        assert "我的工作台" in menu_titles
        assert "客户跟进" in menu_titles
        assert "会话复盘" in menu_titles
        assert "个人账号" in menu_titles
        assert _child_titles(body.get("menus") or [], "SmartQA") == {"我的工作台", "客户跟进", "会话复盘", "个人账号"}
        assert "客服管理" not in menu_titles
        assert "我的改进建议" not in menu_titles

    def test_password_update_route_exists(self, test_client: TestClient, auth_headers: dict) -> None:
        response = test_client.put(
            "/system/user/password/change",
            headers=auth_headers,
            json={"old_password": "bad-password", "new_password": "NewSmartQA@123456"},
        )
        assert response.status_code != 404


def _first_staff_username(client: TestClient) -> str:
    boss = _login(client, "boss")
    headers = _auth_headers(boss["access_token"])

    staff_id = _ensure_test_staff_dimension()
    ensure = client.post(
        f"/api/v1/smartqa/staff-users/{staff_id}/ensure",
        headers=headers,
        json={"password": "SmartQA@123456"},
    )
    assert ensure.status_code == 200, ensure.text

    response = client.get("/api/v1/smartqa/staff-users", headers=headers, params={"bound_only": True})
    assert response.status_code == 200, response.text
    rows = response.json()["data"]
    assert rows, "expected at least one seeded staff user"
    matched = next(row for row in rows if row["staff_id"] == staff_id)
    assert matched["username"]
    return matched["username"]


def _ensure_test_staff_dimension() -> int:
    import anyio
    from sqlalchemy import select

    from app.core.database import async_db_session
    from app.smartqa.models.dimension import DimStaffModel

    async def _inner() -> int:
        async with async_db_session() as db:
            result = await db.execute(
                select(DimStaffModel).where(DimStaffModel.staff_key == "test-staff-role-scope")
            )
            staff = result.scalar_one_or_none()
            if staff:
                return staff.id
            staff = DimStaffModel(
                staff_key="test-staff-role-scope",
                staff_name="测试客服",
                primary_account="test_staff_role_scope",
                source_system="qianniu",
                status="active",
                tenant_id=1,
            )
            db.add(staff)
            await db.commit()
            await db.refresh(staff)
            return staff.id

    return anyio.run(_inner)


def _flatten_menu_titles(items: list[dict]) -> set[str]:
    titles: set[str] = set()
    stack = list(items)
    while stack:
        item = stack.pop()
        title = item.get("title") or item.get("name")
        if title:
            titles.add(title)
        stack.extend(item.get("children") or [])
    return titles


def _child_titles(items: list[dict], title: str) -> set[str]:
    for item in items:
        current_title = item.get("title") or item.get("name")
        if current_title == title:
            return {
                child_title
                for child in item.get("children") or []
                if (child_title := child.get("title") or child.get("name"))
            }
        nested = _child_titles(item.get("children") or [], title)
        if nested:
            return nested
    return set()
