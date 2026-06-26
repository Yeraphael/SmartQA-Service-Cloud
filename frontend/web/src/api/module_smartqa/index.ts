import { request } from "@utils";

const API_PATH = "/smartqa";

const SmartQAAPI = {
  health() {
    return request<ApiResponse<SmartQAHealth>>({
      url: `${API_PATH}/health/status`,
      method: "get",
    });
  },
  dashboardOverview() {
    return request<ApiResponse<DashboardOverview>>({
      url: `${API_PATH}/dashboard/overview`,
      method: "get",
    });
  },
  staffRanking(limit = 20) {
    return request<ApiResponse<StaffRanking[]>>({
      url: `${API_PATH}/dashboard/staff-ranking`,
      method: "get",
      params: { limit },
    });
  },
  shopDistribution() {
    return request<ApiResponse<ShopDistribution[]>>({
      url: `${API_PATH}/dashboard/shop-distribution`,
      method: "get",
    });
  },
  issueDistribution() {
    return request<ApiResponse<IssueDistribution[]>>({
      url: `${API_PATH}/dashboard/issue-distribution`,
      method: "get",
    });
  },
  batchSummary() {
    return request<ApiResponse<QianniuSummary>>({
      url: `${API_PATH}/qianniu/summary`,
      method: "get",
    });
  },
  batches(params: PageQuery & { status?: string; source_type?: string }) {
    return request<ApiResponse<PageResult<ImportBatch>>>({
      url: `${API_PATH}/qianniu/batches`,
      method: "get",
      params,
    });
  },
  syncSourceDb(data: { build: boolean; seed: boolean; truncate_dwd: boolean }) {
    return request<ApiResponse<SyncResult>>({
      url: `${API_PATH}/sync/source-db`,
      method: "post",
      data,
    });
  },
  conversations(params: PageQuery & ConversationQuery) {
    return request<ApiResponse<PageResult<ConversationRow>>>({
      url: `${API_PATH}/conversations/list`,
      method: "get",
      params,
    });
  },
  conversationDetail(id: number) {
    return request<ApiResponse<ConversationDetail>>({
      url: `${API_PATH}/conversations/detail/${id}`,
      method: "get",
    });
  },
  qcTasks(params: { conversation_id?: number; status?: string; limit?: number }) {
    return request<ApiResponse<QcTask[]>>({
      url: `${API_PATH}/qc/tasks`,
      method: "get",
      params,
    });
  },
  createTasks(data: { conversation_ids: number[]; rule_version: string; model_name?: string }) {
    return request<ApiResponse<QcTask[]>>({
      url: `${API_PATH}/qc/tasks`,
      method: "post",
      data,
    });
  },
  executeTasks(data: { task_ids: number[]; batch_size: number }) {
    return request<ApiResponse<QcTaskExecuteResult[]>>({
      url: `${API_PATH}/qc/tasks/execute`,
      method: "post",
      data,
    });
  },
  qcResults(params: PageQuery & QcResultQuery) {
    return request<ApiResponse<PageResult<QcResultRow>>>({
      url: `${API_PATH}/qc/results/list`,
      method: "get",
      params,
    });
  },
  qcResultDetail(id: number) {
    return request<ApiResponse<QcResultDetail>>({
      url: `${API_PATH}/qc/results/detail/${id}`,
      method: "get",
    });
  },
  staffUsers(boundOnly = false) {
    return request<ApiResponse<StaffUser[]>>({
      url: `${API_PATH}/staff-users`,
      method: "get",
      params: { bound_only: boundOnly },
    });
  },
  seedStaffUsers(force = false) {
    return request<ApiResponse<Record<string, unknown>>>({
      url: `${API_PATH}/staff-users/seed`,
      method: "post",
      data: { force },
    });
  },
};

export default SmartQAAPI;

export interface SmartQAHealth {
  module: string;
  status: string;
  ali_model_name: string;
  qc_task_concurrency: number;
  sync_overlap_minutes: number;
}

export interface DashboardOverview {
  conversation_count: number;
  qc_count: number;
  avg_score: number;
  fail_count: number;
  high_risk_count: number;
  issue_count: number;
}

