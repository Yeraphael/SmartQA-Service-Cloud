# SmartQA 数据库字段使用审计表

> 目的：逐表标记字段是否真正使用、含义是什么、是否冗余，供后续删字段、改表、做增量同步和 BI 宽表时决策。
> 范围：本表审计 `backend/app/plugin/module_smartqa/models` 下的 SmartQA 业务表，不包含系统用户、角色、菜单、租户等平台基础表。
> 依据：SQLAlchemy 模型、`pipeline.py` 同步/构建 SQL、后端 service 查询、前端 SmartQA API 类型、`docs/SmartQA客服质检与客户意向BI开发规则.md`。

## 标记说明

| 标记 | 含义 | 处理建议 |
|---|---|---|
| 必用 | 当前同步、查询、权限、质检、页面展示或外键关联真实依赖 | 保留 |
| 框架字段 | 框架分页、软删除、租户、审计或通用 CRUD 依赖 | 低频表保留；高频批量表可瘦身 |
| 有用但可替代 | 当前有用，但可以用自然键、外键或实时计算替代 | 后续按性能和复杂度决定 |
| 预留 | 业务上合理，但当前代码基本没有使用 | 不做该功能就删除；要做增量/承接/身份打通就保留 |
| 疑似冗余 | 当前代码和近期业务都没有明确使用，或完全可由其他字段推导 | 优先删除或停止写入 |

## 总体结论

| 类型 | 字段/表 | 判断 |
|---|---|---|
| 千牛源数据幂等 | `source_id`、`relation_id`、`business_id`、`row_hash` | 必用。同步去重、会话聚合、数据变更判断都靠它们。 |
| 会话事实主线 | `dwd_qn_conversation.id`、`conversation_id`、`shop_id`、`product_id`、`staff_id`、`customer_id`、`data_hash` | 必用。页面、质检任务、权限、重复质检控制都依赖。 |
| 消息证据链 | `dwd_qn_message.id`、`message_id`、`source_message_id`、`speaker_type`、`content_text`、`message_time` | 必用。AI prompt、质检证据、会话复盘依赖。 |
| 客服权限 | `dim_staff.sys_user_id` | 必用。客服端只能看自己的会话，核心权限字段。 |
| AI 质检 | `qc_task`、`qc_result`、`qc_issue`、`qc_issue_evidence` 主外键和结果字段 | 必用。现有页面和 BI 指标直接依赖。 |
| 批量表 UUID/人员审计 | ODS/DIM/DWD 上的 `uuid`、`created_id`、`updated_id`、`deleted_id` | 疑似冗余。高频同步表不用这些字段做业务查询。 |
| 同步水位 | `ods_import_batch.checkpoint` | 预留。当前是全量同步，没有真正用它做增量。 |
| 首次/最后批次 | `first_seen_batch_id`、`last_seen_batch_id` | 预留。可用于溯源和历史变化，但当前页面不查。 |
| 消息指纹 | `message_fingerprint` | 有用但可替代。如果源表 `id` 长期稳定，价值低；如果源数据可能重复或缺 ID，保留。 |
| 维表业务键 | `shop_key`、`product_key`、`staff_key`、`customer_key` 等 | 有用但可替代。当前用于部分 builder 幂等，SQL 主链也有自然唯一约束。 |
| 客户身份表 | `dim_customer_identity` | 预留。目前只存淘宝账号，和 `dim_customer.primary_taobao_account` 重复；未来接微信/手机号才有价值。 |
| 客户客服关系表 | `dwd_customer_staff_relation` | 疑似冗余/预聚合。当前服务基本可从 `dwd_qn_conversation` 聚合出来。 |
| 模型调用日志 | `model_call_log` | 有用。不是页面核心，但对排错、成本、失败追踪有价值。 |

## 通用字段

### 高频批量表通用字段

适用于：`ods_*`、`dim_*`、`dwd_*`。

