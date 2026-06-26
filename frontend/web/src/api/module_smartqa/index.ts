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
  staffPerformance(params?: { staff_id?: number; limit?: number }) {
    return request<ApiResponse<StaffPerformance[]>>({
      url: `${API_PATH}/dashboard/staff-performance`,
      method: "get",
      params,
    });
  },
  improvements(limit = 20, staffId?: number) {
    return request<ApiResponse<ImprovementSummary>>({
      url: `${API_PATH}/dashboard/improvements`,
      method: "get",
      params: { limit, staff_id: staffId },
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
  ensureStaffUser(staffId: number, password = "SmartQA@123456") {
    return request<ApiResponse<Record<string, unknown>>>({
      url: `${API_PATH}/staff-users/${staffId}/ensure`,
      method: "post",
      data: { password },
    });
  },
  resetStaffPassword(staffId: number, password = "SmartQA@123456") {
    return request<ApiResponse<Record<string, unknown>>>({
      url: `${API_PATH}/staff-users/${staffId}/password`,
      method: "put",
      data: { password },
    });
  },
  setStaffUserStatus(staffId: number, status: 0 | 1) {
    return request<ApiResponse<Record<string, unknown>>>({
      url: `${API_PATH}/staff-users/${staffId}/status`,
      method: "patch",
      data: { status },
    });
  },
  rules(params?: { category?: string; status?: string }) {
    return request<ApiResponse<QcRule[]>>({
      url: `${API_PATH}/qc/rules`,
      method: "get",
      params,
    });
  },
  createRule(data: QcRuleForm) {
    return request<ApiResponse<QcRule>>({
      url: `${API_PATH}/qc/rules`,
      method: "post",
      data,
    });
  },
  updateRule(id: number, data: Partial<QcRuleForm>) {
    return request<ApiResponse<QcRule>>({
      url: `${API_PATH}/qc/rules/${id}`,
      method: "put",
      data,
    });
  },
  deleteRule(id: number) {
    return request<ApiResponse<Record<string, unknown>>>({
      url: `${API_PATH}/qc/rules/${id}`,
      method: "delete",
    });
  },
  promptTemplates(params?: { status?: string }) {
    return request<ApiResponse<QcPromptTemplate[]>>({
      url: `${API_PATH}/qc/rules/prompt-templates`,
      method: "get",
      params,
    });
  },
  createPromptTemplate(data: QcPromptTemplateForm) {
    return request<ApiResponse<QcPromptTemplate>>({
      url: `${API_PATH}/qc/rules/prompt-templates`,
      method: "post",
      data,
    });
  },
  updatePromptTemplate(id: number, data: Partial<QcPromptTemplateForm>) {
    return request<ApiResponse<QcPromptTemplate>>({
      url: `${API_PATH}/qc/rules/prompt-templates/${id}`,
      method: "put",
      data,
    });
  },
  ruleVersions(params?: { status?: string }) {
    return request<ApiResponse<QcRuleVersion[]>>({
      url: `${API_PATH}/qc/rules/versions`,
      method: "get",
      params,
    });
  },
  publishRuleVersion(data: { rule_version: string; prompt_version: string; rule_codes: string[] }) {
    return request<ApiResponse<QcRuleVersion>>({
      url: `${API_PATH}/qc/rules/versions/publish`,
      method: "post",
      data,
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
  issue_count?: number;
  conversation_count?: number;
  fail_count?: number;
  high_risk_count: number;
}

export interface StaffPerformance extends StaffRanking {
  conversation_count: number;
  issue_count: number;
  fail_count: number;
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

export interface ImprovementSummary {
  issue_summary: IssueDistribution[];
  frequent_issues: ImprovementIssue[];
  suggested_replies: SuggestedReply[];
  recent_high_risk: RecentHighRisk[];
}

export interface ImprovementIssue {
  rule_code: string;
  severity: string;
  title: string;
  reason?: string;
  suggested_action?: string;
  issue_count: number;
}

export interface SuggestedReply {
  rule_code: string;
  title: string;
  suggested_reply: string;
  issue_count: number;
}

export interface RecentHighRisk {
  result_id: number;
  score: number;
  risk_level: string;
  summary?: string;
  conversation_pk: number;
  conversation_id: string;
  start_time?: string;
  product_name?: string;
  customer_account?: string;
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

export interface QcRule {
  id: number;
  rule_code: string;
  rule_name: string;
  category: string;
  judgment_standard: string;
  deduction_score: number;
  severity: string;
  status: string;
  created_time: string;
  updated_time: string;
}

export interface QcRuleForm {
  rule_code: string;
  rule_name: string;
  category: string;
  judgment_standard: string;
  deduction_score: number;
  severity: string;
  status: string;
}

export interface QcPromptTemplate {
  id: number;
  prompt_version: string;
  name: string;
  template_content: string;
  output_schema_version: string;
  status: string;
  created_time: string;
  updated_time: string;
}

export interface QcPromptTemplateForm {
  prompt_version: string;
  name: string;
  template_content: string;
  output_schema_version: string;
  status: string;
}

export interface QcRuleVersion {
  id: number;
  rule_version: string;
  prompt_version: string;
  rule_codes?: string[];
  rule_snapshot?: Record<string, unknown>;
  status: string;
  published_at?: string;
  created_time: string;
  updated_time: string;
}
