# SmartQA 安全与登录机制说明

> 适用范围：SmartQA Service Cloud 当前产品后端与前端工程。
> 当前结论：产品登录只保留账号、密码、登录端类型和角色权限链路，不启用图形校验，不保留旧模板登录流程。

## 1. 保留的安全能力

SmartQA 当前保留底座中真正需要的安全能力：

| 能力 | 当前用途 |
|---|---|
| 账号密码认证 | 老板端和客服端共用一个登录入口 |
| bcrypt 密码哈希 | 系统用户密码不可明文存储 |
| JWT Access Token | 前端访问后端接口的身份凭证 |
| Refresh Token | 续期会话 |
| Redis/内存会话 | 保存登录会话、用户身份和过期时间 |
| 角色权限 | 区分老板端与客服端数据范围 |
| 菜单权限 | 返回老板端或客服端可见菜单 |
| 租户上下文 | 作为底座兼容和数据隔离，不在界面提供切换 |
| 请求上下文 | 记录会话、请求 ID、当前用户 |

## 2. 登录接口

登录入口：

```http
POST /api/v1/system/auth/login
Content-Type: application/x-www-form-urlencoded
```

请求字段：

```text
username
password
login_type
grant_type=password
```

前端调用时只提交以上字段。当前产品没有额外图片校验接口，也不提交额外校验字段。

登录成功返回：

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "expires_in": 43200,
  "user_info": {
    "id": 6,
    "username": "boss",
    "name": "老板",
    "is_superuser": false
  }
}
```

## 3. 后端登录校验顺序

1. 根据 `username` 查询系统用户。
2. 使用 `PwdUtil.verify_password()` 校验 bcrypt 密码。
3. 检查用户状态，停用账号不可登录。
4. 检查用户所属租户是否启用。
5. 更新 `last_login`。
6. 创建服务端会话。
7. 生成 Access Token 和 Refresh Token。
8. 返回用户基础信息。

相关文件：

```text
backend/app/api/v1/module_system/auth/controller.py
backend/app/api/v1/module_system/auth/service.py
backend/app/core/security.py
backend/app/core/dependencies.py
```

## 4. 前端登录处理

前端登录文件：

```text
frontend/web/src/smartqa/App.vue
frontend/web/src/smartqa/api.ts
```

处理原则：

| 项 | 规则 |
|---|---|
| 登录页 | 老板端/客服端角色切换，账号、密码输入 |
| 老板端 | `boss` 账号进入工作台总览 |
| 客服端 | 客服账号进入我的工作台 |
| 路径 | 本地开发固定保持 `/web` 基础路径，避免登录后跳根路径 |
| Token | 写入本地存储或会话存储 |
| 401 | 清空 Token，回到登录页 |

## 5. 角色识别

老板端识别：

```text
username == "boss"
或后端返回 is_superuser = true
```

客服端识别：

```text
非老板账号均进入客服端
```

客服账号由老板端“客服账号”页面创建或重置，账号与 `dim_staff.sys_user_id` 绑定。

## 6. 数据权限

老板端：

| 范围 | 权限 |
|---|---|
| 工作台总览 | 全部客服、全部会话、全部商品机会 |
| 客服表现 | 全部客服 |
| 客户商机 | 全部客户机会 |
| 商品机会 | 全部商品机会 |
| 会话复盘 | 全部会话 |
| 规则配置 | 可查看和测试规则 |
| 客服账号 | 可创建、重置、启停客服账号 |
| 数据与任务 | 可立即同步、发起每日抽检 |

客服端：

| 范围 | 权限 |
|---|---|
| 我的工作台 | 本人服务数据 |
| 客户跟进 | 本人负责客户 |
| 会话复盘 | 本人会话 |
| 个人账号 | 本人账号信息 |

客服端请求老板端管理接口时应返回 `403`。

## 7. 会话与 Token

请求头格式：

```http
Authorization: Bearer <access_token>
```

后端鉴权流程：

1. `BearerTokenAuth` 读取 `Authorization`。
2. `decode_access_token()` 验证 JWT。
3. 根据 `sub` 查服务端会话。
4. 构造 `AuthSchema`。
5. 按角色和数据范围执行接口逻辑。

## 8. 当前真实联调结果

2026-06-30 已通过 API 方式验证：

| 项 | 结果 |
|---|---|
| 老板登录 | `boss / SmartQA@123456` 返回 200 |
| 客服登录 | `staff_211e9e54ee / SmartQA@123456` 返回 200 |
| 老板工作台 | 返回 255 个已分析会话、18 个客服 |
| 客服工作台 | 同一接口在客服身份下只返回本人范围，16 个已分析会话、1 个客服 |
| 前端构建 | `pnpm build` 通过 |
| 后端测试 | `pytest tests\test_api_module_system.py tests\test_api_module_smartqa.py -q` 通过 |

## 9. 开发注意点

- 前端不要再接入旧模板登录页。
- 后端不要再恢复旧模板校验字段。
- 登录失败只应提示账号、密码、账号状态或权限问题。
- 老板端和客服端是产品角色，不是租户切换。
- 页面显示必须来自后端接口或数据库；没有来源的数据展示为空状态或 `-`。