| 字段 | 标记 | 含义 | 使用情况 |
|---|---|---|---|
| `id` | 必用 | 自增主键 | 后端分页、外键、详情查询、质检任务引用都用。 |
| `tenant_id` | 框架字段 | 租户 ID | 多租户隔离需要；当前 SmartQA 默认 1，但建议保留。 |
| `is_deleted` | 框架字段 | 软删除标记 | 几乎所有查询都过滤 `is_deleted=0`，保留。 |
| `created_time` | 框架字段 | 创建时间 | 批次排序、结果排序、排查问题有用。 |
| `updated_time` | 框架字段 | 更新时间 | 同步更新、排查变化有用。 |
| `deleted_time` | 框架字段 | 删除时间 | 当前少用；若统一软删除策略存在，保留。 |
| `uuid` | 疑似冗余 | 通用全局 UUID | SmartQA 高频表无业务引用，且写入和唯一索引有成本。 |
| `created_id` / `updated_id` / `deleted_id` | 疑似冗余 | 通用人员审计 | 批量同步由系统执行，业务权限不靠它们。 |

### 质检低频表通用字段

适用于：`qc_*`、`model_call_log`。

| 字段 | 标记 | 含义 | 使用情况 |
|---|---|---|---|
| `id` | 必用 | 自增主键 | 主外键和详情查询依赖。 |
| `uuid` | 框架字段 | 通用 UUID | 当前业务不靠它，但低频表保留成本较低。 |
| `tenant_id` | 框架字段 | 租户 ID | 保留。 |
| `is_deleted` | 框架字段 | 软删除 | 服务查询大量使用。 |
| `created_time` / `updated_time` / `deleted_time` | 框架字段 | 时间审计 | 页面排序、软删除、排查问题使用。 |
| `created_id` / `updated_id` / `deleted_id` | 框架字段 | 操作人审计 | 规则配置、任务创建这类人为操作可保留。 |

## ODS 原始层

### `ods_import_batch`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `batch_id` | 必用 | 同步批次业务 ID | 创建批次、查询最近成功批次、ODS 行归属。 |
| `source_system` | 必用 | 来源系统，如 `qianniu` | 多来源预留，当前构建 SQL 过滤使用。 |
| `source_type` | 有用但可替代 | 来源类型，如 db/excel/api | 页面展示数据来源；当前主要固定为 `db`。 |
| `checkpoint` | 预留 | 增量同步水位 | 当前未真正用于增量，若仍全量同步可删除。 |
| `chat_rows` | 必用 | 本批有效聊天行数 | 批次页面、同步结果展示。 |
| `shop_rows` | 必用 | 本批有效业务行数 | 批次页面、同步结果展示。 |
| `conversation_count` | 必用 | 当前会话数 | 批次页面、同步结果展示。 |
| `status` | 必用 | pending/running/success/failed | 同步状态、最近批次判断。 |
| `error_message` | 必用 | 同步失败原因 | 同步失败排查。 |
| `started_at` | 必用 | 批次开始时间 | 批次耗时和状态展示。 |
| `finished_at` | 必用 | 批次结束时间 | 最近批次排序、同步状态展示。 |

### `ods_qn_chat_record`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `batch_id` | 必用 | 行所属同步批次 | ODS 构建、追踪来源。 |
| `source_system` | 必用 | 来源系统 | 唯一约束和构建 JOIN 使用。 |
| `source_id` | 必用 | 源表 `qn_chat_record.id` | 幂等 upsert、生成消息 ID、证据追溯。 |
| `relation_id` | 必用 | 千牛关系 ID | 与业务表组成会话键。 |
| `business_id` | 必用 | 千牛业务 ID | 与关系 ID 组成会话键。 |
| `chat_target` | 必用 | 说话方账号 | 区分客服/客户、构建客户维表。 |
| `chat_content` | 必用 | 聊天原文 | AI prompt、会话复盘、证据展示。 |
| `chat_time` | 必用 | 消息时间 | 会话排序、响应时长计算。 |
| `source_create_time` | 预留 | 源表创建时间 | 当前查询很少用；可用于源数据排查。 |
| `message_fingerprint` | 有用但可替代 | 消息兜底指纹 | 当前仅有普通索引；若 `source_id` 稳定可删除。 |
| `row_hash` | 必用 | 原始行内容哈希 | 判断源行是否变化，减少重复写。 |
| `first_seen_batch_id` | 预留 | 首次出现批次 | 当前页面不使用；保留可做数据血缘。 |
| `last_seen_batch_id` | 预留 | 最后出现批次 | 当前页面不使用；保留可做数据血缘。 |

