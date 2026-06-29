# FastAPIAdmin 安全与登录机制学习总结

> 目标：后续 Vue3 页面可以重新设计，但登录、会话、安全、菜单权限和接口鉴权机制必须沿用现有链路。
> 适用范围：SmartQA Service Cloud 当前后端与前端工程。

## 1. 总体结论

当前项目真正值得保留的是 FastAPIAdmin 的账号认证、安全依赖、JWT + Redis 会话、角色菜单权限、动态路由注册、请求拦截和 Token 自动续期机制。

页面外观、布局、老板端/客服端工作台、侧边栏视觉、BI 组件、表格样式、主题风格都可以重做。重做 Vue3 框架页面时，不能把登录和权限链路也一起推倒，否则会重新出现登录失败、客服端 404、菜单空白、角色串台、接口越权等问题。

## 2. 后端登录链路

登录相关入口在：

```text
backend/app/api/v1/module_system/auth/controller.py
backend/app/api/v1/module_system/auth/service.py
backend/app/core/security.py
backend/app/core/dependencies.py
```

### 2.1 验证码

接口：

```http
GET /system/auth/captcha/get
```

返回字段：

```json
{
  "enable": true,
  "key": "验证码唯一键",
  "img_base": "data:image/png;base64,..."
}
```

后端实际逻辑：

1. `CaptchaUtil.captcha_arithmetic()` 生成算术验证码图片和答案。
2. 答案写入 Redis：

```text
captcha_codes:{captcha_key}
```

3. 登录时传 `captcha_key` 和 `captcha`。
4. 校验成功后删除验证码缓存，防止重复使用。

前端重做登录页时，可以换任何样式，但必须保留：

```ts
captcha_key
captcha
```

并且失败后要重新拉验证码。

### 2.2 登录接口

接口：

```http
POST /system/auth/login
Content-Type: multipart/form-data
```

请求字段：

```text
username
password
captcha_key
captcha
login_type
```

其中 `login_type` 当前默认是 `PC端`。

后端登录校验顺序：

1. 如果启用验证码，先校验验证码。
2. 根据 `username` 查询用户。
3. 用 `PwdUtil.verify_password()` 校验 bcrypt 密码。
4. 检查用户是否被停用。
5. 检查用户所属租户是否启用。
6. 更新 `last_login`。
7. 创建会话和 Token。