export interface StaffRanking {
  staff_id: number;
  staff_name: string;
  primary_account: string;
  qc_count: number;
  avg_score: number;
  high_risk_count: number;
}

export interface ShopDistribution {
  shop_id: number;
  shop_name: string;
  conversation_count: number;
}

export interface IssueDistribution {
  rule_code: string;
  severity: string;
  issue_count: number;
}

export interface QianniuSummary {
  latest_batch_id?: string;
  latest_status?: string;
  latest_finished_at?: string;
  batch_count: number;
  success_batch_count: number;
  chat_rows: number;
  shop_rows: number;
  conversation_count: number;
}

export interface ImportBatch {
  id: number;
  batch_id: string;
  source_system: string;
  source_type: string;
  checkpoint?: string;
  chat_rows: number;
  shop_rows: number;
  conversation_count: number;
  status: string;
  error_message?: string;
  started_at?: string;
  finished_at?: string;
  created_time?: string;
}

export interface SyncResult {
  batch_id: string;
  chat_rows: number;
  shop_rows: number;
  conversation_count: number;
  elapsed_seconds?: number;
  build_result: Record<string, unknown>;
  seed_result: Record<string, unknown>;
}

export interface ConversationQuery {
  keyword?: string;
  shop_id?: number;
  staff_id?: number;
  customer_id?: number;
  qn_status?: string;
  qc_status?: string;
  start_time?: string;
  end_time?: string;
}

export interface ConversationRow {
  id: number;
  conversation_id: string;
  relation_id: string;
  business_id: string;
  qn_status?: string;
  qc_status: string;
  start_time?: string;
  end_time?: string;
  message_count: number;
  first_response_seconds?: number;
  avg_response_seconds?: number;
  shop_name?: string;
  product_id?: string;
  product_name?: string;
  staff_name?: string;
  staff_account?: string;
  customer_account?: string;
  buyer_wangwang_masked?: string;
}

export interface ConversationDetail {
  conversation: ConversationRow & Record<string, unknown>;
  messages: ConversationMessage[];
}

export interface ConversationMessage {
  id: number;
  message_id: string;
  source_message_id: string;
  speaker_account: string;
  speaker_type: "staff" | "customer" | "unknown";
  content_text?: string;
  message_time: string;
}

export interface QcTask {
  id: number;
  task_id: string;
  conversation_id: number;
  rule_version: string;
  prompt_version: string;
  model_name: string;
  status: string;
  error_message?: string;
  started_at?: string;
  finished_at?: string;
  created_time?: string;
}

export interface QcTaskExecuteResult {
  task_id: string | number;
  status: string;
  result?: Record<string, unknown>;
  error?: string;
}

export interface QcResultQuery {
  keyword?: string;
  staff_id?: number;
  shop_id?: number;
  result_level?: string;
  risk_level?: string;
  start_time?: string;
  end_time?: string;
}

export interface QcResultRow {
  id: number;
  result_id: string;
  score: number;
  result_level: string;
  risk_level: string;
  summary?: string;
  confidence?: number;
  conversation_id: string;
  qn_status?: string;
  start_time?: string;
  shop_name?: string;
  product_name?: string;
  staff_name?: string;
  customer_account?: string;
}

export interface QcResultDetail {
  result: QcResultRow & Record<string, unknown>;
  issues: QcIssue[];
  evidences: QcEvidence[];
}

export interface QcIssue {
  id: number;
  issue_id: string;
  rule_code: string;
  severity: string;
  title: string;
  reason?: string;
  suggested_action?: string;
  suggested_reply?: string;
  deduction_score: number;
}

export interface QcEvidence {
  issue_id: number;
  evidence_id: string;
  message_id: string;
  speaker_type: string;
  speaker_account: string;
  content_text?: string;
  message_time?: string;
}

export interface StaffUser {
  staff_id: number;
  staff_key: string;
  staff_name: string;
  primary_account: string;
  source_system: string;
  status: string;
  sys_user_id?: number;
  username?: string;
  nickname?: string;
  user_status?: number;
}