### `ods_qn_shop_record`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `batch_id` | 必用 | 行所属同步批次 | 构建维表、追踪来源。 |
| `source_system` | 必用 | 来源系统 | 唯一约束和构建 JOIN 使用。 |
| `source_id` | 有用但可替代 | 源业务表 ID | 仅溯源；唯一键主要是 `relation_id + business_id`。 |
| `relation_id` | 必用 | 千牛关系 ID | 会话键。 |
| `business_id` | 必用 | 千牛业务 ID | 会话键。 |
| `shop_name` | 必用 | 店铺名称 | 构建 `dim_shop`、页面筛选。 |
| `product_name` | 必用 | 商品名称 | 构建 `dim_product`、页面展示、商品机会。 |
| `product_id` | 必用 | 平台商品 ID | 商品维表唯一性和商品筛选。 |
| `buyer_wangwang` | 必用 | 买家旺旺脱敏展示值 | 客户展示字段。 |
| `seller_wangwang` | 必用 | 客服旺旺账号 | 构建客服、识别说话方、权限链路。 |
| `status` | 必用 | 千牛咨询状态 | 会话状态展示和筛选。 |
| `start_time` | 必用 | 咨询开始时间 | 会话时间、趋势、排序。 |
| `end_time` | 必用 | 咨询结束时间 | 会话结束时间展示。 |
| `chat_content` | 预留 | 业务表聊天摘要 | 当前主要使用聊天明细表，可删除或仅排查保留。 |
| `source_create_time` | 预留 | 源表创建时间 | 当前查询很少用。 |
| `row_hash` | 必用 | 原始行内容哈希 | 判断源行是否变化。 |
| `first_seen_batch_id` | 预留 | 首次出现批次 | 当前页面不使用。 |
| `last_seen_batch_id` | 预留 | 最后出现批次 | 当前页面不使用。 |

## DIM 维度层

### `dim_shop`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `shop_key` | 有用但可替代 | 店铺业务键 | builder 用于幂等；也可用 `source_system + shop_name`。 |
| `source_system` | 必用 | 来源系统 | 唯一约束、构建 JOIN。 |
| `shop_name` | 必用 | 店铺名称 | 页面展示、筛选、分布统计。 |
| `status` | 有用但可替代 | active/disabled | 当前基本固定 active，可由 `is_deleted` 替代。 |

### `dim_product`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `product_key` | 有用但可替代 | 商品业务键 | builder 用于幂等；可用自然唯一键替代。 |
| `source_system` | 必用 | 来源系统 | 构建 JOIN。 |
| `shop_id` | 必用 | 所属店铺 | 商品按店铺唯一，页面统计。 |
| `product_id` | 必用 | 平台商品 ID | 商品筛选和商品机会分析。 |
| `product_name` | 必用 | 商品名 | 页面展示、关键词搜索。 |
| `status` | 有用但可替代 | 商品状态 | 当前基本固定 active。 |

### `dim_staff`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `staff_key` | 有用但可替代 | 客服业务键 | builder 和客服账号页面展示；可用 `source_system + primary_account`。 |
| `staff_name` | 必用 | 客服名称 | 页面展示、搜索、排行。 |
| `primary_account` | 必用 | 客服主旺旺账号 | 构建会话、展示、搜索。 |
| `source_system` | 必用 | 来源系统 | 唯一约束和构建。 |
| `sys_user_id` | 必用 | 绑定系统登录用户 | 客服端权限过滤核心字段。 |
| `status` | 必用 | 客服状态 | 创建账号、列表筛选 active 客服。 |

### `dim_staff_account`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `staff_account_key` | 有用但可替代 | 客服渠道账号业务键 | builder 幂等；可由 `source_system + shop_id + account_name` 替代。 |
| `staff_id` | 必用 | 归属客服 | 客服与店铺账号关系。 |
| `shop_id` | 必用 | 所属店铺 | 一个客服可服务多个店铺。 |
| `source_system` | 必用 | 来源系统 | 唯一约束。 |
| `channel` | 预留 | 渠道，如 qianniu/wechat | 当前固定 `qianniu`；多渠道时才有价值。 |
| `account_name` | 必用 | 平台账号 | 账号关系识别。 |
| `status` | 有用但可替代 | 状态 | 当前基本固定 active。 |