登录成功返回：

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 43200,
  "token_type": "Bearer",
  "user_info": {
    "id": 1,
    "username": "boss",
    "name": "...",
    "avatar": "...",
    "is_superuser": false
  }
}
```

## 3. Token 与会话机制

当前不是纯 JWT 无状态登录，而是：

```text
JWT 只保存 session_id
Redis 保存完整在线会话
```

JWT 载荷：

```json
{
  "sub": "session_id",
  "is_refresh": false,
  "exp": 1234567890
}
```

Redis 写入三类 key：

```text
user_session:{session_id}
access_token:{session_id}
refresh_token:{session_id}
```

`user_session` 中保存：

```text
session_id
user_id
tenant_id
user_name
ipaddr
login_location
os
browser
login_time
login_type
```

这意味着接口鉴权时不只看 JWT 是否能解码，还会检查 Redis 里该会话是否在线。退出登录会删除这三类 key。

如果 Redis 未启用，系统会使用：

```text
backend/app/core/memory_redis.py
```

作为本地内存 Redis 兼容实现。生产部署仍建议启用真实 Redis。

## 4. 刷新 Token 与退出登录

刷新接口：

```http
POST /system/auth/token/refresh
```

请求体：

```json
{
  "refresh_token": "..."
}
```

逻辑：

1. 解码 refresh token。
2. 确认 `is_refresh=true`。
3. 读取 Redis 会话。
4. 检查用户仍存在且未停用。
5. 续期 `user_session`。
6. 生成新的 access token 和 refresh token。
7. 覆盖 Redis 中的 token。

退出登录接口：

```http
POST /system/auth/logout
```

请求体：

```json
{
  "token": "当前 access_token"
}
```

逻辑：根据 token 解析 `session_id`，删除 `access_token:{session_id}`、`refresh_token:{session_id}`、`user_session:{session_id}`。

## 5. 后端接口鉴权机制

后端接口依赖：

```python
AuthPermission()
get_current_user()
```

核心文件：

```text
backend/app/core/security.py
backend/app/core/dependencies.py
```

### 5.1 Bearer Token 提取

请求头格式必须是：

```http
Authorization: Bearer <access_token>
```

`BearerTokenAuth` 会从请求头中提取 token。如果没有 token 或 token 类型不对，返回 401。

### 5.2 当前用户解析

`get_current_user()` 做的事情：

1. 解码 access token。
2. 判断 token 不是 refresh token。
3. 通过 `session_id` 从 Redis 读取 `user_session`。
4. 检查 `access_token:{session_id}` 是否还在线。
5. 根据配置执行滑动续期。
6. 从数据库重新加载用户、角色、菜单。
7. 返回 `AuthSchema`，供业务接口使用。

注意：这里会重新查数据库，所以禁用用户、角色变更、菜单变更可以在后续请求中生效。

### 5.3 权限校验

`AuthPermission(permissions=[...])` 的规则：

1. 超级管理员直接通过。
2. 没传 `permissions` 时，只校验登录态。
3. 传了权限码时，从用户角色绑定的菜单中收集 `permission`。
4. 用户拥有任一所需权限才通过。
5. 不满足则返回 403。

因此，按钮权限和接口权限的根源都是：

```text
platform_menu.permission
sys_role_menus
sys_user_roles
```

前端不能只靠隐藏按钮做安全控制，后端接口必须继续做权限判断。

## 6. 租户与请求中间件

相关文件：

```text
backend/app/core/middlewares.py
```

保留机制：

1. `CorrelationIdMiddleware`：给请求生成 `X-Correlation-ID`，方便日志追踪。
2. `TenantMiddleware`：从 token 对应的 Redis 会话中读取 `tenant_id`，写入当前请求上下文。
3. `RequestGuardMiddleware`：支持 IP 黑名单和写保护。
4. `CustomCORSMiddleware`：统一 CORS 配置。
5. `CustomGZipMiddleware`：响应压缩。

登录、验证码、文档、静态资源等路径属于白名单，不需要租户上下文。

## 7. 当前用户信息与菜单树

接口：

```http
GET /system/user/current/info
```

返回当前用户信息和菜单树。前端登录后必须调用这个接口。

后端逻辑：

1. 如果是超级管理员，返回全部 PC 菜单。
2. 普通用户根据角色绑定菜单返回可见菜单。
3. 返回菜单时会补齐父级菜单，避免子菜单存在但父级缺失导致前端菜单树断裂。
4. 只返回 `client=pc` 的菜单。
5. 菜单用 `traversal_to_tree()` 转为树形结构。

菜单字段和前端路由强相关：

```text
title            页面标题
icon             菜单图标
route_name       Vue route name
route_path       Vue route path
component_path   前端 views 下的组件路径
permission       权限码
hidden           是否隐藏
keep_alive       是否缓存
parent_id        父菜单
type             1目录 2菜单 3按钮 4外链
client           pc/app
```

## 8. 老板端与客服端角色机制

当前不是前端自己切换老板/客服，而是后端账号角色决定菜单和接口能力。

老板角色：

```text
smartqa_boss
```

客服角色：

```text
smartqa_staff
```

老板端可以看到老板菜单和老板接口。客服端只看到客服菜单，并且后端数据会按绑定客服过滤。

老板专属接口要继续使用类似机制：

```python
await ensure_smartqa_boss(auth)
```

客服数据范围要继续使用：

```python
build_staff_scope_condition(auth)
```

这样即使前端误显示了入口，后端也不会把老板数据暴露给客服。

## 9. 前端登录最小链路

前端相关文件：

```text
frontend/web/src/api/module_system/auth.ts
frontend/web/src/api/module_system/user.ts
frontend/web/src/store/modules/user.store.ts
frontend/web/src/utils/auth/index.ts
frontend/web/src/utils/http/index.ts
frontend/web/src/router/beforeEach.ts
frontend/web/src/router/MenuProcessor.ts
frontend/web/src/router/core/RouteRegistry.ts
frontend/web/src/router/core/RouteTransformer.ts
frontend/web/src/router/core/ComponentLoader.ts
```

新 Vue3 页面可以重写视觉，但至少要保留这些动作：

```text
进入登录页
  -> GET /system/auth/captcha/get
  -> 用户输入账号、密码、验证码
  -> POST /system/auth/login
  -> 保存 access_token 和 refresh_token
  -> GET /system/user/current/info
  -> 保存用户信息、角色、菜单、权限
  -> 根据菜单树注册动态路由
  -> 跳转首页
