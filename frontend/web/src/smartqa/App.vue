<template>
  <ElConfigProvider :locale="zhCn" size="default" :z-index="3000">
    <main v-if="!isAuthed" class="login-page">
      <section class="login-brand">
        <div class="brand-hero">
          <img :src="brandLogo" alt="SmartQA" />
          <div>
            <strong>SmartQA</strong>
            <span>Service Cloud</span>
          </div>
        </div>
        <h2>智能质检 · 数据驱动 · 服务升级</h2>
        <p>全面提升客服质量，助力企业服务增长</p>
        <div class="login-illustration">
          <div class="cloud-shape"></div>
          <div class="bar-plate">
            <i v-for="height in [34, 58, 82, 112]" :key="height" :style="{ height: `${height}px` }"></i>
          </div>
          <div class="lens-shape"></div>
          <div class="pie-shape"></div>
        </div>
      </section>

      <section class="login-card">
        <h1>欢迎登录</h1>
        <p>请选择登录身份</p>
        <div class="login-role-tabs">
          <button :class="{ active: loginRole === 'boss' }" type="button" @click="loginRole = 'boss'">
            <ElIcon><UserFilled /></ElIcon>
            老板端
          </button>
          <button :class="{ active: loginRole === 'staff' }" type="button" @click="loginRole = 'staff'">
            <ElIcon><Service /></ElIcon>
            客服端
          </button>
        </div>

        <ElForm class="login-form" label-position="top" @submit.prevent="handleLogin">
          <ElFormItem label="账号">
            <ElInput v-model.trim="loginForm.username" autocomplete="username" placeholder="请输入账号">
              <template #prefix>
                <ElIcon><User /></ElIcon>
              </template>
            </ElInput>
          </ElFormItem>
          <ElFormItem label="密码">
            <ElInput
              v-model="loginForm.password"
              autocomplete="current-password"
              placeholder="请输入密码"
              show-password
              type="password"
              @keyup.enter="handleLogin"
            >
              <template #prefix>
                <ElIcon><Lock /></ElIcon>
              </template>
            </ElInput>
          </ElFormItem>
          <ElButton class="login-submit" :loading="loginLoading" type="primary" @click="handleLogin">登 录</ElButton>
        </ElForm>
        <footer>© 2025 SmartQA Service Cloud. 保留所有权利</footer>
      </section>
    </main>

    <div v-else class="product-shell">
      <aside class="app-sidebar">
        <div class="sidebar-brand">
          <img :src="brandLogo" alt="SmartQA" />
        </div>
        <nav class="sidebar-nav">
          <button
            v-for="item in navItems"
            :key="item.key"
            :class="['side-link', { active: activeView === item.key }]"
            type="button"
            @click="openView(item.key)"
          >
            <ElIcon><component :is="item.icon" /></ElIcon>
            <span>{{ item.label }}</span>
          </button>
        </nav>
        <div class="sidebar-user">
          <AvatarBubble :name="displayName" />
          <div>
            <strong>{{ displayName }}</strong>
            <span>{{ roleMode === 'boss' ? '超级管理员' : '客服专员' }}</span>
          </div>
          <ElIcon><ArrowDown /></ElIcon>
        </div>
      </aside>

      <main class="app-main">
        <header class="app-header">
          <div class="breadcrumb">
            <span>SmartQA</span>
            <b>/</b>
            <span>{{ roleMode === 'boss' ? '我的工作台' : currentTitle }}</span>
            <template v-if="roleMode === 'boss'">
              <b>/</b>
              <strong>{{ currentTitle }}</strong>
            </template>
          </div>
          <div class="header-actions">
            <ElButton text circle><ElIcon><Search /></ElIcon></ElButton>
            <button class="bell-button" type="button">
              <ElIcon><Bell /></ElIcon>
              <i>12</i>
            </button>
            <ElButton text circle @click="toggleFullscreen"><ElIcon><FullScreen /></ElIcon></ElButton>
            <ElButton text circle><ElIcon><Moon /></ElIcon></ElButton>
            <div class="header-user">
              <AvatarBubble :name="displayName" />
              <span>{{ displayName }}</span>
              <ElDropdown trigger="click">
                <ElIcon class="dropdown-trigger"><ArrowDown /></ElIcon>
                <template #dropdown>
                  <ElDropdownMenu>
                    <ElDropdownItem @click="roleMode = isBoss ? 'boss' : 'staff'; activeView = roleMode === 'boss' ? 'boss-workbench' : 'staff-workbench'">
                      返回首页
                    </ElDropdownItem>
                    <ElDropdownItem divided @click="handleLogout">退出登录</ElDropdownItem>
                  </ElDropdownMenu>
                </template>
              </ElDropdown>
            </div>
          </div>
        </header>

        <ElAlert v-if="loadError" class="page-error" :closable="false" type="error" :title="loadError" />

        <StatusStrip :status="statusData" :show-covered="roleMode === 'boss'" />

        <section v-if="activeView === 'boss-workbench'" class="page-content">
          <BossWorkbench />
        </section>
        <section v-else-if="activeView === 'staff-performance'" class="page-content">
          <StaffPerformancePage />
        </section>
        <section v-else-if="activeView === 'customer-opportunity'" class="page-content">
          <CustomerOpportunityPage />
        </section>
        <section v-else-if="activeView === 'product-opportunity'" class="page-content">
          <ProductOpportunityPage />
        </section>
        <section v-else-if="activeView === 'conversation-review'" class="page-content">
          <ConversationReviewPage />
        </section>
        <section v-else-if="activeView === 'rule-config'" class="page-content">
          <RuleConfigPage />
        </section>
        <section v-else-if="activeView === 'staff-account'" class="page-content">
          <StaffAccountPage />
        </section>
        <section v-else-if="activeView === 'data-task'" class="page-content">
          <DataTaskPage />
        </section>
        <section v-else-if="activeView === 'staff-workbench'" class="page-content">
          <StaffWorkbenchPage />
        </section>
        <section v-else-if="activeView === 'staff-followup'" class="page-content">
          <StaffFollowupPage />
        </section>
        <section v-else-if="activeView === 'staff-account-self'" class="page-content">
          <PersonalAccountPage />
        </section>
      </main>
    </div>
  </ElConfigProvider>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from "vue";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import { ElIcon, ElMessage, ElMessageBox } from "element-plus";
import {
  ArrowDown,
  Bell,
  Calendar,
  ChatDotRound,
  CircleCheck,
  Clock,
  Coin,
  Connection,
  DataAnalysis,
  Document,
  Files,
  FullScreen,
  Goods,
  Histogram,
  HomeFilled,
  Link,
  List,
  Lock,
  Management,
  Moon,
  Opportunity,
  Platform,
  QuestionFilled,
  Refresh,
  Search,
  Service,
  Setting,
  StarFilled,
  TrendCharts,
  User,
  UserFilled,
  WarningFilled,
} from "@element-plus/icons-vue";
import brandLogo from "@fa_imgs/smartqa-brand.png";
import {
  apiErrorMessage,
  Auth,
  SmartQAService,
  type BossDimension,
  type BossStaffQuality,
  type BossTrendPoint,
  type BossWorkbench,
  type ConversationDetail,
  type ConversationRow,
  type ImportBatch,
  type ImprovementPayload,
  type IntentCustomer,
  type ProductOpportunity,
  type QcPromptTemplate,
  type QcRule,
  type QcRuleVersion,
  type QcTask,
  type QianniuSummary,
  type StaffPerformanceRow,
  type StaffUser,
  type SyncSchedule,
  type UserInfo,
} from "./api";

type RoleMode = "boss" | "staff";
type NavKey =
  | "boss-workbench"
  | "staff-performance"
  | "customer-opportunity"
  | "product-opportunity"
  | "conversation-review"
  | "rule-config"
  | "staff-account"
  | "data-task"
  | "staff-workbench"
  | "staff-followup"
  | "staff-account-self";

const isAuthed = ref(Boolean(Auth.getAccessToken()));
const loginRole = ref<RoleMode>("boss");
const loginLoading = ref(false);
const loadError = ref("");
const roleMode = ref<RoleMode>("boss");
const activeView = ref<NavKey>("boss-workbench");
const currentUser = ref<UserInfo | null>(null);
const workbench = ref<BossWorkbench | null>(null);
const staffPerformance = ref<StaffPerformanceRow[]>([]);
const intentCustomers = ref<IntentCustomer[]>([]);
const productOpportunities = ref<ProductOpportunity[]>([]);
const improvements = ref<ImprovementPayload | null>(null);
const conversations = reactive<{ items: ConversationRow[]; total: number }>({ items: [], total: 0 });
const conversationDetail = ref<ConversationDetail | null>(null);
const selectedConversationId = ref<number | null>(null);
const staffUsers = ref<StaffUser[]>([]);
const batchSummary = ref<QianniuSummary | null>(null);
const syncSchedule = ref<SyncSchedule | null>(null);
const syncBatches = ref<ImportBatch[]>([]);
const qcTasks = ref<QcTask[]>([]);
const rules = ref<QcRule[]>([]);
const promptTemplates = ref<QcPromptTemplate[]>([]);
const ruleVersions = ref<QcRuleVersion[]>([]);
const selectedStaffId = ref<number | null>(null);
const selectedCustomerId = ref<number | null>(null);
const selectedProductName = ref<string>("");
const activeDimension = ref<BossDimension["key"]>("overall");
const conversationKeyword = ref("");
const customerKeyword = ref("");
const productKeyword = ref("");
const syncing = ref(false);
const runningQc = ref(false);
const appBasePath = (import.meta.env.BASE_URL || "/").replace(/\/+$/, "") || "/";