### `dim_customer`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `customer_key` | 有用但可替代 | 客户业务键 | builder 幂等；可用 `first_source + primary_taobao_account`。 |
| `primary_taobao_account` | 必用 | 客户淘宝/旺旺账号 | 客户识别、搜索、展示。 |
| `buyer_wangwang_masked` | 必用 | 买家脱敏展示名 | 页面展示。 |
| `first_source` | 必用 | 首次来源 | 唯一约束和未来多来源客户合并。 |
| `first_seen_at` | 必用 | 首次出现时间 | 客户历史和生命周期。 |
| `last_seen_at` | 必用 | 最近出现时间 | 客户活跃、沉默判断。 |
| `status` | 有用但可替代 | 客户状态 | 当前基本固定 active。 |

### `dim_customer_identity`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `customer_id` | 预留 | 归属客户 | 未来身份打通需要。 |
| `identity_type` | 预留 | 身份类型，如 taobao_account/wechat/phone | 当前只写 taobao_account。 |
| `identity_value` | 预留 | 身份值 | 当前与 `primary_taobao_account` 重复。 |
| `source_system` | 预留 | 身份来源 | 多来源打通时有用。 |
| `confidence` | 预留 | 置信度 | 当前固定 high。 |
| `status` | 预留 | 身份状态 | 当前基本固定 active。 |

结论：如果近期不做微信、手机号、先发客户匹配，`dim_customer_identity` 可以暂时不建或不写。

## DWD 明细层

### `dwd_qn_conversation`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `conversation_key` | 有用但可替代 | 会话业务键 `qianniu|relation|business` | builder 幂等；可由唯一约束字段替代。 |
| `conversation_id` | 必用 | 对外展示会话 ID，如 `conv_xxx` | 前端展示、AI prompt、任务 ID 生成。 |
| `source_system` | 必用 | 来源系统 | 唯一约束和构建。 |
| `relation_id` | 必用 | 千牛关系 ID | 源会话定位。 |
| `business_id` | 必用 | 千牛业务 ID | 源会话定位。 |
| `shop_id` | 必用 | 店铺维表 ID | 店铺筛选和统计。 |
| `product_id` | 必用 | 商品维表 ID | 商品机会和展示。 |
| `staff_id` | 必用 | 客服维表 ID | 权限、排行、筛选。 |
| `customer_id` | 必用 | 客户维表 ID | 客户意向和展示。 |
| `qn_status` | 必用 | 千牛咨询状态 | 页面筛选、展示。 |
| `start_time` | 必用 | 会话开始时间 | 排序、趋势、筛选。 |
| `end_time` | 必用 | 会话结束时间 | 展示。 |
| `message_count` | 必用 | 消息总数 | 列表展示、统计。 |
| `customer_message_count` | 必用 | 客户消息数 | 意向判断、BI。 |
| `staff_message_count` | 必用 | 客服消息数 | 服务分析。 |
| `first_response_seconds` | 必用 | 首响秒数 | 服务质量指标。 |
| `avg_response_seconds` | 必用 | 平均响应秒数 | 服务质量指标。 |
| `qc_status` | 必用 | 质检状态 | 会话列表筛选、任务状态。 |
| `data_hash` | 必用 | 会话数据版本哈希 | 判断会话是否变化，避免重复质检。 |

### `dwd_qn_message`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `message_id` | 必用 | 对外展示消息 ID，如 `msg_xxx` | AI 证据绑定、前端展示。 |
| `conversation_id` | 必用 | 会话主键 ID | 消息归属、详情查询。 |
| `source_system` | 必用 | 来源系统 | 唯一约束。 |
| `source_message_id` | 必用 | 源消息 ID | 溯源和详情展示。 |
| `message_fingerprint` | 有用但可替代 | 消息兜底指纹 | 如果源 ID 稳定，可删除。 |
| `speaker_account` | 必用 | 说话方账号 | 会话复盘、AI prompt。 |
| `speaker_type` | 必用 | staff/customer/unknown | AI prompt、响应计算、展示。 |
| `content_text` | 必用 | 消息正文 | AI、证据、复盘。 |
| `message_time` | 必用 | 消息时间 | 排序、响应时长。 |
| `message_hash` | 有用但可替代 | 消息内容哈希 | 当前展示少用，可由内容实时 hash。 |

