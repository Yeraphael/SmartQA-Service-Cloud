# SmartQA Service Cloud Web

SmartQA 前端是老板端和客服端共用的 Vue3 管理端。页面只保留 P0 业务：工作台、千牛数据源、会话、AI 质检任务、质检结果、客服表现、质检规则、客服账号，以及客服端“我的”页面。

## 启动

```bash
cd frontend/web
corepack pnpm install
corepack pnpm run dev
```

## 构建与检查

```bash
corepack pnpm run type-check
corepack pnpm run build:dev
```

## 目录

```text
src/api/module_smartqa/        # SmartQA 接口
src/views/module_smartqa/      # 老板端和客服端页面
src/router/                    # 登录、布局和动态菜单路由
src/store/                     # 登录态、配置、菜单等基础状态
```

登录后业务菜单来自后端 `platform_menu` 种子和角色菜单绑定。