const loginForm = reactive({
  username: "",
  password: "",
  remember: Auth.rememberMe(),
});

const bossNavItems = [
  { key: "boss-workbench" as const, label: "工作台总览", icon: HomeFilled },
  { key: "staff-performance" as const, label: "客服表现", icon: TrendCharts },
  { key: "customer-opportunity" as const, label: "客户商机", icon: Opportunity },
  { key: "product-opportunity" as const, label: "商品机会", icon: Goods },
  { key: "conversation-review" as const, label: "会话复盘", icon: ChatDotRound },
  { key: "rule-config" as const, label: "规则配置", icon: Files },
  { key: "staff-account" as const, label: "客服账号", icon: User },
  { key: "data-task" as const, label: "数据与任务", icon: Platform },
];

const staffNavItems = [
  { key: "staff-workbench" as const, label: "我的工作台", icon: HomeFilled },
  { key: "staff-followup" as const, label: "客户跟进", icon: Opportunity },
  { key: "conversation-review" as const, label: "会话复盘", icon: ChatDotRound },
  { key: "staff-account-self" as const, label: "个人账号", icon: User },
];

const navItems = computed(() => (roleMode.value === "boss" ? bossNavItems : staffNavItems));
const currentTitle = computed(() => navItems.value.find((item) => item.key === activeView.value)?.label || "工作台总览");
const displayName = computed(() => currentUser.value?.name || currentUser.value?.nickname || currentUser.value?.username || (roleMode.value === "boss" ? "老板" : "客服"));
const isBoss = computed(() => Boolean(currentUser.value?.is_superuser || currentUser.value?.username === "boss"));

const statusData = computed(() => workbench.value?.status || {
  data_date: "",
  rpa_fetch_time: "",
  ai_finished_time: "",
  analyzed_conversation_count: 0,
  covered_staff_count: 0,
  system_status: "待加载",
});

const dimensions = computed<BossDimension[]>(() => workbench.value?.dimensions?.length ? workbench.value.dimensions : [
  { key: "overall", label: "综合表现" },
  { key: "response_efficiency", label: "响应效率" },
  { key: "service_attitude", label: "服务态度" },
  { key: "professional_ability", label: "专业能力" },
  { key: "problem_solving", label: "问题解决" },
  { key: "demand_mining", label: "需求挖掘" },
  { key: "conversion_progress", label: "成交推进" },
]);

const staffRows = computed(() => workbench.value?.staff_quality || []);
const sortedStaff = computed(() => sortStaffByDimension(activeDimension.value));
const selectedStaff = computed(() => staffRows.value.find((row) => row.staff_id === selectedStaffId.value) || sortedStaff.value[0] || null);
const selectedCustomer = computed(() => filteredIntentCustomers.value.find((row) => row.customer_id === selectedCustomerId.value) || filteredIntentCustomers.value[0] || null);
const selectedProduct = computed(() => productOpportunities.value.find((row) => row.product_name === selectedProductName.value) || filteredProducts.value[0] || null);
const myStaff = computed(() => {
  const username = currentUser.value?.username || "";
  return staffRows.value.find((row) => row.primary_account === username || row.staff_name === displayName.value) || selectedStaff.value;
});

const filteredIntentCustomers = computed(() => {
  const keyword = customerKeyword.value.trim();
  if (!keyword) return intentCustomers.value;
  return intentCustomers.value.filter((row) => [row.customer_account, row.customer_alias_masked, row.product_name, row.staff_name].some((value) => String(value || "").includes(keyword)));
});

const filteredProducts = computed(() => {
  const keyword = productKeyword.value.trim();
  if (!keyword) return productOpportunities.value;
  return productOpportunities.value.filter((row) => row.product_name.includes(keyword));
});

const currentRoleIsStaff = computed(() => roleMode.value === "staff");
const staffIntentRows = computed(() => {
  const staff = myStaff.value;
  if (!staff) return intentCustomers.value;
  return intentCustomers.value.filter((row) => row.staff_id === staff.staff_id);
});

watch(staffRows, (rows) => {
  if (!selectedStaffId.value && rows[0]) selectedStaffId.value = rows[0].staff_id;
}, { immediate: true });

watch(filteredIntentCustomers, (rows) => {
  if (!selectedCustomerId.value && rows[0]?.customer_id) selectedCustomerId.value = rows[0].customer_id;
}, { immediate: true });

watch(filteredProducts, (rows) => {
  if (!selectedProductName.value && rows[0]) selectedProductName.value = rows[0].product_name;
}, { immediate: true });

onMounted(async () => {
  normalizeEntryPath();
  if (isAuthed.value) {
    try {
      await loadAll();
      applyRoleHome();
    } catch {
      Auth.clear();
      isAuthed.value = false;
    }
  }
});

async function handleLogin() {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning("请输入账号和密码");
    return;
  }
  loginLoading.value = true;
  try {
    const data = await SmartQAService.login(loginForm.username, loginForm.password, loginForm.remember);
    currentUser.value = data.user_info;
    isAuthed.value = true;
    roleMode.value = loginRole.value === "boss" && (data.user_info.is_superuser || data.user_info.username === "boss") ? "boss" : "staff";
    activeView.value = roleMode.value === "boss" ? "boss-workbench" : "staff-workbench";
    normalizeEntryPath();
    await loadAll();
    ElMessage.success("登录成功");
  } catch (error) {
    ElMessage.error(apiErrorMessage(error));
  } finally {
    loginLoading.value = false;
  }
}

async function handleLogout() {
  await SmartQAService.logout();
  Auth.clear();
  isAuthed.value = false;
  currentUser.value = null;
  roleMode.value = "boss";
  activeView.value = "boss-workbench";
  normalizeEntryPath();
}

function applyRoleHome() {
  roleMode.value = isBoss.value ? "boss" : "staff";
  activeView.value = roleMode.value === "boss" ? "boss-workbench" : "staff-workbench";
}

function openView(key: NavKey) {
  activeView.value = key;
  if (key === "conversation-review" && !conversations.items.length) void loadConversations();
}

function normalizeEntryPath() {
  const desiredPath = appBasePath === "/" ? "/" : appBasePath;
  const currentPath = window.location.pathname.replace(/\/+$/, "") || "/";
  if (currentPath !== desiredPath) {
    window.history.replaceState({}, "", `${desiredPath}${window.location.search}${window.location.hash}`);
  }
}

async function loadAll() {
  loadError.value = "";
  try {
    const [userResult, workbenchResult] = await Promise.all([
      SmartQAService.currentUser().catch(() => currentUser.value),
      SmartQAService.bossWorkbench(),
    ]);
    currentUser.value = userResult;
    workbench.value = workbenchResult;
    productOpportunities.value = workbenchResult.product_opportunities || [];

    const results = await Promise.allSettled([
      SmartQAService.staffPerformance({ limit: 200 }),
      SmartQAService.intentCustomers({ limit: 200 }),
      SmartQAService.productOpportunities(100),
      SmartQAService.improvements({ limit: 30 }),
      SmartQAService.conversations({ page_no: 1, page_size: 20 }),
      SmartQAService.staffUsers(),
      SmartQAService.batchSummary(),
      SmartQAService.syncSchedule(),
      SmartQAService.syncBatches(20),
      SmartQAService.qcTasks({ limit: 80 }),
      SmartQAService.rules(),
      SmartQAService.promptTemplates(),
      SmartQAService.ruleVersions(),
    ]);

    if (results[0].status === "fulfilled") staffPerformance.value = results[0].value;
    if (results[1].status === "fulfilled") intentCustomers.value = results[1].value;
    if (results[2].status === "fulfilled") productOpportunities.value = results[2].value;
    if (results[3].status === "fulfilled") improvements.value = results[3].value;
    if (results[4].status === "fulfilled") {
      conversations.items = results[4].value.items;
      conversations.total = results[4].value.total;
    }
    if (results[5].status === "fulfilled") staffUsers.value = results[5].value;
    if (results[6].status === "fulfilled") batchSummary.value = results[6].value;
    if (results[7].status === "fulfilled") syncSchedule.value = results[7].value;
    if (results[8].status === "fulfilled") syncBatches.value = results[8].value;
    if (results[9].status === "fulfilled") qcTasks.value = results[9].value;
    if (results[10].status === "fulfilled") rules.value = results[10].value;
    if (results[11].status === "fulfilled") promptTemplates.value = results[11].value;
    if (results[12].status === "fulfilled") ruleVersions.value = results[12].value;
  } catch (error) {
    loadError.value = apiErrorMessage(error);
    throw error;
  }
}

async function loadConversations() {
  const data = await SmartQAService.conversations({
    page_no: 1,
    page_size: 20,
    keyword: conversationKeyword.value || undefined,
  });
  conversations.items = data.items;
  conversations.total = data.total;
}

async function openConversation(row: ConversationRow) {
  selectedConversationId.value = row.id;
  conversationDetail.value = await SmartQAService.conversationDetail(row.id);
}

async function triggerSync() {
  syncing.value = true;
  try {
    await SmartQAService.syncSourceDb();
    ElMessage.success("同步任务已完成");
    await loadAll();
  } catch (error) {
    ElMessage.error(apiErrorMessage(error));
  } finally {
    syncing.value = false;
  }
}

async function runDailyQc(execute = true) {
  runningQc.value = true;
  try {
    await SmartQAService.dailyQcSample({ limit: 100, execute });
    ElMessage.success(execute ? "AI抽检已执行" : "AI抽检任务已生成");
    qcTasks.value = await SmartQAService.qcTasks({ limit: 80 });
    workbench.value = await SmartQAService.bossWorkbench();
  } catch (error) {
    ElMessage.error(apiErrorMessage(error));
  } finally {
    runningQc.value = false;
  }
}