### `dwd_customer_staff_relation`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `relation_key` | 疑似冗余 | 客户-客服-店铺关系业务键 | 当前服务基本不查。 |
| `customer_id` | 疑似冗余 | 客户 ID | 可从 `dwd_qn_conversation` 聚合。 |
| `staff_id` | 疑似冗余 | 客服 ID | 可从 `dwd_qn_conversation` 聚合。 |
| `shop_id` | 疑似冗余 | 店铺 ID | 可从 `dwd_qn_conversation` 聚合。 |
| `first_conversation_at` | 疑似冗余 | 首次会话时间 | 可聚合 `MIN(start_time)`。 |
| `last_conversation_at` | 疑似冗余 | 最近会话时间 | 可聚合 `MAX(start_time)`。 |
| `conversation_count` | 疑似冗余 | 会话数 | 可聚合 `COUNT(*)`。 |

结论：这是预聚合表。当前数据量不大时可删除；如果后续客户-客服关系查询很频繁，再保留。

## QC 质检层

### `qc_rule`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `rule_code` | 必用 | 规则编码 | 问题分类、规则版本快照、BI 维度映射。 |
| `rule_name` | 必用 | 规则名称 | 规则页面展示。 |
| `category` | 必用 | 规则分类 | 规则页面筛选。 |
| `judgment_standard` | 必用 | 判断标准 | 发布规则版本、AI prompt。 |
| `deduction_score` | 必用 | 默认扣分 | AI 规则和问题展示。 |
| `severity` | 必用 | 严重程度 | 问题风险统计。 |
| `status` | 必用 | active/inactive | 规则启停。 |

### `qc_prompt_template`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `prompt_version` | 必用 | Prompt 版本 | 任务和规则版本绑定。 |
| `name` | 必用 | 模板名称 | 规则页面展示。 |
| `template_content` | 必用 | Prompt 内容 | AI 执行直接使用。 |
| `output_schema_version` | 必用 | 输出结构版本 | 约束 AI 返回结构。 |
| `status` | 必用 | active/inactive | 模板启停。 |

### `qc_rule_version`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `rule_version` | 必用 | 规则版本号 | 任务创建、结果追溯。 |
| `prompt_version` | 必用 | 使用的 Prompt 版本 | 执行 AI 时加载模板。 |
| `rule_codes` | 必用 | 本版本包含的规则编码 | 版本详情展示和追溯。 |
| `rule_snapshot` | 必用 | 规则快照 JSON | 保证历史任务按当时规则解释。 |
| `status` | 必用 | active/inactive | 版本启停。 |
| `published_at` | 必用 | 发布时间 | 版本管理。 |

### `qc_task`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `task_id` | 必用 | 任务业务 ID | 前端列表展示、调用日志关联、排查。 |
| `conversation_id` | 必用 | 会话主键 ID | 质检哪条会话。 |
| `conversation_data_hash` | 必用 | 创建任务时的会话版本 | 避免同一版本重复质检；会话变化后可重检。 |
| `rule_version` | 必用 | 规则版本 | 加载规则快照。 |
| `prompt_version` | 必用 | Prompt 版本 | 加载模板。 |
| `model_name` | 必用 | AI 模型名 | 执行调用和展示。 |
| `status` | 必用 | pending/running/success/failed | 任务状态。 |
| `response_json` | 必用 | AI 结构化响应 | 商机、意向、联系状态、维度分析会读取。 |
| `error_message` | 必用 | 失败原因 | 任务失败排查。 |
| `started_at` | 必用 | 开始执行时间 | 状态和耗时。 |
| `finished_at` | 必用 | 执行完成时间 | 状态、趋势、耗时。 |

### `qc_result`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `result_id` | 必用 | 结果业务 ID | 详情展示和排查。 |
| `task_id` | 必用 | 质检任务 ID | 结果与任务一对一。 |
| `conversation_id` | 必用 | 会话主键 ID | 结果列表、权限、BI。 |
| `score` | 必用 | 总分 | 工作台、排行、结果页面。 |
| `result_level` | 必用 | pass/fail 等结果等级 | 结果筛选、统计。 |
| `risk_level` | 必用 | 风险等级 | 高风险统计和预警。 |
| `summary` | 必用 | 总结 | 结果详情和列表。 |
| `dimension_scores` | 必用 | 维度分 JSON | 能力雷达、客服表现。 |
| `confidence` | 必用 | AI 置信度 | 结果可信度展示。 |

