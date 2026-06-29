import axios, { AxiosError } from "axios";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const REMEMBER_ME_KEY = "remember_me";

const api = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API || "/api/v1",
  timeout: Number(import.meta.env.VITE_API_TIMEOUT || 120000),
});

api.interceptors.request.use((config) => {
  const token = Auth.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiResponse<unknown>>) => {
    if (error.response?.status === 401) {
      Auth.clear();
    }
    return Promise.reject(error);
  }
);

export const Auth = {
  getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY) || sessionStorage.getItem(ACCESS_TOKEN_KEY) || "";
  },
  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY) || sessionStorage.getItem(REFRESH_TOKEN_KEY) || "";
  },
  setTokens(accessToken: string, refreshToken: string, rememberMe: boolean) {
    localStorage.setItem(REMEMBER_ME_KEY, String(rememberMe));
    const storage = rememberMe ? localStorage : sessionStorage;
    storage.setItem(ACCESS_TOKEN_KEY, accessToken);
    storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    if (rememberMe) {
      sessionStorage.removeItem(ACCESS_TOKEN_KEY);
      sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    } else {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  },
  rememberMe() {
    return localStorage.getItem(REMEMBER_ME_KEY) === "true";
  },
  clear() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

export const SmartQAService = {
  async login(username: string, password: string, rememberMe: boolean) {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    form.append("login_type", "PC端");
    form.append("grant_type", "password");
    const response = await api.post<ApiResponse<LoginPayload>>("/system/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const data = unwrap(response.data);
    Auth.setTokens(data.access_token, data.refresh_token, rememberMe);
    return data;
  },
  async logout() {
    const token = Auth.getAccessToken();
    if (token) {
      await api.post<ApiResponse<null>>("/system/auth/logout", { token }).catch(() => undefined);
    }
    Auth.clear();
  },
  currentUser() {
    return get<UserInfo>("/system/user/current/info");
  },
  bossWorkbench() {
    return get<BossWorkbench>("/smartqa/dashboard/boss-workbench");
  },
  productOpportunities(limit = 20) {
    return get<ProductOpportunity[]>("/smartqa/dashboard/product-opportunities", { limit });
  },
  conversations(params: PageQuery & ConversationQuery) {
    return get<PageResult<ConversationRow>>("/smartqa/conversations/list", params);
  },
  conversationDetail(id: number) {
    return get<ConversationDetail>(`/smartqa/conversations/detail/${id}`);
  },
  staffUsers(boundOnly = false) {
    return get<StaffUser[]>("/smartqa/staff-users", { bound_only: boundOnly });
  },
  batchSummary() {
    return get<QianniuSummary>("/smartqa/qianniu/summary");
  },
  syncSchedule() {
    return get<SyncSchedule>("/smartqa/sync/schedule");
  },
  syncBatches(limit = 30) {
    return get<ImportBatch[]>("/smartqa/sync/batches", { limit });
  },
  qianniuBatches(params: PageQuery & { status?: string; source_type?: string }) {
    return get<PageResult<ImportBatch>>("/smartqa/qianniu/batches", params);
  },
  syncSourceDb(data = { build: true, seed: true, truncate_dwd: false }) {
    return post<SyncResult>("/smartqa/sync/source-db", data);
  },
  qcTasks(params: { conversation_id?: number; status?: string; limit?: number } = { limit: 50 }) {
    return get<QcTask[]>("/smartqa/qc/tasks", params);
  },
  dailyQcSample(data: { limit: number; execute: boolean; rule_version?: string; model_name?: string }) {
    return post<QcDailySampleResult>("/smartqa/qc/tasks/daily-sample", data);
  },
  rules(params?: { category?: string; status?: string }) {
    return get<QcRule[]>("/smartqa/qc/rules", params);
  },
};

async function get<T>(url: string, params?: object): Promise<T> {
  const response = await api.get<ApiResponse<T>>(url, { params });
  return unwrap(response.data);
}

async function post<T>(url: string, data?: unknown): Promise<T> {
  const response = await api.post<ApiResponse<T>>(url, data);
  return unwrap(response.data);
}

function unwrap<T>(payload: ApiResponse<T>): T {
  if (!payload.success || payload.code !== 200) {
    throw new Error(payload.msg || "请求失败");
  }
  return payload.data as T;
}

export function apiErrorMessage(error: unknown) {
  if (axios.isAxiosError<ApiResponse<unknown>>(error)) {
    return error.response?.data?.msg || error.message || "请求失败";
  }
  if (error instanceof Error) return error.message;
  return "请求失败";
}

export interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T | null;
  status_code: number;
  success: boolean;
}

export interface LoginPayload {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  user_info: UserInfo;
}

export interface UserInfo {
  id: number;
  username: string;
  name?: string;
  nickname?: string;
  avatar?: string;
  is_superuser?: boolean;
  roles?: Array<{ id: number; code?: string; name?: string }>;
}

export interface BossWorkbench {
  status: BossWorkbenchStatus;
  metrics: BossWorkbenchMetrics;
  dimensions: BossDimension[];
  staff_quality: BossStaffQuality[];
  quadrant: BossQuadrant;
  product_opportunities: ProductOpportunity[];
  trend_7d: BossTrendPoint[];
}

export interface BossWorkbenchStatus {
  data_date?: string;
  rpa_fetch_time?: string;
  ai_finished_time?: string;
  analyzed_conversation_count: number;
  covered_staff_count: number;
  system_status: string;
}

export interface BossWorkbenchMetrics {
  service_quality_score: number;
  high_risk_conversation_count: number;
  need_attention_staff_count: number;
  high_intent_pending_count: number;
  avg_response_seconds: number;
  conversation_count: number;
}

export interface BossDimension {
  key:
    | "overall"
    | "response_efficiency"
    | "service_attitude"
    | "professional_ability"
    | "problem_solving"
    | "demand_mining"
    | "conversion_progress";
  label: string;
}

export interface BossStaffQuality {
  staff_id: number;
  staff_name: string;
  primary_account: string;
  role_label: string;
  qc_count: number;
  conversation_count: number;
  overall_score: number;
  dimensions: Record<string, number>;
  high_risk_count: number;
  pending_intent_count: number;
  main_issue: string;
  trend: Array<{ date: string; score: number }>;
}

export interface BossQuadrant {
  x_axis: string;
  y_axis: string;
  points: BossQuadrantPoint[];
}

export interface BossQuadrantPoint {
  staff_id: number;
  staff_name: string;
  x: number;
  y: number;
  score: number;
  status: string;
}

export interface BossTrendPoint {
  date: string;
  quality_score: number;
  high_risk_count: number;
  pending_intent_count: number;
  conversation_count: number;
}

export interface ProductOpportunity {
  product_id?: string;
  product_name: string;
  conversation_count: number;
  h_customer_count: number;
  avg_intent_score: number;
  custom_count: number;
  bulk_count: number;
  price_sensitive_count: number;
  h_customer_rate: number;
}

export interface PageQuery {
  page_no?: number;
  page_size?: number;
}

export interface PageResult<T> {
  page_no: number;
  page_size: number;
  total: number;
  has_next: boolean;
  items: T[];
}

export interface ConversationQuery {
  keyword?: string;
  staff_id?: number;
  qn_status?: string;
  qc_status?: string;
}

export interface ConversationRow {
  id: number;
  conversation_id: string;
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
  id?: number;
  batch_id: string;
  source_system?: string;
  source_type?: string;
  checkpoint?: string;
  chat_rows?: number;
  shop_rows?: number;
  conversation_count?: number;
  status: string;
  error_message?: string;
  started_at?: string;
  finished_at?: string;
  created_time?: string;
}

export interface SyncSchedule {
  scheduler_enabled: boolean;
  scheduler_running: boolean;
  timezone: string;
  source_sync_times: string;
  daily_qc_time: string;
  daily_qc_sample_limit: number;
  daily_qc_execute: boolean;
  jobs: Array<{ id: string; name: string; next_run_time?: string }>;
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

export interface QcDailySampleResult {
  limit: number;
  execute: boolean;
  selected_count: number;
  staff_count: number;
  covered_staff_count: number;
  expanded_for_staff_coverage: boolean;
  conversation_ids: number[];
  staff_ids: number[];
  create_result: {
    created: number;
    skipped: number;
    selected: number;
    task_ids: number[];
    model_name: string;
    rule_version: string;
    prompt_version: string;
  };
  execute_result?: {
    success: number;
    failed: number;
    results: Array<{ task_id: string | number; status: string; error?: string }>;
  };
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