async function createOrResetStaff(staff: StaffUser, reset = false) {
  const password = await ElMessageBox.prompt("请输入不少于 8 位的新密码", reset ? "重置密码" : "创建客服账号", {
    confirmButtonText: "确认",
    cancelButtonText: "取消",
    inputPattern: /^.{8,}$/,
    inputErrorMessage: "密码至少 8 位",
  }).then((res) => res.value).catch(() => "");
  if (!password) return;
  try {
    if (reset) await SmartQAService.resetStaffPassword(staff.staff_id, password);
    else await SmartQAService.ensureStaffUser(staff.staff_id, password);
    ElMessage.success(reset ? "密码已重置" : "客服账号已就绪");
    staffUsers.value = await SmartQAService.staffUsers();
  } catch (error) {
    ElMessage.error(apiErrorMessage(error));
  }
}

async function toggleStaffStatus(staff: StaffUser, enabled: boolean) {
  try {
    await SmartQAService.setStaffUserStatus(staff.staff_id, enabled ? "enabled" : "disabled");
    ElMessage.success(enabled ? "账号已启用" : "账号已停用");
    staffUsers.value = await SmartQAService.staffUsers();
  } catch (error) {
    ElMessage.error(apiErrorMessage(error));
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) void document.documentElement.requestFullscreen();
  else void document.exitFullscreen();
}

function sortStaffByDimension(key: string) {
  return [...staffRows.value].sort((a, b) => scoreOf(b, key) - scoreOf(a, key) || b.qc_count - a.qc_count);
}

function scoreOf(staff: BossStaffQuality | null | undefined, key: string) {
  if (!staff) return 0;
  if (key === "overall") return Number(staff.overall_score || 0);
  return Number(staff.dimensions?.[key] || 0);
}

function dimensionWinner(key: string) {
  return sortStaffByDimension(key)[0] || null;
}

function rankDelta(staff: BossStaffQuality, rank: number) {
  const overallRank = sortStaffByDimension("overall").findIndex((row) => row.staff_id === staff.staff_id) + 1;
  return overallRank ? overallRank - rank : 0;
}

function formatNumber(value?: number | null) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function formatScore(value?: number | null) {
  return Number(value || 0).toFixed(1);
}

function formatPercent(value?: number | null) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 10);
}

function formatTime(value?: string | null) {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 16);
}

function formatClock(value?: string | null) {
  if (!value) return "-";
  return value.replace("T", " ").slice(11, 16);
}

function riskText(level?: string) {
  const map: Record<string, string> = { critical: "高风险", high: "高风险", medium: "中风险", low: "低风险", none: "低风险" };
  return map[level || ""] || "低风险";
}

function intentText(tier?: string) {
  const map: Record<string, string> = { H1: "A 高意向", H2: "B 中高意向", H3: "C 中意向", H4: "D 低意向", L: "低意向" };
  return map[tier || ""] || "低意向";
}

function followStatus(row: IntentCustomer) {
  if (!row.quote_given && ["H1", "H2"].includes(row.intent_tier)) return "待报价";
  if (row.missing_infos?.length) return "待补问";
  if (!row.contact_requested && ["H1", "H2"].includes(row.intent_tier)) return "待留资";
  if ((row.silent_hours || 0) >= 24) return "待唤回";
  return "跟进中";
}

function staffGroupLabel(staff?: { group_name?: string | null; shop_name?: string | null } | null) {
  return staff?.group_name || staff?.shop_name || "未分组";
}

function taskDurationMinutes(task?: QcTask | null) {
  if (!task?.started_at || !task.finished_at) return null;
  const started = new Date(task.started_at).getTime();
  const finished = new Date(task.finished_at).getTime();
  if (!Number.isFinite(started) || !Number.isFinite(finished) || finished < started) return null;
  return Math.round((finished - started) / 60000);
}

function averageTaskDurationMinutes() {
  const durations = qcTasks.value.map((task) => taskDurationMinutes(task)).filter((value): value is number => value !== null);
  if (!durations.length) return "-";
  return formatNumber(Math.round(durations.reduce((sum, value) => sum + value, 0) / durations.length));
}

function issueTitle(ruleCode?: string) {
  return rules.value.find((row) => row.rule_code === ruleCode)?.rule_name || ruleCode || "问题标签";
}