### `qc_issue`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `issue_id` | 必用 | 问题业务 ID | 详情展示、证据关联排查。 |
| `result_id` | 必用 | 所属质检结果 | 结果详情加载问题。 |
| `rule_code` | 必用 | 命中的规则编码 | 问题分布、维度扣分。 |
| `severity` | 必用 | 严重程度 | 风险统计。 |
| `title` | 必用 | 问题标题 | 页面展示。 |
| `reason` | 必用 | 判断原因 | 页面展示、改进建议。 |
| `suggested_action` | 必用 | 处理建议 | 客服改进。 |
| `suggested_reply` | 必用 | 建议话术 | 客服端可复制使用。 |
| `deduction_score` | 必用 | 扣分 | 总分解释、问题排序。 |

### `qc_issue_evidence`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `evidence_id` | 必用 | 证据业务 ID | 防重复、排查。 |
| `issue_id` | 必用 | 问题 ID | 证据归属。 |
| `message_id` | 必用 | 消息主键 ID | 关联原始消息。 |
| `evidence_text` | 有用但可替代 | 证据文本快照 | 当前详情会 join 消息正文；该字段可作为快照，也可删除。 |

### `model_call_log`

| 字段 | 标记 | 含义 | 当前使用 |
|---|---|---|---|
| `call_id` | 必用 | 调用业务 ID | 调用排查。 |
| `task_id` | 必用 | 关联质检任务 | 找到哪个任务触发了调用。 |
| `model_name` | 必用 | 模型名 | 成本和效果对比。 |
| `request_payload` | 有用但可替代 | 请求摘要 JSON | 当前只存摘要；完整 prompt 未存。 |
| `response_payload` | 必用 | 模型结构化响应 | 排错和重放分析。 |
| `raw_response_text` | 必用 | 模型原始文本 | JSON 解析失败时排查。 |
| `input_tokens` | 预留 | 输入 token | 成本统计，当前依赖模型是否返回。 |
| `output_tokens` | 预留 | 输出 token | 成本统计，当前依赖模型是否返回。 |
| `success` | 必用 | 调用是否成功 | 失败率统计。 |
| `error_message` | 必用 | 调用失败原因 | 排错。 |

## 优先清理建议

| 优先级 | 对象 | 原因 | 建议 |
|---|---|---|---|
| P0 | ODS/DIM/DWD 的 `uuid`、人员审计字段 | 高频同步无业务使用，写入和索引维护有成本 | 删除或不再写入 |
| P0 | `ods_import_batch.checkpoint` | 没有增量同步时无用 | 做增量就保留；否则删除 |
| P1 | `dim_customer_identity` | 当前只重复存淘宝账号 | 做微信/手机号打通前可不写 |
| P1 | `dwd_customer_staff_relation` | 当前可由会话表聚合 | 数据量不大时删除 |
| P1 | `message_fingerprint` | 当前主要靠源 ID 幂等 | 确认源 ID 稳定后删除 |
| P2 | `first_seen_batch_id`、`last_seen_batch_id` | 仅数据血缘，页面不查 | 不做血缘审计可删除 |
| P2 | 各维表 `*_key` | 可由自然唯一键替代 | 若只保留一种唯一键，可删除业务 key |
| P2 | `evidence_text` | 可 join 消息正文 | 若不需要证据快照，可删除 |

## 不建议删除的字段

| 字段 | 原因 |
|---|---|
| `relation_id` + `business_id` | 这是千牛会话聚合的核心自然键。 |
| `source_id` | 聊天明细幂等同步和消息追溯依赖。 |
| `row_hash` / `data_hash` / `conversation_data_hash` | 控制重复同步和重复质检，是性能优化关键。 |
| `dim_staff.sys_user_id` | 客服端权限核心字段。 |
| `dwd_qn_message.message_id` | AI 输出证据 ID 依赖。 |
| `qc_task.response_json` | 当前商机、客户意向、联系方式状态大量从这里解析。 |
| `qc_issue_evidence.message_id` | 扣分和意向判断必须能回到原始消息。 |

## 下一步建议

1. 先确认是否继续保留“全量同步”模式。如果继续全量，`checkpoint` 可以删；如果要提速，应该改成增量同步并启用 `checkpoint`。
2. 先删高频批量表冗余字段，再考虑低频 QC 表。高频表每行都写，收益最大。
3. 不要先删 `source_id`、`row_hash`、`data_hash` 这类看起来像技术字段的列，它们才是同步和重检提速的关键。
4. 如果要做“客户跨渠道身份打通”，保留并扩展 `dim_customer_identity`；否则它现在价值不高。
5. 如果要做“客户-客服关系长期画像”，保留 `dwd_customer_staff_relation`；否则直接从会话表聚合更简单。
