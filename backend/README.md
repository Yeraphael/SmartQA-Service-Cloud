# SmartQA Service Cloud Backend

SmartQA 后端负责账号权限、千牛数据同步、每日 AI 质检、老板端看板、客服端工作台和会话证据服务。运行范围围绕当前产品链路收敛，部署时通过环境变量接入真实数据库、Redis 与阿里模型。

## 目录

```text
backend/
├── app/api/v1/module_system/       # 登录、当前用户、字典、参数等最小基础接口
├── app/api/v1/module_platform/     # 动态菜单模型，仅作为权限底座
├── app/core/                       # 配置、权限、数据库、启动流程
├── app/smartqa/                    # SmartQA 业务系统
├── app/scripts/data/               # SmartQA 最小种子数据
├── scripts/smartqa_pipeline.py     # 真实数据同步、扩表、质检任务、模型执行
└── main.py
```

## 启动

```bash
cd backend
python main.py run --env=dev
```

## 真实数据命令

```bash
cd backend
python scripts\smartqa_pipeline.py counts
python scripts\smartqa_pipeline.py sync
python scripts\smartqa_pipeline.py create-tasks --limit 10
python scripts\smartqa_pipeline.py run-ai --limit 1
python scripts\smartqa_pipeline.py verify
```

账号、数据库、Redis、阿里模型配置读取 `backend/env/.env.dev` 和服务器环境变量。不要把密钥提交到仓库。