function productProblemTags(product?: ProductOpportunity | null) {
  if (!product) return [];
  const rows = intentCustomers.value.filter((row) => row.product_name === product.product_name);
  const tags = new Map<string, number>();
  rows.forEach((row) => {
    [...(row.missing_infos || []), ...(row.tags || []), ...(row.risk_flags || [])].forEach((tag) => tags.set(tag, (tags.get(tag) || 0) + 1));
  });
  return [...tags.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
}

function staffStatus(score: number) {
  if (score >= 90) return "优秀";
  if (score >= 80) return "良好";
  if (score >= 70) return "需关注";
  return "需改进";
}

function scoreTone(score: number) {
  if (score >= 90) return "excellent";
  if (score >= 80) return "good";
  if (score >= 70) return "watch";
  return "risk";
}

function conversationAnalysis(row?: ConversationRow | null) {
  if (!row) return null;
  const intent = intentCustomers.value.find((item) => item.conversation_pk === row.id);
  const risk = improvements.value?.recent_high_risk.find((item) => item.conversation_pk === row.id);
  return { intent, risk };
}

const AvatarBubble = defineComponent({
  props: { name: { type: String, required: true }, size: { type: String, default: "normal" } },
  setup(props) {
    return () => h("b", { class: ["avatar", `avatar-${props.size}`] }, props.name.slice(0, 1));
  },
});

const StatusStrip = defineComponent({
  props: {
    status: { type: Object as () => BossWorkbench["status"], required: true },
    showCovered: { type: Boolean, default: true },
  },
  setup(props) {
    return () => h("div", { class: "status-strip" }, [
      h(StatusInfo, { icon: Calendar, label: "数据日期", value: props.status.data_date ? formatDate(String(props.status.data_date)) : "-" }),
      h(StatusInfo, { icon: Files, label: "RPA 数据时间", value: formatTime(props.status.rpa_fetch_time) }),
      h(StatusInfo, { icon: Clock, label: "AI 分析完成时间", value: formatTime(props.status.ai_finished_time) }),
      h(StatusInfo, { icon: Document, label: "已分析会话数", value: formatNumber(props.status.analyzed_conversation_count) }),
      props.showCovered ? h(StatusInfo, { icon: User, label: "覆盖客服数", value: formatNumber(props.status.covered_staff_count) }) : null,
      h(StatusInfo, { icon: Setting, label: "系统状态", value: props.status.system_status || "待加载", status: true }),
    ]);
  },
});

const StatusInfo = defineComponent({
  props: {
    icon: { type: Object, required: true },
    label: { type: String, required: true },
    value: { type: String, required: true },
    status: { type: Boolean, default: false },
  },
  setup(props) {
    return () => h("div", { class: "status-info" }, [
      h(ElIcon, null, () => h(props.icon)),
      h("span", props.label + "："),
      h("strong", { class: props.status ? "green-dot" : "" }, props.value),
    ]);
  },
});

const MetricCard = defineComponent({
  props: {
    icon: { type: Object, required: true },
    title: { type: String, required: true },
    value: { type: String, required: true },
    suffix: { type: String, default: "" },
    change: { type: String, default: "" },
    tone: { type: String, default: "blue" },
  },
  setup(props) {
    return () => h("div", { class: ["metric-card", props.tone] }, [
      h("div", { class: "metric-icon" }, [h(ElIcon, null, () => h(props.icon))]),
      h("div", { class: "metric-body" }, [
        h("span", props.title),
        h("strong", [props.value, props.suffix ? h("em", props.suffix) : null]),
        props.change ? h("small", props.change) : null,
      ]),
    ]);
  },
});

const PanelHeader = defineComponent({
  props: { title: { type: String, required: true }, subtitle: { type: String, default: "" } },
  setup(props, { slots }) {
    return () => h("div", { class: "panel-header" }, [
      h("div", [h("h3", props.title), props.subtitle ? h("span", props.subtitle) : null]),
      slots.default?.(),
    ]);
  },
});

const EmptyState = defineComponent({
  props: { text: { type: String, default: "暂无数据" } },
  setup(props) {
    return () => h("div", { class: "empty-state" }, props.text);
  },
});

const MiniLine = defineComponent({
  props: { points: { type: Array as () => Array<{ score?: number; value?: number }>, default: () => [] }, tone: { type: String, default: "green" } },
  setup(props) {
    return () => {
      const values = props.points.length ? props.points.map((item) => Number(item.score ?? item.value ?? 0)) : [0, 0, 0, 0];
      const max = Math.max(...values, 100);
      const min = Math.min(...values, 0);
      const width = 96;
      const height = 28;
      const path = values.map((value, index) => {
        const x = values.length === 1 ? 0 : (index * width) / (values.length - 1);
        const y = height - ((value - min) / Math.max(max - min, 1)) * height;
        return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(" ");
      return h("svg", { class: ["mini-line", props.tone], viewBox: `0 0 ${width} ${height}` }, [h("path", { d: path })]);
    };
  },
});

const HexRadar = defineComponent({
  props: { staff: { type: Object as () => BossStaffQuality, required: true }, compact: { type: Boolean, default: false } },
  setup(props) {
    return () => {
      const axis: Array<[string, string]> = [
        ["服务态度", "service_attitude"],
        ["响应效率", "response_efficiency"],
        ["专业能力", "professional_ability"],
        ["问题解决", "problem_solving"],
        ["需求挖掘", "demand_mining"],
        ["风险控制", "conversion_progress"],
      ];
      const cx = 150;
      const cy = 126;
      const radius = props.compact ? 70 : 82;
      const polygon = axis.map(([, key], index) => {
        const angle = -Math.PI / 2 + (Math.PI * 2 * index) / axis.length;
        const r = (Math.max(Math.min(scoreOf(props.staff, key), 100), 0) / 100) * radius;
        return `${cx + Math.cos(angle) * r},${cy + Math.sin(angle) * r}`;
      }).join(" ");
      const grid = [0.25, 0.5, 0.75, 1].map((scale) => axis.map((_, index) => {
        const angle = -Math.PI / 2 + (Math.PI * 2 * index) / axis.length;
        return `${cx + Math.cos(angle) * radius * scale},${cy + Math.sin(angle) * radius * scale}`;
      }).join(" "));
      return h("svg", { class: ["hex-radar", { compact: props.compact }], viewBox: "0 0 300 260" }, [
        ...grid.map((points) => h("polygon", { class: "radar-grid", points })),
        h("polygon", { class: "radar-area", points: polygon }),
        ...axis.map(([label, key], index) => {
          const angle = -Math.PI / 2 + (Math.PI * 2 * index) / axis.length;
          const x = cx + Math.cos(angle) * (radius + 34);
          const y = cy + Math.sin(angle) * (radius + 24);
          return h("g", [
            h("text", { class: "radar-label", x, y, "text-anchor": "middle" }, label),
            h("text", { class: "radar-score", x, y: y + 16, "text-anchor": "middle" }, formatScore(scoreOf(props.staff, key))),
          ]);
        }),
      ]);
    };
  },
});

const TrendChart = defineComponent({
  props: { points: { type: Array as () => BossTrendPoint[], default: () => [] }, staff: { type: Object as () => BossStaffQuality | null, default: null }, simple: { type: Boolean, default: false } },
  setup(props) {
    return () => {
      const width = 720;
      const height = 250;
      const pad = 34;
      const staffTrend = props.staff?.trend || [];
      const dates = props.simple && staffTrend.length ? staffTrend.map((row) => row.date) : props.points.map((row) => row.date);
      const quality = props.simple && staffTrend.length ? staffTrend.map((row) => row.score) : props.points.map((row) => row.quality_score);
      const risk = props.points.map((row) => row.high_risk_count);
      const intent = props.points.map((row) => row.pending_intent_count);
      const x = (index: number) => pad + (index * (width - pad * 2)) / Math.max(dates.length - 1, 1);
      const yScore = (value: number) => height - pad - (Math.max(Math.min(value, 100), 0) / 100) * (height - pad * 2);
      const maxCount = Math.max(...risk, ...intent, 10);
      const yCount = (value: number) => height - pad - (value / maxCount) * (height - pad * 2);
      const line = (values: number[], y: (v: number) => number) => values.map((value, index) => `${x(index)},${y(value)}`).join(" ");
      return h("svg", { class: "trend-chart", viewBox: `0 0 ${width} ${height}` }, [
        h("line", { class: "chart-axis", x1: pad, y1: height - pad, x2: width - pad, y2: height - pad }),
        h("line", { class: "chart-axis", x1: pad, y1: pad, x2: pad, y2: height - pad }),
        h("polyline", { class: "trend-line quality", points: line(quality, yScore) }),
        props.simple ? null : h("polyline", { class: "trend-line risk", points: line(risk, yCount) }),
        props.simple ? null : h("polyline", { class: "trend-line intent", points: line(intent, yCount) }),
        ...quality.map((value, index) => h("text", { class: "point-label quality", x: x(index), y: yScore(value) - 8, "text-anchor": "middle" }, formatScore(value))),
        ...dates.map((date, index) => h("text", { class: "chart-date", x: x(index), y: height - 10, "text-anchor": "middle" }, date)),
      ]);
    };
  },
});

const QuadrantChart = defineComponent({
  props: { selectedId: { type: Number, default: null } },
  emits: ["select"],
  setup(props, { emit }) {
    return () => h("div", { class: "quadrant" }, [
      h("span", { class: "quadrant-axis y" }, "服务能力分"),
      h("span", { class: "quadrant-axis x" }, "服务效率分"),
      h("i", { class: "quad-v" }),
      h("i", { class: "quad-h" }),
      h("b", { class: "quad-label lt" }, ["质量优秀", h("br"), "效率待提升"]),
      h("b", { class: "quad-label rt" }, ["质量优秀 效率优秀", h("br"), "优秀客服"]),
      h("b", { class: "quad-label lb" }, ["质量待提升", h("br"), "效率待提升"]),
      h("b", { class: "quad-label rb" }, ["效率优秀", h("br"), "质量待提升"]),
      ...(workbench.value?.quadrant.points || []).map((point) => h("button", {
        class: ["quad-point", { active: props.selectedId === point.staff_id }],
        style: { left: `${Math.max(5, Math.min(point.x, 95))}%`, bottom: `${Math.max(7, Math.min(point.y, 92))}%` },
        type: "button",
        onClick: () => emit("select", point.staff_id),
      }, point.staff_name)),
    ]);
  },
});

const BossWorkbench = defineComponent({
  setup() {
    return () => h("div", { class: "boss-workbench" }, [
      h("div", { class: "metric-grid five" }, [
        h(MetricCard, { icon: StarFilled, title: "总体服务质量分", value: formatScore(workbench.value?.metrics.service_quality_score), tone: "blue" }),
        h(MetricCard, { icon: WarningFilled, title: "高风险会话数", value: formatNumber(workbench.value?.metrics.high_risk_conversation_count), tone: "red" }),
        h(MetricCard, { icon: UserFilled, title: "高意向未跟进数", value: formatNumber(workbench.value?.metrics.high_intent_pending_count), tone: "orange" }),
        h(MetricCard, { icon: Clock, title: "平均响应时长", value: formatNumber(workbench.value?.metrics.avg_response_seconds), suffix: "秒", tone: "purple" }),
        h(MetricCard, { icon: ChatDotRound, title: "已分析会话数", value: formatNumber(workbench.value?.metrics.conversation_count), tone: "green" }),
      ]),
      h("div", { class: "workbench-grid" }, [
        h("section", { class: "panel ranking-card" }, [
          h(PanelHeader, { title: "客服质检维度" }, () => [
            h("div", { class: "mini-filters" }, [h("button", "按日查看"), h("button", "近7天")]),
          ]),
          h("div", { class: "dimension-cards" }, dimensions.value.map((dim) => {
            const winner = dimensionWinner(dim.key);
            return h("button", { class: ["dimension-card", { active: activeDimension.value === dim.key }], type: "button", onClick: () => (activeDimension.value = dim.key) }, [
              h("span", dim.label),
              h("div", [winner ? h(AvatarBubble, { name: winner.staff_name, size: "small" }) : null, h("b", winner?.staff_name || "-")]),
              h("strong", formatScore(scoreOf(winner, dim.key))),
            ]);
          })),
          h("div", { class: "quality-table boss" }, [
            h("div", { class: "quality-head boss" }, ["排名", "客服", "本维度得分", "综合得分", "排名变化", "趋势", "主要问题", "状态", "所属组"].map((text) => h("span", text))),
            ...sortedStaff.value.map((staff, index) => h("button", {
              class: ["quality-row boss", { selected: selectedStaff.value?.staff_id === staff.staff_id }],
              type: "button",
              onMouseenter: () => (selectedStaffId.value = staff.staff_id),
              onClick: () => (selectedStaffId.value = staff.staff_id),
            }, [
              h("span", { class: "rank" }, index < 3 ? ["🥇", "🥈", "🥉"][index] : String(index + 1)),
              h("span", { class: "staff-name" }, [h(AvatarBubble, { name: staff.staff_name, size: "small" }), h("em", [h("strong", staff.staff_name), h("small", staff.primary_account || "客服账号")])]),
              h("strong", { class: scoreTone(scoreOf(staff, activeDimension.value)) }, formatScore(scoreOf(staff, activeDimension.value))),
              h("span", formatScore(staff.overall_score)),
              h("span", { class: rankDelta(staff, index + 1) >= 0 ? "up" : "down" }, rankDelta(staff, index + 1) === 0 ? "-" : `${rankDelta(staff, index + 1) > 0 ? "↑" : "↓"} ${Math.abs(rankDelta(staff, index + 1))}`),
              h(MiniLine, { points: staff.trend, tone: staff.overall_score >= 80 ? "green" : "red" }),
              h("span", { class: "issue" }, staff.main_issue || "暂无明显问题"),
              h("span", { class: ["tag", scoreTone(scoreOf(staff, activeDimension.value))] }, staffStatus(scoreOf(staff, activeDimension.value))),
              h("span", staffGroupLabel(staff)),
            ])),
            !sortedStaff.value.length ? h(EmptyState) : null,
          ]),
        ]),
        h("section", { class: "middle-column" }, [
          h(StaffDetailPanel),
          h(ProductTopPanel),
        ]),
        h("section", { class: "right-column" }, [
          h("div", { class: "panel" }, [h(PanelHeader, { title: "客服能力四象限", subtitle: "近7天" }), h(QuadrantChart, { selectedId: selectedStaff.value?.staff_id || undefined, onSelect: (id: number) => (selectedStaffId.value = id) })]),
          h("div", { class: "panel" }, [h(PanelHeader, { title: "近7天趋势" }), h("div", { class: "chart-legend" }, [h("span", "质量分"), h("span", "高风险对话"), h("span", "高意向未跟进")]), h(TrendChart, { points: workbench.value?.trend_7d || [] })]),
        ]),
      ]),
    ]);
  },
});

const StaffDetailPanel = defineComponent({
  setup() {
    return () => h("div", { class: "panel staff-detail-panel" }, selectedStaff.value ? [
      h(PanelHeader, { title: "客服详情" }),
      h("div", { class: "staff-detail-head" }, [
        h(AvatarBubble, { name: selectedStaff.value.staff_name, size: "large" }),
        h("div", [h("h3", selectedStaff.value.staff_name), h("span", [h("i", { class: "tag good" }, staffStatus(selectedStaff.value.overall_score)), ` ${staffGroupLabel(selectedStaff.value)} ｜ 角色：${selectedStaff.value.role_label}`])]),
      ]),
      h("div", { class: "score-line" }, [h("span", "综合得分"), h("strong", formatScore(selectedStaff.value.overall_score)), h("em", "/100"), h("small", `排名 ${sortStaffByDimension("overall").findIndex((row) => row.staff_id === selectedStaff.value?.staff_id) + 1} / ${staffRows.value.length}`)]),
      h(HexRadar, { staff: selectedStaff.value }),
      h("div", { class: "detail-stats" }, [
        h("div", [h("span", "高风险会话"), h("strong", String(selectedStaff.value.high_risk_count || 0))]),
        h("div", [h("span", "高意向未跟进"), h("strong", String(selectedStaff.value.pending_intent_count || 0))]),
      ]),
      h("div", { class: "suggestion-box" }, [
        h("h4", "改进建议"),
        ...((improvements.value?.frequent_issues || []).slice(0, 3).map((issue) => h("p", `• ${issue.suggested_action || issue.title}`))),
      ]),
    ] : [h(EmptyState)]);
  },
});

const ProductTopPanel = defineComponent({
  setup() {
    return () => h("div", { class: "panel product-top-panel" }, [
      h(PanelHeader, { title: "商品机会 Top 5" }),
      h("div", { class: "product-mini-table" }, [
        h("div", { class: "product-mini-head" }, ["排名", "产品名称", "相关会话数", "高意向数", "转化潜力"].map((text) => h("span", text))),
        ...productOpportunities.value.slice(0, 5).map((item, index) => h("button", { class: "product-mini-row", type: "button", onClick: () => { selectedProductName.value = item.product_name; activeView.value = "product-opportunity"; } }, [
          h("span", String(index + 1)),
          h("strong", item.product_name),
          h("span", formatNumber(item.conversation_count)),
          h("span", formatNumber(item.h_customer_count)),
          h("span", "★★★★★".slice(0, Math.max(1, Math.round((item.h_customer_rate || 0) / 20)))),
        ])),
        !productOpportunities.value.length ? h(EmptyState) : null,
      ]),
    ]);
  },
});

const StaffPerformancePage = defineComponent({
  setup() {
    return () => h("div", { class: "staff-performance-page" }, [
      h("div", { class: "filter-bar" }, ["日期 近7天", "客服组 全部", "客服 全部", "商品 全部", "维度 综合维度", "状态 全部"].map((text) => h("button", text))),
      h("div", { class: "dimension-summary" }, dimensions.value.map((dim) => {
        const winner = dimensionWinner(dim.key);
        return h("button", { class: ["dimension-summary-card", { active: activeDimension.value === dim.key }], type: "button", onClick: () => (activeDimension.value = dim.key) }, [
          h("span", dim.label),
          h("strong", formatScore(winner ? scoreOf(winner, dim.key) : 0)),
          h("small", `TOP 1 ${winner?.staff_name || "-"}`),
          h(MiniLine, { points: winner?.trend || [] }),
        ]);
      })),
      h("div", { class: "performance-grid" }, [
        h("div", { class: "panel heatmap-panel" }, [
          h(PanelHeader, { title: "客服维度热力矩阵" }),
          h("div", { class: "heatmap" }, [
            h("div", { class: "heat-head" }, ["客服", ...dimensions.value.filter((dim) => dim.key !== "overall").map((dim) => dim.label), "综合分"].map((text) => h("span", text))),
            ...sortedStaff.value.slice(0, 10).map((staff) => h("button", { class: "heat-row", type: "button", onClick: () => (selectedStaffId.value = staff.staff_id) }, [
              h("span", { class: "staff-name" }, [h(AvatarBubble, { name: staff.staff_name, size: "small" }), staff.staff_name]),
              ...dimensions.value.filter((dim) => dim.key !== "overall").map((dim) => h("b", { class: scoreTone(scoreOf(staff, dim.key)) }, formatScore(scoreOf(staff, dim.key)))),
              h("strong", formatScore(staff.overall_score)),
            ])),
          ]),
          h("div", { class: "quality-table compact" }, [
            h("div", { class: "quality-head compact" }, ["排名", "客服", "本维度得分", "综合分", "排名变化", "主要问题", "影响会话数", "状态", "证据入口"].map((text) => h("span", text))),
            ...sortedStaff.value.slice(0, 12).map((staff, index) => h("button", { class: ["quality-row compact", { selected: selectedStaffId.value === staff.staff_id }], type: "button", onClick: () => (selectedStaffId.value = staff.staff_id) }, [
              h("span", String(index + 1)),
              h("span", { class: "staff-name" }, [h(AvatarBubble, { name: staff.staff_name, size: "small" }), staff.staff_name]),
              h("strong", { class: scoreTone(scoreOf(staff, activeDimension.value)) }, formatScore(scoreOf(staff, activeDimension.value))),
              h("span", formatScore(staff.overall_score)),
              h("span", rankDelta(staff, index + 1) ? String(rankDelta(staff, index + 1)) : "-"),
              h("span", { class: "issue" }, staff.main_issue || "暂无明显问题"),
              h("span", formatNumber(staff.conversation_count)),
              h("span", { class: ["tag", scoreTone(staff.overall_score)] }, staffStatus(staff.overall_score)),
              h("span", "查看证据"),
            ])),
          ]),
        ]),
        h("div", { class: "right-detail-stack" }, [h(StaffDetailPanel), h("div", { class: "panel issue-card" }, [
          h(PanelHeader, { title: "问题 Top 5" }),
          ...(improvements.value?.frequent_issues || []).slice(0, 5).map((issue) => h("span", { class: "issue-pill" }, `${issue.title} ${issue.issue_count}`)),
        ]), h("div", { class: "panel" }, [h(PanelHeader, { title: "近 7 天趋势", subtitle: "单位：分" }), h(TrendChart, { points: workbench.value?.trend_7d || [], staff: selectedStaff.value, simple: true })])]),
      ]),
    ]);
  },
});

const CustomerOpportunityPage = defineComponent({
  setup() {
    return () => {
      const pendingQuote = intentCustomers.value.filter((row) => !row.quote_given && ["H1", "H2"].includes(row.intent_tier)).length;
      const missing = intentCustomers.value.filter((row) => row.missing_infos?.length).length;
      const silent = intentCustomers.value.filter((row) => (row.silent_hours || 0) >= 24).length;
      return h("div", { class: "customer-page" }, [
        h("div", { class: "metric-grid five" }, [
          h(MetricCard, { icon: UserFilled, title: "高意向客户数", value: formatNumber(intentCustomers.value.filter((row) => ["H1", "H2"].includes(row.intent_tier)).length), tone: "blue" }),
          h(MetricCard, { icon: Clock, title: "待跟进客户数", value: formatNumber(filteredIntentCustomers.value.length), tone: "orange" }),
          h(MetricCard, { icon: Coin, title: "未报价客户数", value: formatNumber(pendingQuote), tone: "green" }),
          h(MetricCard, { icon: QuestionFilled, title: "未确认需求客户数", value: formatNumber(missing), tone: "purple" }),
          h(MetricCard, { icon: Bell, title: "沉默客户数", value: formatNumber(silent), tone: "red" }),
        ]),
        h("div", { class: "opportunity-stage-row" }, ["高意向待成交", "待报价", "待补问", "待留资", "待唤回"].map((title) => h("div", { class: "stage-card" }, [h("strong", title), h("b", formatNumber(intentCustomers.value.filter((row) => followStatus(row).includes(title.replace("高意向待成交", ""))).length || 0)), h("small", "转化率 " + formatPercent(0))]))),
        h("div", { class: "customer-grid" }, [
          h("div", { class: "panel" }, [
            h(PanelHeader, { title: "客户商机列表" }, () => h("input", { class: "search-input", placeholder: "搜索客户名称", value: customerKeyword.value, onInput: (event: Event) => (customerKeyword.value = (event.target as HTMLInputElement).value) })),
            h("div", { class: "customer-table" }, [
              h("div", { class: "customer-head" }, ["客户", "咨询商品", "负责客服", "意向等级", "意向原因", "当前状态", "建议动作", "最后互动", "证据入口"].map((text) => h("span", text))),
              ...filteredIntentCustomers.value.slice(0, 12).map((row) => h("button", { class: ["customer-row", { selected: selectedCustomer.value?.conversation_pk === row.conversation_pk }], type: "button", onClick: () => (selectedCustomerId.value = row.customer_id || null) }, [
                h("strong", row.customer_alias_masked || row.customer_account || "-"),
                h("span", row.product_name || "-"),
                h("span", row.staff_name || "-"),
                h("i", { class: ["tag", ["H1", "H2"].includes(row.intent_tier) ? "risk" : "watch"] }, intentText(row.intent_tier)),
                h("span", row.intent_reason_text || row.need_summary || "-"),
                h("i", { class: "tag watch" }, followStatus(row)),
                h("span", row.next_action || "-"),
                h("span", formatTime(row.end_time || row.start_time)),
                h("span", "证据"),
              ])),
              !filteredIntentCustomers.value.length ? h(EmptyState) : null,
            ]),
          ]),
          h(CustomerDetailPanel),
        ]),
      ]);
    };
  },
});

const CustomerDetailPanel = defineComponent({
  setup() {
    return () => h("div", { class: "panel customer-detail-panel" }, selectedCustomer.value ? [
      h(PanelHeader, { title: "客户详情" }, () => h("button", { class: "outline-btn", onClick: () => { activeView.value = "conversation-review"; selectedConversationId.value = selectedCustomer.value?.conversation_pk || null; } }, "查看完整档案")),
      h("div", { class: "customer-profile" }, [
        h("div", { class: "product-logo" }, (selectedCustomer.value.product_name || "商").slice(0, 2)),
        h("div", [h("h3", selectedCustomer.value.customer_alias_masked || selectedCustomer.value.customer_account || "客户"), h("span", [selectedCustomer.value.product_name || "-", " ｜ ", selectedCustomer.value.staff_name || "-"])]),
        h("strong", formatScore(selectedCustomer.value.intent_score)),
      ]),
      h("div", { class: "detail-two" }, [
        h("div", [h("h4", "意向判断"), h("strong", `${formatScore(selectedCustomer.value.intent_score)} /100`), h("p", intentText(selectedCustomer.value.intent_tier))]),
        h("div", [h("h4", "当前缺口概览"), h("div", { class: "status-boxes" }, ["报价", "需求确认", "留资", "唤回"].map((name) => h("span", { class: followStatus(selectedCustomer.value!).includes(name.replace("需求确认", "补问")) ? "todo" : "done" }, name)))]),
      ]),
      h("div", { class: "timeline-box" }, [h("h4", "互动记录"), h("p", selectedCustomer.value.need_summary || selectedCustomer.value.summary || "暂无摘要")]),
      h("div", { class: "suggestion-box" }, [h("h4", "建议动作"), h("p", selectedCustomer.value.next_action || "-"), h("h4", "建议话术"), h("p", selectedCustomer.value.suggested_reply || "请结合会话证据补齐客户需求并推进下一步。")]),
    ] : [h(EmptyState)]);
  },
});

const ProductOpportunityPage = defineComponent({
  setup() {
    return () => h("div", { class: "product-page" }, [
      h("div", { class: "metric-grid four" }, [
        h(MetricCard, { icon: Goods, title: "咨询商品数", value: formatNumber(productOpportunities.value.length), tone: "blue" }),
        h(MetricCard, { icon: ChatDotRound, title: "咨询会话数", value: formatNumber(productOpportunities.value.reduce((sum, row) => sum + row.conversation_count, 0)), tone: "green" }),
        h(MetricCard, { icon: Opportunity, title: "高意向商品数", value: formatNumber(productOpportunities.value.filter((row) => row.h_customer_count > 0).length), tone: "orange" }),
        h(MetricCard, { icon: QuestionFilled, title: "高频问题数", value: formatNumber(productOpportunities.value.reduce((sum, row) => sum + row.price_sensitive_count, 0)), tone: "purple" }),
      ]),
      h("div", { class: "product-grid" }, [
        h("div", { class: "panel product-rank-panel" }, [
          h(PanelHeader, { title: "商品机会排行" }, () => h("input", { class: "search-input", placeholder: "搜索商品名称", value: productKeyword.value, onInput: (event: Event) => (productKeyword.value = (event.target as HTMLInputElement).value) })),
          h("div", { class: "product-table" }, [
            h("div", { class: "product-head" }, ["排名", "商品", "咨询数", "高意向数", "转化潜力", "常见问题", "常见异议", "证据入口"].map((text) => h("span", text))),
            ...filteredProducts.value.slice(0, 14).map((row, index) => h("button", { class: ["product-row-full", { selected: selectedProduct.value?.product_name === row.product_name }], type: "button", onClick: () => (selectedProductName.value = row.product_name) }, [
              h("span", index < 3 ? ["🥇", "🥈", "🥉"][index] : String(index + 1)),
              h("strong", row.product_name),
              h("span", formatNumber(row.conversation_count)),
              h("span", formatNumber(row.h_customer_count)),
              h("span", "★★★★★".slice(0, Math.max(1, Math.round((row.h_customer_rate || 0) / 20)))),
              h("span", formatNumber(row.price_sensitive_count)),
              h("span", formatNumber(row.custom_count + row.bulk_count)),
              h("span", "证据"),
            ])),
            !filteredProducts.value.length ? h(EmptyState) : null,
          ]),
        ]),
        h(ProductDetailPanel),
      ]),
    ]);
  },
});

const ProductDetailPanel = defineComponent({
  setup() {
    return () => h("div", { class: "product-detail-stack" }, selectedProduct.value ? [
      h("div", { class: "panel product-detail-card" }, [
        h("div", { class: "product-detail-head" }, [
          h("div", { class: "product-cover" }, selectedProduct.value.product_name.slice(0, 2)),
          h("div", [h("h3", selectedProduct.value.product_name), h("span", "AI 识别的商品机会与客户问题")]),
          h("i", { class: "tag watch" }, "当前选中"),
        ]),
        h("div", { class: "product-overview" }, [
          h("div", [h("span", "咨询数"), h("strong", formatNumber(selectedProduct.value.conversation_count))]),
          h("div", [h("span", "高意向数"), h("strong", formatNumber(selectedProduct.value.h_customer_count))]),
          h("div", [h("span", "转化潜力"), h("strong", formatPercent(selectedProduct.value.h_customer_rate))]),
        ]),
      ]),
      h("div", { class: "panel" }, [h(PanelHeader, { title: "常见异议分布" }), h("div", { class: "objection-tags" }, productProblemTags(selectedProduct.value).map(([tag, count]) => h("span", [h("b", tag), h("em", `${count} 次`)]))), !productProblemTags(selectedProduct.value).length ? h(EmptyState) : null]),
      h("div", { class: "panel" }, [h(PanelHeader, { title: "典型会话 Evidence" }), ...(intentCustomers.value.filter((row) => row.product_name === selectedProduct.value?.product_name).slice(0, 4).map((row) => h("button", { class: "evidence-row", type: "button", onClick: () => { activeView.value = "conversation-review"; selectedConversationId.value = row.conversation_pk; } }, [h("span", row.intent_reason_text || row.need_summary || "客户咨询"), h("em", formatTime(row.start_time))])))]),
      h("div", { class: "panel suggestion-columns" }, [h(PanelHeader, { title: "优化建议" }), h("p", "商品详情优化：补齐客户高频问题对应的信息。"), h("p", "客服话术优化：围绕价格、规格、交期与定制问题形成标准答复。"), h("p", "培训重点：结合典型会话 Evidence 复盘客服解释和推进方式。")]),
    ] : [h("div", { class: "panel" }, [h(EmptyState)])]);
  },
});

const ConversationReviewPage = defineComponent({
  setup() {
    return () => {
      const selected = conversations.items.find((row) => row.id === selectedConversationId.value) || conversations.items[0] || null;
      const analysis = conversationAnalysis(selected);
      const messages = conversationDetail.value?.conversation.id === selected?.id ? conversationDetail.value?.messages || [] : [];
      return h("div", { class: "review-layout" }, [
        h("aside", { class: "panel review-filter" }, [
          h(PanelHeader, { title: "筛选条件" }),
          ...["日期", "客服", "客户", "商品", "意向等级", "问题标签", "风险等级", "跟进状态"].map((label) => h("label", [h("span", label), h("input", { placeholder: label === "客户" ? "请输入客户名称/手机号" : "全部" })])),
          h("div", { class: "filter-actions" }, [h("button", "重置"), h("button", { onClick: loadConversations }, "搜索")]),
          h(PanelHeader, { title: `会话列表（${formatNumber(conversations.total)}）` }),
          h("div", { class: "review-list" }, conversations.items.map((row) => h("button", { class: ["review-list-item", { active: selected?.id === row.id }], type: "button", onClick: () => openConversation(row) }, [
            h("strong", formatClock(row.start_time)),
            h("span", row.customer_account || row.buyer_wangwang_masked || "-"),
            h("em", row.product_name || "-"),
            h("small", `AI状态 ${row.qc_status}`),
          ]))),
        ]),
        h("section", { class: "panel chat-timeline" }, [
          h(PanelHeader, { title: "聊天时间线" }, () => h("div", { class: "toolbar-buttons" }, [h("button", "导出"), h("button", "展开全屏")])),
          selected ? h("div", { class: "conversation-meta" }, [h("strong", "会话信息"), h("span", `会话时间：${formatTime(selected.start_time)}`), h("span", `客户：${selected.customer_account || selected.buyer_wangwang_masked || "-"}`), h("span", `客服：${selected.staff_name || "-"}`), h("span", `商品：${selected.product_name || "-"}`), h("span", `服务分：${formatScore(analysis?.intent?.staff_quality_score || 0)}`)]) : null,
          h("div", { class: "messages" }, messages.map((message) => h("div", { class: ["message", message.speaker_type] }, [h("b", `${message.speaker_account} ${formatClock(message.message_time)}`), h("p", message.content_text || "")]))),
          !selected ? h(EmptyState) : null,
        ]),
        h("aside", { class: "analysis-panel" }, [
          h("div", { class: "panel" }, [h(PanelHeader, { title: "AI 分析" }), h(AnalysisBlocks, { row: selected, analysis })]),
          h("div", { class: "panel" }, [h(PanelHeader, { title: "证据定位" }), ...(improvements.value?.frequent_issues || []).slice(0, 3).map((issue, index) => h("div", { class: "proof-row" }, [h("b", `证据 0${index + 1}`), h("span", issue.title), h("em", issue.reason || "")]))]),
        ]),
      ]);
    };
  },
});

const AnalysisBlocks = defineComponent({
  props: { row: { type: Object as () => ConversationRow | null, default: null }, analysis: { type: Object as () => ReturnType<typeof conversationAnalysis>, default: null } },
  setup(props) {
    return () => h("div", { class: "analysis-blocks" }, [
      h("section", [h("h4", "会话总结"), h("p", props.analysis?.intent?.summary || props.analysis?.risk?.summary || "当前会话暂无AI总结")]),
      h("section", [h("h4", "客户需求"), h("p", props.analysis?.intent?.need_summary || "-")]),
      h("section", [h("h4", "机会判断"), h("p", props.analysis?.intent ? `${intentText(props.analysis.intent.intent_tier)}，意向分 ${formatScore(props.analysis.intent.intent_score)}` : "-")]),
      h("section", [h("h4", "服务问题"), h("p", props.analysis?.risk?.summary || props.analysis?.intent?.risk_flags?.join("、") || "-")]),
      h("section", [h("h4", "建议动作"), h("p", props.analysis?.intent?.next_action || "-")]),
      h("section", [h("h4", "建议话术"), h("p", props.analysis?.intent?.suggested_reply || "-")]),
    ]);
  },
});

const RuleConfigPage = defineComponent({
  setup() {
    return () => h("div", { class: "rule-layout" }, [
      h("div", { class: "rule-tabs" }, ["质检维度规则", "评分权重", "AI 提示词", "问题标签", "风险表达", "商品场景", "建议话术库", "规则版本"].map((tab, index) => h("button", { class: index === 0 ? "active" : "" }, tab))),
      h("div", { class: "rule-grid" }, [
        h("section", { class: "panel rule-main" }, [
          h(PanelHeader, { title: "质检维度规则", subtitle: "配置质检维度的定义、评分规则与权重" }, () => h("button", { class: "outline-btn" }, "+ 新增维度")),
          h("div", { class: "rule-dimension-grid" }, dimensions.value.map((dim) => h("div", { class: "rule-dim-card" }, [h("strong", dim.label), h("p", rules.value.find((rule) => rule.category === dim.key)?.judgment_standard || "基于AI质检结果与真实会话证据计算。"), h("label", ["权重", h("input", { value: dim.key === "overall" ? "15" : "20", readonly: true })])]))),
          h("div", { class: "panel inline-panel" }, [h(PanelHeader, { title: "问题标签" }), h("div", { class: "issue-tags" }, rules.value.slice(0, 12).map((rule) => h("span", [rule.rule_name, h("i", "×")])))]),
          h("div", { class: "panel inline-panel" }, [h(PanelHeader, { title: "规则版本" }), h("div", { class: "version-table" }, ruleVersions.value.slice(0, 6).map((version) => h("div", [h("strong", version.rule_version), h("span", version.status), h("em", formatTime(version.published_at || version.created_time))]))) ]),
        ]),
        h("aside", { class: "panel rule-test" }, [
          h(PanelHeader, { title: "规则测试" }),
          h("label", ["选择会话样本", h("select", conversations.items.slice(0, 20).map((row) => h("option", { value: row.id }, `${row.conversation_id} ${row.product_name || ""}`)))]),
          h("button", { class: "primary-block", onClick: () => runDailyQc(false) }, "运行测试"),
          h("div", { class: "test-result" }, [h("b", formatScore(workbench.value?.metrics.service_quality_score)), h("span", "当前综合质量分")]),
          h("div", { class: "score-bars" }, dimensions.value.map((dim) => h("p", [h("span", dim.label), h("i", { style: { width: `${Math.min(100, scoreOf(selectedStaff.value, dim.key))}%` } }), h("em", formatScore(scoreOf(selectedStaff.value, dim.key)))]))),
          h("button", { class: "primary-block", onClick: () => runDailyQc(true) }, "发布规则"),
        ]),
      ]),
    ]);
  },
});

const StaffAccountPage = defineComponent({
  setup() {
    return () => {
      const selected = staffUsers.value.find((row) => row.staff_id === selectedStaffId.value) || staffUsers.value[0] || null;
      return h("div", { class: "account-page" }, [
        h("div", { class: "metric-grid four" }, [
          h(MetricCard, { icon: User, title: "客服账号总数", value: formatNumber(staffUsers.value.length), tone: "blue" }),
          h(MetricCard, { icon: Link, title: "已绑定千牛", value: formatNumber(staffUsers.value.filter((row) => row.sys_user_id).length), tone: "green" }),
          h(MetricCard, { icon: CircleCheck, title: "启用中", value: formatNumber(staffUsers.value.filter((row) => row.user_status !== 1).length), tone: "orange" }),
          h(MetricCard, { icon: Connection, title: "待绑定", value: formatNumber(staffUsers.value.filter((row) => !row.sys_user_id).length), tone: "purple" }),
        ]),
        h("div", { class: "account-grid" }, [
          h("aside", { class: "panel org-tree" }, [h(PanelHeader, { title: "客服组织结构" }), ...Array.from(new Map(staffUsers.value.map((row) => [staffGroupLabel(row), staffUsers.value.filter((staff) => staffGroupLabel(staff) === staffGroupLabel(row))])).entries()).map(([group, rows]) => h("section", [h("strong", `${group}（${rows.length}人）`), ...rows.slice(0, 6).map((row) => h("button", { onClick: () => (selectedStaffId.value = row.staff_id) }, row.staff_name))]))]),
          h("section", { class: "panel account-table-panel" }, [
            h(PanelHeader, { title: "客服账号列表" }),
            h("div", { class: "account-table" }, [
              h("div", { class: "account-head" }, ["客服姓名", "登录账号", "千牛账号", "所属店铺", "客服组", "账号状态", "绑定状态", "最近登录", "数据覆盖", "操作"].map((text) => h("span", text))),
              ...staffUsers.value.map((row) => h("button", { class: ["account-row", { selected: selected?.staff_id === row.staff_id }], type: "button", onClick: () => (selectedStaffId.value = row.staff_id) }, [
                h("strong", row.staff_name),
                h("span", row.username || "-"),
                h("span", row.primary_account || "-"),
                h("span", row.shop_name || "-"),
                h("span", staffGroupLabel(row)),
                h("i", { class: ["tag", row.user_status === 1 ? "risk" : "good"] }, row.user_status === 1 ? "停用" : "启用"),
                h("i", { class: ["tag", row.sys_user_id ? "good" : "watch"] }, row.sys_user_id ? "已绑定" : "待绑定"),
                h("span", formatTime(row.last_login)),
                h("span", formatNumber(row.conversation_count || 0)),
                h("span", "•••"),
              ])),
            ]),
          ]),
          h("aside", { class: "panel account-detail" }, selected ? [
            h(PanelHeader, { title: "账号详情" }),
            h("div", { class: "account-person" }, [h(AvatarBubble, { name: selected.staff_name, size: "large" }), h("h3", selected.staff_name), h("span", selected.user_status === 1 ? "已停用" : "启用中")]),
            ...[
              ["系统登录账号", selected.username || "-"],
              ["千牛绑定状态", selected.sys_user_id ? "已绑定" : "待绑定"],
              ["千牛账号", selected.primary_account || "-"],
              ["所属客服组", staffGroupLabel(selected)],
              ["最近登录时间", formatTime(selected.last_login)],
              ["最近一次分析覆盖会话数", formatNumber(selected.conversation_count || 0)],
            ].map(([label, value]) => h("p", [h("span", label), h("strong", value)])),
            h("button", { class: "primary-block", onClick: () => createOrResetStaff(selected, false) }, "创建客服"),
            h("button", { class: "outline-block", onClick: () => createOrResetStaff(selected, true) }, "重置密码"),
            h("button", { class: "danger-block", onClick: () => toggleStaffStatus(selected, selected.user_status === 1) }, selected.user_status === 1 ? "启用账号" : "停用账号"),
          ] : [h(EmptyState)]),
        ]),
      ]);
    };
  },
});

const DataTaskPage = defineComponent({
  setup() {
    return () => h("div", { class: "data-task-page" }, [
      h("div", { class: "metric-grid five" }, [
        h(MetricCard, { icon: Files, title: "同步批次", value: formatNumber(syncBatches.value.length), tone: "blue" }),
        h(MetricCard, { icon: Platform, title: "AI 任务成功率", value: formatPercent(qcTasks.value.length ? (qcTasks.value.filter((row) => row.status === "success").length * 100) / qcTasks.value.length : 0), tone: "green" }),
        h(MetricCard, { icon: WarningFilled, title: "失败任务数", value: formatNumber(qcTasks.value.filter((row) => row.status === "failed").length), tone: "orange" }),
        h(MetricCard, { icon: Clock, title: "平均耗时", value: averageTaskDurationMinutes(), suffix: averageTaskDurationMinutes() === "-" ? "" : "分钟", tone: "purple" }),
        h(MetricCard, { icon: CircleCheck, title: "系统状态", value: statusData.value.system_status || "正常", tone: "green" }),
      ]),
      h("div", { class: "task-flow panel" }, [h(PanelHeader, { title: "今日任务流程" }), h("div", { class: "flow-row" }, ["数据同步", "数据清洗", "AI 质检", "客户意向识别", "商品机会分析"].map((name, index) => h("div", { class: "flow-card" }, [h(ElIcon, null, () => index === 2 ? h(Platform) : h(Files)), h("strong", name), h("i", "成功"), h("span", index === 0 ? formatTime(statusData.value.rpa_fetch_time) : index === 2 ? formatTime(statusData.value.ai_finished_time) : "-")])))]),
      h("div", { class: "data-task-grid" }, [
        h("section", { class: "panel" }, [h(PanelHeader, { title: "每日数据批次" }, () => h("button", { class: "outline-btn", onClick: triggerSync }, syncing.value ? "同步中" : "立即同步")), h("div", { class: "batch-table" }, [
          h("div", { class: "batch-head" }, ["数据日期", "源库记录数", "入库记录数", "新增数量", "更新数量", "跳过数量", "同步状态", "同步时间", "触发方式", "操作"].map((text) => h("span", text))),
          ...syncBatches.value.map((row) => h("div", { class: "batch-row" }, [h("span", formatDate(row.created_time)), h("span", formatNumber(row.chat_rows)), h("span", formatNumber(row.conversation_count)), h("span", "-"), h("span", "-"), h("span", "-"), h("i", { class: ["tag", row.status === "success" ? "good" : "watch"] }, row.status), h("span", formatTime(row.finished_at || row.created_time)), h("span", row.source_type || "RPA定时"), h("span", "详情")]))]),
        ]),
        h("section", { class: "panel" }, [h(PanelHeader, { title: "AI 分析任务" }, () => h("button", { class: "outline-btn", onClick: () => runDailyQc(true) }, runningQc.value ? "执行中" : "抽检100条")), h("div", { class: "task-table" }, [
          h("div", { class: "task-head" }, ["任务名称", "数据日期", "任务状态", "会话数量", "覆盖客服", "成功数量", "失败数量", "耗时", "操作"].map((text) => h("span", text))),
          ...qcTasks.value.slice(0, 8).map((row) => h("div", { class: "task-row" }, [h("strong", row.task_id), h("span", formatDate(row.created_time)), h("i", { class: ["tag", row.status === "success" ? "good" : row.status === "failed" ? "risk" : "watch"] }, row.status), h("span", row.conversation_id), h("span", "-"), h("span", row.status === "success" ? "1" : "0"), h("span", row.status === "failed" ? "1" : "0"), h("span", taskDurationMinutes(row) === null ? "-" : `${taskDurationMinutes(row)}分钟`), h("span", "详情")]))]),
        ]),
      ]),
    ]);
  },
});

const StaffWorkbenchPage = defineComponent({
  setup() {
    return () => h("div", { class: "staff-workbench-page" }, [
      h("div", { class: "metric-grid four" }, [
        h(MetricCard, { icon: UserFilled, title: "待跟进客户", value: formatNumber(staffIntentRows.value.length), tone: "blue" }),
        h(MetricCard, { icon: WarningFilled, title: "高风险会话", value: formatNumber(myStaff.value?.high_risk_count || 0), tone: "red" }),
        h(MetricCard, { icon: StarFilled, title: "我的服务分", value: formatScore(myStaff.value?.overall_score), tone: "green" }),
        h(MetricCard, { icon: Opportunity, title: "主要改进点", value: myStaff.value?.main_issue || "-", tone: "orange" }),
      ]),
      h("div", { class: "staff-home-grid" }, [
        h("section", { class: "panel staff-follow-list" }, [h(PanelHeader, { title: "客户跟进队列" }), h(CustomerFollowupTable, { rows: staffIntentRows.value.slice(0, 8) })]),
        h("section", { class: "panel my-performance" }, [h(PanelHeader, { title: "我的服务表现" }), myStaff.value ? h(StaffDetailPanel) : h(EmptyState)]),
        h("aside", { class: "staff-right-stack" }, [
          h("div", { class: "panel" }, [h(PanelHeader, { title: "主要问题与建议" }), ...(improvements.value?.frequent_issues || []).slice(0, 3).map((issue) => h("p", { class: "numbered" }, issue.title)), h("h4", "改进建议"), ...(improvements.value?.frequent_issues || []).slice(0, 3).map((issue) => h("p", issue.suggested_action || issue.reason || issue.title))]),
          h("div", { class: "panel" }, [h(PanelHeader, { title: "最近复盘" }), ...(conversations.items.slice(0, 3).map((row) => h("button", { class: "recent-review", onClick: () => { activeView.value = "conversation-review"; openConversation(row); } }, [h("span", row.product_name || "会话"), h("strong", formatScore(conversationAnalysis(row)?.intent?.staff_quality_score || 0)), h("em", "查看证据")])))]),
        ]),
      ]),
    ]);
  },
});

const CustomerFollowupTable = defineComponent({
  props: { rows: { type: Array as () => IntentCustomer[], required: true } },
  setup(props) {
    return () => h("div", { class: "follow-table" }, [
      h("div", { class: "follow-head" }, ["优先级", "客户", "商品", "意向等级", "当前缺口", "下一步动作", "建议话术", "证据入口"].map((text) => h("span", text))),
      ...props.rows.map((row, index) => h("button", { class: "follow-row", type: "button", onClick: () => (selectedCustomerId.value = row.customer_id || null) }, [
        h("b", String(index + 1)),
        h("strong", row.customer_alias_masked || row.customer_account || "-"),
        h("span", row.product_name || "-"),
        h("i", { class: "tag watch" }, intentText(row.intent_tier)),
        h("span", followStatus(row)),
        h("span", row.next_action || "-"),
        h("span", row.suggested_reply || "查看"),
        h("span", "证据"),
      ])),
      !props.rows.length ? h(EmptyState) : null,
    ]);
  },
});

const StaffFollowupPage = defineComponent({
  setup() {
    return () => h("div", { class: "staff-follow-page" }, [
      h("div", { class: "metric-grid four" }, [
        h(MetricCard, { icon: UserFilled, title: "待跟进客户", value: formatNumber(staffIntentRows.value.length), tone: "blue" }),
        h(MetricCard, { icon: Coin, title: "待报价", value: formatNumber(staffIntentRows.value.filter((row) => followStatus(row) === "待报价").length), tone: "red" }),
        h(MetricCard, { icon: QuestionFilled, title: "待补问", value: formatNumber(staffIntentRows.value.filter((row) => followStatus(row) === "待补问").length), tone: "green" }),
        h(MetricCard, { icon: Service, title: "待唤回", value: formatNumber(staffIntentRows.value.filter((row) => followStatus(row) === "待唤回").length), tone: "orange" }),
      ]),
      h("div", { class: "staff-follow-grid" }, [h("section", { class: "panel" }, [h(PanelHeader, { title: "客户跟进列表" }), h(CustomerFollowupTable, { rows: staffIntentRows.value })]), h(CustomerDetailPanel)]),
    ]);
  },
});

const PersonalAccountPage = defineComponent({
  setup() {
    return () => h("div", { class: "personal-page" }, [
      h("div", { class: "metric-grid four" }, [
        h(MetricCard, { icon: CircleCheck, title: "我的账号状态", value: currentUser.value?.status === 1 ? "停用" : "正常", tone: "green" }),
        h(MetricCard, { icon: Link, title: "千牛绑定", value: myStaff.value?.primary_account ? "已绑定" : "待绑定", tone: "blue" }),
        h(MetricCard, { icon: User, title: "所属客服组", value: staffGroupLabel(myStaff.value), tone: "purple" }),
        h(MetricCard, { icon: Clock, title: "最近登录", value: formatTime(currentUser.value?.last_login), tone: "green" }),
      ]),
      h("div", { class: "personal-grid" }, [
        h("section", { class: "panel personal-info" }, [h(PanelHeader, { title: "个人资料" }), ...[
          ["登录账号", currentUser.value?.username || "-"],
          ["客服姓名", displayName.value],
          ["手机号", currentUser.value?.phone || "-"],
          ["邮箱", currentUser.value?.email || "-"],
          ["角色", "客服专员"],
          ["所属客服组", staffGroupLabel(myStaff.value)],
          ["千牛账号", myStaff.value?.primary_account || "-"],
          ["所属店铺", myStaff.value?.shop_name || "-"],
        ].map(([label, value]) => h("p", [h("span", label), h("strong", value)]))]),
        h("aside", { class: "panel account-actions" }, [h(PanelHeader, { title: "账号操作" }), h("div", { class: "account-person" }, [h(AvatarBubble, { name: displayName.value, size: "large" }), h("h3", displayName.value), h("span", "在线")]), ...["修改密码", "修改手机号", "更新邮箱", "查看千牛绑定", "申请调整客服组"].map((action) => h("button", { class: "outline-block" }, action))]),
        h("section", { class: "panel my-data-overview" }, [h(PanelHeader, { title: "我的数据概览" }), h("div", { class: "metric-grid four inline" }, [
          h(MetricCard, { icon: ChatDotRound, title: "本周会话数", value: formatNumber(myStaff.value?.conversation_count || 0), tone: "blue" }),
          h(MetricCard, { icon: StarFilled, title: "我的服务分", value: formatScore(myStaff.value?.overall_score), tone: "green" }),
          h(MetricCard, { icon: Histogram, title: "组内排名", value: String(sortStaffByDimension("overall").findIndex((row) => row.staff_id === myStaff.value?.staff_id) + 1 || "-"), tone: "orange" }),
          h(MetricCard, { icon: UserFilled, title: "待跟进客户", value: formatNumber(staffIntentRows.value.length), tone: "red" }),
        ])]),
      ]),
    ]);
  },
});
</script>