```

## 10. 前端 Token 存储

文件：

```text
frontend/web/src/utils/auth/index.ts
```

当前规则：

1. `remember=true`：token 存 `localStorage`。
2. `remember=false`：token 存 `sessionStorage`。
3. 固定 key：

```text
access_token
refresh_token
remember_me
```

注意：token 不走版本化 storage key，这是有意设计。重写前端时不要把 token 混进普通 Pinia 持久化数据里。

## 11. 前端请求拦截机制

文件：

```text
frontend/web/src/utils/http/index.ts
```

请求拦截：

1. 从 `Auth.getAccessToken()` 读取 token。
2. 自动加请求头：

```http
Authorization: Bearer <access_token>
```

3. 如果某接口设置：

```ts
headers: { Authorization: NO_AUTH_FLAG }
```

则不带 token。

响应拦截：

1. 统一检查业务 `code`。
2. GET 不弹成功提示，非 GET 成功可提示。
3. 遇到 401 或 token 过期，自动调用 refresh token。
4. refresh 成功后重放原请求。
5. 多个请求同时 401 时，只发一次 refresh，其余请求排队等待。
6. refresh 失败后清理登录态并跳回登录页。

这套机制后续必须保留，否则页面重构后接口体验会很差。

## 12. 前端动态路由机制

后端菜单不是只用来显示左侧菜单，它还决定前端动态路由。

核心流程：

```text
userStore.login()
  -> AuthAPI.login()
  -> Auth.setTokens()
  -> userStore.getUserInfo()
  -> 保存 menus 到 routeList

router.beforeEach()
  -> MenuProcessor.getMenuList()
  -> 菜单树转 AppRouteRecord
  -> RouteRegistry.register()
  -> router.addRoute()
  -> 目标路由权限校验
