# SmartQA Service Cloud

基于 FastApiAdmin 二开的千牛客服质检系统。当前版本只保留 P0 主链路：老板端、客服端、千牛真实数据同步、会话检索、AI 质检、质检结果和客服账号管理。

## 当前范围

- 源数据只读库：`aizhijian`
- 扩建业务库：`smartqa`
- 初始老板账号：`boss/admin`
- AI 模型：阿里百炼 `qwen3.7-plus`
- 后端运行时仅启用 SmartQA 业务插件，原框架示例、任务、内置 AI 聊天等非 P0 模块不进入业务菜单和业务路由。

敏感信息不要提交到 GitHub。数据库、阿里模型等账号密钥放在本地 `docs/` 或环境变量中，部署时按宝塔服务器实际配置填写。

## 代码位置

- 后端业务模块：`backend/app/plugin/module_smartqa/`
- 数据同步与质检流水线：`backend/app/plugin/module_smartqa/pipeline.py`
- 命令行流水线脚本：`backend/scripts/smartqa_pipeline.py`
- 前端页面：`frontend/web/src/views/module_smartqa/`
- 前端 API：`frontend/web/src/api/module_smartqa/`
- 核心设计文档：`docs/项目系统设计精炼文档.md`
- 启动使用文档：`docs/项目启动使用文档.md`

## 本地启动

后端：

```bash
cd backend
python main.py run --env=dev
```

前端：

```bash
cd frontend/web
corepack pnpm install --frozen-lockfile
corepack pnpm run dev
```

数据流水线校验：

```bash
cd backend
python scripts\smartqa_pipeline.py verify
```

如需按真实数据执行同步、建任务、调用模型质检，使用同一脚本的子命令查看帮助：

```bash
cd backend
python scripts\smartqa_pipeline.py --help
```

## 数据链路

系统从千牛源库增量同步到业务库，并按唯一键去重，适配源数据持续更新：

1. `ods_qn_chat_record` / `ods_qn_shop_record` 保留源表关键字段和源行标识。
2. `dwd_qn_message` 生成标准消息明细。
3. `dwd_qn_conversation` 生成会话聚合。
4. `qc_task` 创建待质检任务。
5. `qc_result` 保存模型质检结果。
6. `model_call_log` 记录真实模型调用。

## 权限模型

最高权限是业务老板端，不再把 `boss` 作为框架超级管理员使用。

- 老板：拥有 SmartQA 全局业务权限，可创建和管理客服账号。
- 客服：只能查看和处理与自己绑定的数据。
- 菜单：仅保留 SmartQA 工作台、千牛数据、会话明细、质检任务、质检结果、客服账号。

## 验证命令

后端编译：

```bash
cd backend
python -m compileall app\config\setting.py app\core\discover.py app\core\memory_redis.py app\core\dependencies.py app\init_app.py app\scripts\initialize.py app\api\v1\module_system\user\schema.py app\plugin\module_smartqa scripts\smartqa_pipeline.py
```

前端类型检查：

```bash
cd frontend/web
corepack pnpm run type-check
```

前端构建：

```bash
cd frontend/web
corepack pnpm run build:dev
```

## 部署提示

- 宝塔部署时按远程 MySQL、Redis、阿里百炼密钥配置环境变量。
- Redis 本地不可用时后端可用内存降级实现启动，生产环境建议使用正式 Redis。
- 不提交 `dist/`、`node_modules/`、`__pycache__/`、日志、临时脚本和任何密钥文件。