```

组件路径加载规则：

```text
component_path = /module_smartqa/dashboard
实际加载 = frontend/web/src/views/module_smartqa/dashboard/index.vue
```

所以后续新页面重做时，有两种选择：

1. 保持数据库菜单 `component_path` 不变，在对应路径下重写页面。
2. 如果改页面路径，必须同步更新 `platform_menu.component_path` 和种子数据。

不能只改前端文件路径，不改后端菜单路径。

## 13. 前端按钮权限

可用机制：

```vue
v-has-perm="'module_smartqa:staff-users:query'"
v-auth="'module_smartqa:staff-users:query'"
```

权限来源：

```text
userStore.prems
```

`userStore.prems` 从当前用户菜单树和角色菜单中收集 `permission` 字段得到。

注意：按钮隐藏只是体验，真正安全仍以后端接口权限为准。

## 14. 新 Vue3 框架页面重做建议

### 14.1 必须保留的底层能力

```text
AuthAPI.login
AuthAPI.getCaptcha
AuthAPI.refreshToken
AuthAPI.logout
UserAPI.getCurrentUserInfo
Auth token 存储
Axios 请求/响应拦截器
Pinia user store
router.beforeEach 登录态校验
后端菜单转动态路由
按钮权限指令或等价能力
```

### 14.2 可以重做的部分

```text
登录页视觉
登录页快捷账号入口
滑块验证 UI
主 Layout
侧边栏样式
顶部栏样式
工作台页面
BI 图表
表格组件
详情抽屉
客服端页面
主题色和整体设计语言
```

### 14.3 建议的新页面架构

```text
src/
  app/
    providers/           全局 provider、router、store 初始化
  api/
    auth.ts              登录、验证码、刷新、退出
    user.ts              当前用户、个人资料、改密
    smartqa.ts           SmartQA 业务接口
  auth/
    token.ts             access/refresh token 管理
    session.ts           登录态判断、退出
  router/
    guards.ts            登录态、菜单路由、权限校验
    dynamic-routes.ts    后端菜单转路由
  layouts/
    AuthLayout.vue
    BossLayout.vue
    StaffLayout.vue
  pages/
    auth/LoginPage.vue
    boss/...
    staff/...
  stores/
    user.ts
    menu.ts
  shared/
    http/
    ui/
    charts/
```

这只是建议目录，不要求照搬。关键是：业务页面可以自由设计，但认证、菜单、路由、权限必须有清晰边界。

## 15. 重做时不要犯的错误

1. 不要绕过 `/system/auth/captcha/get`，除非后端明确关闭验证码。
2. 不要把 refresh token 当 access token 放进 `Authorization`。
3. 不要只保存 token，不调用 `/system/user/current/info`。
4. 不要在前端硬编码老板/客服菜单作为权限来源。
5. 不要前端自行判断“老板端/客服端”后直接放行接口。
6. 不要把菜单树只当侧边栏数据，它也是动态路由来源。
7. 不要改页面路径却不改数据库 `component_path`。
8. 不要删除 Token 自动续期和并发 401 排队机制。
9. 不要把按钮隐藏当成安全机制，后端仍必须校验。
10. 不要在退出登录时只清前端状态，后端 `/logout` 也要调用。

## 16. 新前端接入验收标准

页面重做后，至少要通过这些验证：

1. 老板账号能登录。
2. 客服账号能登录。
3. 验证码错误会登录失败，刷新验证码后可重试。
4. 登录成功后能拿到当前用户信息。
5. 老板菜单只显示老板端菜单。
6. 客服菜单只显示客服端菜单。
7. 刷新页面后登录态不丢失。
8. access token 过期后能用 refresh token 自动续期。
9. refresh token 失效后会跳回登录页。
10. 客服访问老板专属接口返回 403。
11. 后端菜单新增页面后，前端可以按 `component_path` 动态加载。
12. 退出登录会清前端 token，并调用后端删除会话。

## 17. 最小登录伪代码

```ts
async function submitLogin(form) {
  const loginResp = await AuthAPI.login({
    username: form.username,
    password: form.password,
    captcha_key: form.captcha_key,
    captcha: form.captcha,
    login_type: "PC端",
  });

  const data = loginResp.data.data;
  Auth.setTokens(data.access_token, data.refresh_token, form.remember);

  const userResp = await UserAPI.getCurrentUserInfo();
  userStore.setUserInfo(userResp.data.data);
  userStore.setRoute(userResp.data.data.menus || []);

  await registerDynamicRoutes(userResp.data.data.menus || []);
  router.replace("/");
}
```

## 18. 最终判断

FastAPIAdmin 这套机制的核心价值不在页面，而在：

```text
登录认证
在线会话
Token 续期
角色菜单
动态路由
按钮权限
接口权限
租户上下文
```

SmartQA 后续可以重新设计整个 Vue3 页面框架，但必须把这些机制作为底座保留下来。页面越重做，越要把这条底座链路先稳住。
