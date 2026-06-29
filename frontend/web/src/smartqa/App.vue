<template>
  <ElConfigProvider :locale="zhCn" size="default" :z-index="3000">
    <div v-if="!isAuthed" class="login-screen">
      <section class="login-panel">
        <div class="brand-lockup">
          <img :src="brandLogo" alt="SmartQA" />
          <div>
            <strong>SmartQA</strong>
            <span>Service Cloud</span>
          </div>
        </div>
        <h1>客服质检与客户意向分析系统</h1>
        <p>登录后查看每日真实千牛会话、AI 质检结果和客服多维表现。</p>
        <ElForm label-position="top" @submit.prevent="handleLogin">
          <ElFormItem label="账号">
            <ElInput v-model.trim="loginForm.username" autocomplete="username" placeholder="请输入老板或客服账号" />
          </ElFormItem>
          <ElFormItem label="密码">
            <ElInput
              v-model="loginForm.password"
              autocomplete="current-password"
              placeholder="请输入密码"
              show-password
              type="password"
              @keyup.enter="handleLogin"
            />
          </ElFormItem>
          <div class="login-options">
            <ElCheckbox v-model="loginForm.remember">保持登录</ElCheckbox>
          </div>
          <ElButton class="primary-action" :loading="loginLoading" type="primary" @click="handleLogin">
            登录系统
          </ElButton>
        </ElForm>
      </section>
    </div>

    <div v-else class="smartqa-shell">
      <aside :class="['side-nav', { collapsed: navCollapsed }]">
        <div class="side-brand">
          <img :src="brandLogo" alt="SmartQA" />
          <div v-if="!navCollapsed">
            <strong>SmartQA</strong>
            <span>Service Cloud</span>
          </div>
        </div>
        <button class="collapse-btn" type="button" @click="navCollapsed = !navCollapsed">
          <ElIcon><Fold v-if="!navCollapsed" /><Expand v-else /></ElIcon>
        </button>
        <nav class="nav-list">
          <button
            v-for="item in visibleNavItems"
            :key="item.key"
            :class="['nav-item', { active: activeView === item.key }]"
            type="button"
            @click="activeView = item.key"
          >
            <ElIcon><component :is="item.icon" /></ElIcon>
            <span v-if="!navCollapsed">{{ item.label }}</span>
          </button>
        </nav>
      </aside>

      <main class="workspace">
        <header class="topbar">
          <div>
            <span class="eyebrow">SmartQA</span>
            <h2>{{ currentTitle }}</h2>
          </div>
          <div class="topbar-actions">
            <ElSegmented v-model="roleMode" :options="roleOptions" />
            <ElButton circle @click="loadAll">
              <ElIcon><Refresh /></ElIcon>
            </ElButton>
            <div class="user-chip">
              <span>{{ currentUser?.name || currentUser?.username || "SmartQA 用户" }}</span>
              <ElButton text @click="handleLogout">退出</ElButton>
            </div>
          </div>
        </header>

        <ElAlert v-if="loadError" class="page-alert" :closable="false" type="error" :title="loadError" />

        <section v-if="activeView === 'boss-workbench'" class="page-view dashboard-view">
          <div class="status-strip">
            <StatusItem label="RPA获取时间" :value="formatTime(workbench?.status.rpa_fetch_time)" />
            <StatusItem label="AI分析完成时间" :value="formatTime(workbench?.status.ai_finished_time)" />
            <StatusItem label="已分析会话数" :value="formatNumber(workbench?.status.analyzed_conversation_count)" />
            <StatusItem label="系统状态" :value="workbench?.status.system_status || '待加载'" status />
          </div>

          <div class="metric-grid">
            <MetricCard
              label="总体服务质量分"
              :value="formatScore(workbench?.metrics.service_quality_score)"
              tone="blue"
              suffix="/100"
            />
            <MetricCard
              label="高风险会话"
              :value="formatNumber(workbench?.metrics.high_risk_conversation_count)"
              tone="red"
            />
            <MetricCard
              label="需关注客服数"
              :value="formatNumber(workbench?.metrics.need_attention_staff_count)"
              tone="amber"
            />
            <MetricCard
              label="高意向未跟进数"
              :value="formatNumber(workbench?.metrics.high_intent_pending_count)"
              tone="green"
            />
          </div>

          <div class="dashboard-grid">
            <section class="panel ranking-panel">
              <PanelTitle title="客服质检榜单" :subtitle="`${sortedStaff.length} 名客服 · 当前维度：${activeDimensionLabel}`" />
              <div class="dimension-tabs">
                <button
                  v-for="dim in dimensions"
                  :key="dim.key"
                  :class="['dimension-tab', { active: activeDimension === dim.key }]"
                  type="button"
                  @click="activeDimension = dim.key"
                >
                  {{ dim.label }}
                </button>
              </div>
              <div class="winner-strip">
                <div v-for="winner in dimensionWinners" :key="winner.key" class="winner-card">
                  <span>{{ winner.label }}</span>
                  <strong>{{ winner.staff?.staff_name || "暂无" }}</strong>
                  <em>{{ winner.staff ? scoreOf(winner.staff, winner.key).toFixed(1) : "--" }}</em>
                </div>
              </div>
              <div class="quality-table">
                <div class="quality-head">
                  <span>排名</span>
                  <span>客服</span>
                  <span>当前维度得分</span>
                  <span>综合得分</span>
                  <span>较综合排名</span>
                  <span>主要问题</span>
                  <span>状态</span>
                </div>
                <button
                  v-for="(staff, index) in sortedStaff"
                  :key="staff.staff_id"
                  :class="['quality-row', { selected: selectedStaff?.staff_id === staff.staff_id }]"
                  type="button"
                  @click="selectedStaffId = staff.staff_id"
                  @mouseenter="hoverStaffId = staff.staff_id"
                  @mouseleave="hoverStaffId = null"
                >
                  <span class="rank-cell">{{ index + 1 }}</span>
                  <span class="staff-cell">
                    <AvatarBubble :name="staff.staff_name" />
                    <span>
                      <strong>{{ staff.staff_name }}</strong>
                      <em>{{ staff.primary_account || staff.role_label }}</em>
                    </span>
                  </span>
                  <span :class="scoreClass(scoreOf(staff, activeDimension))">{{ scoreOf(staff, activeDimension).toFixed(1) }}</span>
                  <span>{{ staff.overall_score.toFixed(1) }}</span>
                  <span :class="rankDeltaClass(rankDelta(staff))">{{ rankDeltaText(rankDelta(staff)) }}</span>
                  <span class="issue-cell">{{ staff.main_issue }}</span>
                  <span><StatusBadge :score="scoreOf(staff, activeDimension)" /></span>
                </button>
                <EmptyState v-if="!sortedStaff.length" text="暂无已分析客服数据" />
              </div>
            </section>

            <section class="panel detail-panel">
              <PanelTitle title="客服详情" :subtitle="selectedStaff?.primary_account || '点击榜单查看详情'" />
              <StaffDetailCard v-if="selectedStaff" :staff="selectedStaff" />
              <EmptyState v-else text="暂无客服详情" />
            </section>

            <section class="panel quadrant-panel">
              <PanelTitle title="客服能力四象限" subtitle="服务效率分 × 服务质量分" />
              <QuadrantChart
                :points="workbench?.quadrant.points || []"
                :selected-id="selectedStaff?.staff_id || undefined"
                :hover-id="hoverStaffId || undefined"
                @select="selectedStaffId = $event"
              />
            </section>
          </div>

          <div class="bottom-grid">
            <section class="panel">
              <PanelTitle title="商品机会 Top 5" subtitle="按高意向与咨询量综合展示" />
              <ProductOpportunityList :items="workbench?.product_opportunities || []" />
            </section>
            <section class="panel">
              <PanelTitle title="近 7 天趋势" subtitle="质量分、风险、未跟进与会话量" />
              <TrendChart :points="workbench?.trend_7d || []" />
            </section>
          </div>
        </section>

        <section v-else-if="activeView === 'staff-performance'" class="page-view">
          <SectionHeader title="客服表现" subtitle="按六个能力维度查看团队真实表现，点击工作台榜单可查看客服详情。" />
          <div class="staff-performance-grid">
            <div v-for="dim in dimensions.filter((item) => item.key !== 'overall')" :key="dim.key" class="panel dimension-rank-panel">
              <PanelTitle :title="dim.label" subtitle="当前维度排名" />
              <div class="mini-rank-list">
                <div v-for="staff in topStaffByDimension(dim.key).slice(0, 6)" :key="staff.staff_id" class="mini-rank-row">
                  <span>{{ staff.staff_name }}</span>
                  <strong>{{ scoreOf(staff, dim.key).toFixed(1) }}</strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section v-else-if="activeView === 'product-opportunity'" class="page-view">
          <SectionHeader title="商品机会" subtitle="从真实会话识别咨询量、高意向数和商品层面的需求信号。" />
          <div class="panel">
            <ProductOpportunityTable :items="productOpportunities" />
          </div>
        </section>

        <section v-else-if="activeView === 'conversation-review'" class="page-view">
          <SectionHeader title="会话复盘" subtitle="查看千牛原始会话、AI 质检状态和会话证据。" />
          <div class="panel conversation-panel">
            <div class="table-toolbar">
              <ElInput v-model.trim="conversationKeyword" clearable placeholder="搜索客户、客服或商品" @keyup.enter="loadConversations" />
              <ElButton type="primary" @click="loadConversations">查询</ElButton>
            </div>
            <ConversationTable :items="conversations.items" :selected-id="selectedConversationId || undefined" @select="openConversation" />
          </div>
          <div v-if="conversationDetail" class="panel chat-panel">
            <PanelTitle
              :title="conversationDetail.conversation.product_name || '会话详情'"
              :subtitle="conversationDetail.conversation.conversation_id || ''"
            />
            <div class="message-list">
              <div
                v-for="message in conversationDetail.messages"
                :key="message.id"
                :class="['message-item', message.speaker_type]"
              >
                <span>{{ message.speaker_account }} · {{ formatTime(message.message_time) }}</span>
                <p>{{ message.content_text || "空消息" }}</p>
              </div>
            </div>
          </div>
        </section>

        <section v-else-if="activeView === 'staff-users'" class="page-view">
          <SectionHeader title="客服管理" subtitle="管理客服与千牛账号、系统账号之间的绑定状态。" />
          <div class="panel">
            <StaffUserTable :items="staffUsers" />
          </div>
        </section>

        <section v-else-if="activeView === 'data-config'" class="page-view">
          <SectionHeader title="数据与配置" subtitle="查看同步计划、每日批次、AI任务和质检规则。" />
          <div class="data-grid">
            <div class="panel">
              <PanelTitle title="数据状态" subtitle="千牛同步与每日任务" />
              <div class="data-status-list">
                <StatusItem label="最近批次" :value="batchSummary?.latest_batch_id || '暂无'" />
                <StatusItem label="聊天行数" :value="formatNumber(batchSummary?.chat_rows)" />
                <StatusItem label="会话数" :value="formatNumber(batchSummary?.conversation_count)" />
                <StatusItem label="定时任务" :value="schedule?.scheduler_running ? '运行中' : '未运行'" status />
              </div>
              <ElButton class="sync-button" type="primary" :loading="syncing" @click="triggerSync">立即同步千牛数据</ElButton>
            </div>
            <div class="panel">
              <PanelTitle title="AI分析任务" :subtitle="`${qcTasks.length} 条任务`" />
              <TaskList :items="qcTasks" />
              <ElButton class="sync-button" :loading="dailyQcLoading" @click="runDailyQc">先抽检 100 个会话</ElButton>
            </div>
            <div class="panel">
              <PanelTitle title="规则配置" :subtitle="`${rules.length} 条规则`" />
              <RuleList :items="rules" />
            </div>
          </div>
        </section>

        <section v-else-if="activeView === 'my-workbench'" class="page-view">
          <SectionHeader title="我的工作台" subtitle="客服查看本人服务表现、风险会话和待跟进客户。" />
          <div class="dashboard-grid support-grid">
            <section class="panel detail-panel">
              <PanelTitle title="个人表现" :subtitle="selectedStaff?.primary_account || '当前账号绑定客服'" />
              <StaffDetailCard v-if="selectedStaff" :staff="selectedStaff" />
              <EmptyState v-else text="当前账号暂无绑定客服数据" />
            </section>
            <section class="panel">
              <PanelTitle title="我的近 7 天趋势" subtitle="服务质量变化" />
              <TrendChart :points="workbench?.trend_7d || []" />
            </section>
          </div>
        </section>
      </main>
    </div>
  </ElConfigProvider>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from "vue";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import {
  ChatDotRound,
  DataAnalysis,
  Expand,
  Fold,
  Goods,
  Management,
  Refresh,
  Setting,
  TrendCharts,
  User,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import brandLogo from "@fa_imgs/smartqa-brand.png";
import {
  apiErrorMessage,
  Auth,
  type BossDimension,
  type BossStaffQuality,
  type BossTrendPoint,
  type BossWorkbench,
  type ConversationDetail,
  type ConversationRow,
  type ImportBatch,
  type ProductOpportunity,
  type QcRule,
  type QcTask,
  type QianniuSummary,
  type StaffUser,
  type SyncSchedule,
  SmartQAService,
  type UserInfo,
} from "./api";

const isAuthed = ref(Boolean(Auth.getAccessToken()));
const loginLoading = ref(false);
const loadError = ref("");
const navCollapsed = ref(false);
const roleMode = ref<"boss" | "staff">("boss");
const activeView = ref("boss-workbench");
const currentUser = ref<UserInfo | null>(null);
const workbench = ref<BossWorkbench | null>(null);
const productOpportunities = ref<ProductOpportunity[]>([]);
const staffUsers = ref<StaffUser[]>([]);
const batchSummary = ref<QianniuSummary | null>(null);
const schedule = ref<SyncSchedule | null>(null);
const syncBatches = ref<ImportBatch[]>([]);
const qcTasks = ref<QcTask[]>([]);
const rules = ref<QcRule[]>([]);
const syncing = ref(false);
const dailyQcLoading = ref(false);
const activeDimension = ref<BossDimension["key"]>("overall");
const selectedStaffId = ref<number | null>(null);
const hoverStaffId = ref<number | null>(null);
const conversationKeyword = ref("");
const selectedConversationId = ref<number | null>(null);
const conversationDetail = ref<ConversationDetail | null>(null);
const conversations = reactive<{ items: ConversationRow[]; total: number }>({ items: [], total: 0 });

const loginForm = reactive({
  username: "",
  password: "",
  remember: Auth.rememberMe(),
});

const roleOptions = [
  { label: "老板端", value: "boss" },
  { label: "客服端", value: "staff" },
];

const bossNavItems = [
  { key: "boss-workbench", label: "工作台总览", icon: DataAnalysis },
  { key: "staff-performance", label: "客服表现", icon: TrendCharts },
  { key: "product-opportunity", label: "商品机会", icon: Goods },
  { key: "conversation-review", label: "会话复盘", icon: ChatDotRound },
  { key: "staff-users", label: "客服管理", icon: Management },
  { key: "data-config", label: "数据与配置", icon: Setting },
];

const staffNavItems = [
  { key: "my-workbench", label: "我的工作台", icon: User },
  { key: "conversation-review", label: "会话复盘", icon: ChatDotRound },
];

const visibleNavItems = computed(() => (roleMode.value === "boss" ? bossNavItems : staffNavItems));
const currentTitle = computed(() => visibleNavItems.value.find((item) => item.key === activeView.value)?.label || "SmartQA");

const dimensions = computed<BossDimension[]>(() => {
  const list = workbench.value?.dimensions || [];
  if (list.length) return list;
  return [
    { key: "overall", label: "综合表现" },
    { key: "response_efficiency", label: "响应效率" },
    { key: "service_attitude", label: "服务态度" },
    { key: "professional_ability", label: "专业能力" },
    { key: "problem_solving", label: "问题解决" },
    { key: "demand_mining", label: "需求挖掘" },
    { key: "conversion_progress", label: "成交推进" },
  ];
});

const activeDimensionLabel = computed(() => dimensions.value.find((item) => item.key === activeDimension.value)?.label || "综合表现");
const staffList = computed(() => workbench.value?.staff_quality || []);
const overallRankMap = computed(() => {
  const map = new Map<number, number>();
  [...staffList.value]
    .sort((a, b) => scoreOf(b, "overall") - scoreOf(a, "overall"))
    .forEach((staff, index) => map.set(staff.staff_id, index + 1));
  return map;
});
const currentRankMap = computed(() => {
  const map = new Map<number, number>();
  sortedStaff.value.forEach((staff, index) => map.set(staff.staff_id, index + 1));
  return map;
});
const sortedStaff = computed(() => topStaffByDimension(activeDimension.value));
const selectedStaff = computed(() => {
  const list = staffList.value;
  return list.find((staff) => staff.staff_id === selectedStaffId.value) || list[0] || null;
});
const dimensionWinners = computed(() =>
  dimensions.value.map((dimension) => ({
    ...dimension,
    staff: topStaffByDimension(dimension.key)[0],
  }))
);

watch(roleMode, () => {
  activeView.value = roleMode.value === "boss" ? "boss-workbench" : "my-workbench";
});

watch(staffList, (list) => {
  if (!selectedStaffId.value && list[0]) selectedStaffId.value = list[0].staff_id;
});

onMounted(async () => {
  if (isAuthed.value) {
    await loadAll();
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
    ElMessage.success("登录成功");
    await loadAll();
  } catch (error) {
    ElMessage.error(apiErrorMessage(error));
  } finally {
    loginLoading.value = false;
  }
}

async function handleLogout() {
  await SmartQAService.logout();
  isAuthed.value = false;
  currentUser.value = null;
}

async function loadAll() {
  loadError.value = "";
  try {
    const [user, bossData] = await Promise.all([SmartQAService.currentUser().catch(() => null), SmartQAService.bossWorkbench()]);
    currentUser.value = user;
    workbench.value = bossData;
    productOpportunities.value = bossData.product_opportunities || [];
    await Promise.allSettled([loadConversations(), loadBossOnlyData()]);
  } catch (error) {
    loadError.value = apiErrorMessage(error);
  }
}

async function loadBossOnlyData() {
  const [staffResult, summaryResult, scheduleResult, batchResult, taskResult, ruleResult, productResult] = await Promise.allSettled([
    SmartQAService.staffUsers(),
    SmartQAService.batchSummary(),
    SmartQAService.syncSchedule(),
    SmartQAService.syncBatches(20),
    SmartQAService.qcTasks({ limit: 50 }),
    SmartQAService.rules(),
    SmartQAService.productOpportunities(30),
  ]);
  if (staffResult.status === "fulfilled") staffUsers.value = staffResult.value;
  if (summaryResult.status === "fulfilled") batchSummary.value = summaryResult.value;
  if (scheduleResult.status === "fulfilled") schedule.value = scheduleResult.value;
  if (batchResult.status === "fulfilled") syncBatches.value = batchResult.value;
  if (taskResult.status === "fulfilled") qcTasks.value = taskResult.value;
  if (ruleResult.status === "fulfilled") rules.value = ruleResult.value;
  if (productResult.status === "fulfilled") productOpportunities.value = productResult.value;
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
    await loadBossOnlyData();
  } catch (error) {
    ElMessage.error(apiErrorMessage(error));
  } finally {
    syncing.value = false;
  }
}

async function runDailyQc() {
  dailyQcLoading.value = true;
  try {
    await SmartQAService.dailyQcSample({ limit: 100, execute: false });
    ElMessage.success("已生成每日抽检任务");
    qcTasks.value = await SmartQAService.qcTasks({ limit: 50 });
  } catch (error) {
    ElMessage.error(apiErrorMessage(error));
  } finally {
    dailyQcLoading.value = false;
  }
}

function topStaffByDimension(key: string) {
  return [...staffList.value].sort((a, b) => {
    const scoreDelta = scoreOf(b, key) - scoreOf(a, key);
    if (scoreDelta !== 0) return scoreDelta;
    return b.qc_count - a.qc_count;
  });
}

function scoreOf(staff: BossStaffQuality, key: string) {
  return key === "overall" ? Number(staff.overall_score || 0) : Number(staff.dimensions?.[key] || 0);
}

function rankDelta(staff: BossStaffQuality) {
  const current = currentRankMap.value.get(staff.staff_id) || 0;
  const overall = overallRankMap.value.get(staff.staff_id) || 0;
  return overall - current;
}

function rankDeltaText(delta: number) {
  if (delta > 0) return `↑ ${delta}`;
  if (delta < 0) return `↓ ${Math.abs(delta)}`;
  return "-";
}

function rankDeltaClass(delta: number) {
  if (delta > 0) return "rank-up";
  if (delta < 0) return "rank-down";
  return "rank-flat";
}

function scoreClass(score: number) {
  if (score >= 90) return "score-excellent";
  if (score >= 80) return "score-good";
  if (score >= 70) return "score-watch";
  return "score-risk";
}

function formatNumber(value?: number | null) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function formatScore(value?: number | null) {
  return Number(value || 0).toFixed(1);
}

function formatTime(value?: string | null) {
  if (!value) return "暂无";
  return value.replace("T", " ").slice(0, 16);
}

const StatusItem = defineComponent({
  props: {
    label: { type: String, required: true },
    value: { type: String, required: true },
    status: { type: Boolean, default: false },
  },
  setup(props) {
    return () =>
      h("div", { class: "status-item" }, [
        h("span", props.label),
        h("strong", { class: props.status ? "status-value" : "" }, props.value),
      ]);
  },
});

const MetricCard = defineComponent({
  props: {
    label: { type: String, required: true },
    value: { type: String, required: true },
    suffix: { type: String, default: "" },
    tone: { type: String, default: "blue" },
  },
  setup(props) {
    return () =>
      h("div", { class: ["metric-card", props.tone] }, [
        h("span", props.label),
        h("strong", [props.value, props.suffix ? h("em", props.suffix) : null]),
      ]);
  },
});

const PanelTitle = defineComponent({
  props: {
    title: { type: String, required: true },
    subtitle: { type: String, default: "" },
  },
  setup(props) {
    return () =>
      h("div", { class: "panel-title" }, [
        h("h3", props.title),
        props.subtitle ? h("span", props.subtitle) : null,
      ]);
  },
});

const SectionHeader = defineComponent({
  props: {
    title: { type: String, required: true },
    subtitle: { type: String, default: "" },
  },
  setup(props) {
    return () => h("div", { class: "section-header" }, [h("h1", props.title), h("p", props.subtitle)]);
  },
});

const EmptyState = defineComponent({
  props: { text: { type: String, required: true } },
  setup(props) {
    return () => h("div", { class: "empty-state" }, props.text);
  },
});

const AvatarBubble = defineComponent({
  props: { name: { type: String, required: true } },
  setup(props) {
    return () => h("b", { class: "avatar-bubble" }, props.name.slice(0, 1));
  },
});

const StatusBadge = defineComponent({
  props: { score: { type: Number, required: true } },
  setup(props) {
    return () => {
      const text = props.score >= 90 ? "优秀" : props.score >= 80 ? "良好" : props.score >= 70 ? "需关注" : "需改进";
      return h("i", { class: ["status-badge", scoreClass(props.score)] }, text);
    };
  },
});

const StaffDetailCard = defineComponent({
  props: { staff: { type: Object as () => BossStaffQuality, required: true } },
  setup(props) {
    return () =>
      h("div", { class: "staff-detail-card" }, [
        h("div", { class: "staff-profile" }, [
          h(AvatarBubble, { name: props.staff.staff_name }),
          h("div", [h("strong", props.staff.staff_name), h("span", props.staff.role_label || "客服专员")]),
          h("em", scoreOf(props.staff, "overall").toFixed(1)),
        ]),
        h(HexRadar, { staff: props.staff }),
        h("div", { class: "detail-metrics" }, [
          h("div", [h("span", "高风险会话数"), h("strong", String(props.staff.high_risk_count || 0))]),
          h("div", [h("span", "待跟进意向数"), h("strong", String(props.staff.pending_intent_count || 0))]),
        ]),
      ]);
  },
});

const HexRadar = defineComponent({
  props: { staff: { type: Object as () => BossStaffQuality, required: true } },
  setup(props) {
    return () => {
      const axis: Array<[string, string]> = [
        ["响应效率", "response_efficiency"],
        ["服务态度", "service_attitude"],
        ["专业能力", "professional_ability"],
        ["问题解决", "problem_solving"],
        ["需求挖掘", "demand_mining"],
        ["成交推进", "conversion_progress"],
      ];
      const cx = 150;
      const cy = 132;
      const radius = 82;
      const points = axis
        .map(([, key], index) => {
          const angle = -Math.PI / 2 + (Math.PI * 2 * index) / axis.length;
          const score = Math.max(Math.min(scoreOf(props.staff, key), 100), 0);
          const r = (score / 100) * radius;
          return `${cx + Math.cos(angle) * r},${cy + Math.sin(angle) * r}`;
        })
        .join(" ");
      const grid = [0.25, 0.5, 0.75, 1].map((scale) =>
        axis
          .map((_, index) => {
            const angle = -Math.PI / 2 + (Math.PI * 2 * index) / axis.length;
            return `${cx + Math.cos(angle) * radius * scale},${cy + Math.sin(angle) * radius * scale}`;
          })
          .join(" ")
      );
      return h("svg", { class: "hex-radar", viewBox: "0 0 300 270", role: "img" }, [
        ...grid.map((polygon) => h("polygon", { points: polygon, class: "radar-grid" })),
        ...axis.map(([label, key], index) => {
          const angle = -Math.PI / 2 + (Math.PI * 2 * index) / axis.length;
          const x = cx + Math.cos(angle) * (radius + 30);
          const y = cy + Math.sin(angle) * (radius + 22);
          return h("g", [h("text", { x, y, class: "radar-label", "text-anchor": "middle" }, label), h("text", { x, y: y + 15, class: "radar-score", "text-anchor": "middle" }, scoreOf(props.staff, key).toFixed(0))]);
        }),
        h("polygon", { points, class: "radar-area" }),
      ]);
    };
  },
});

const QuadrantChart = defineComponent({
  props: {
    points: { type: Array as () => Array<{ staff_id: number; staff_name: string; x: number; y: number; score: number; status: string }>, default: () => [] },
    selectedId: { type: Number, default: null },
    hoverId: { type: Number, default: null },
  },
  emits: ["select"],
  setup(props, { emit }) {
    return () =>
      h("div", { class: "quadrant-chart" }, [
        h("div", { class: "quadrant-axis x" }, "服务效率分"),
        h("div", { class: "quadrant-axis y" }, "服务质量分"),
        h("div", { class: "quadrant-line vertical" }),
        h("div", { class: "quadrant-line horizontal" }),
        h("span", { class: "quadrant-label top-right" }, "质量优秀 效率优秀"),
        h("span", { class: "quadrant-label bottom-left" }, "质量待提升 效率待提升"),
        props.points.map((point) =>
          h(
            "button",
            {
              class: ["quadrant-point", { active: props.selectedId === point.staff_id, hover: props.hoverId === point.staff_id }],
              style: { left: `${Math.max(4, Math.min(point.x, 98))}%`, bottom: `${Math.max(4, Math.min(point.y, 96))}%` },
              title: `${point.staff_name} ${point.score}`,
              onClick: () => emit("select", point.staff_id),
            },
            point.staff_name.slice(0, 1)
          )
        ),
      ]);
  },
});

const ProductOpportunityList = defineComponent({
  props: { items: { type: Array as () => ProductOpportunity[], default: () => [] } },
  setup(props) {
    return () =>
      h("div", { class: "product-list" }, [
        ...props.items.slice(0, 5).map((item, index) =>
          h("div", { class: "product-row" }, [
            h("span", String(index + 1)),
            h("strong", item.product_name || "未知商品"),
            h("em", `${item.conversation_count || 0} 会话`),
            h("b", `${item.h_customer_count || 0} 高意向`),
          ])
        ),
        props.items.length ? null : h(EmptyState, { text: "暂无商品机会数据" }),
      ]);
  },
});

const ProductOpportunityTable = defineComponent({
  props: { items: { type: Array as () => ProductOpportunity[], default: () => [] } },
  setup(props) {
    return () =>
      h("div", { class: "data-table" }, [
        h("div", { class: "data-head cols-6" }, ["商品", "相关会话", "高意向", "高意向率", "均意向分", "价格敏感"].map((text) => h("span", text))),
        ...props.items.map((item) =>
          h("div", { class: "data-row cols-6" }, [
            h("strong", item.product_name || "未知商品"),
            h("span", formatNumber(item.conversation_count)),
            h("span", formatNumber(item.h_customer_count)),
            h("span", `${Number(item.h_customer_rate || 0).toFixed(1)}%`),
            h("span", Number(item.avg_intent_score || 0).toFixed(1)),
            h("span", formatNumber(item.price_sensitive_count)),
          ])
        ),
        props.items.length ? null : h(EmptyState, { text: "暂无商品机会数据" }),
      ]);
  },
});

const TrendChart = defineComponent({
  props: { points: { type: Array as () => BossTrendPoint[], default: () => [] } },
  setup(props) {
    return () => {
      const width = 720;
      const height = 260;
      const pad = 36;
      const list = props.points;
      const maxCount = Math.max(...list.flatMap((p) => [p.high_risk_count, p.pending_intent_count, p.conversation_count / 5]), 10);
      const x = (index: number) => pad + (index * (width - pad * 2)) / Math.max(list.length - 1, 1);
      const yScore = (score: number) => height - pad - (Math.max(Math.min(score, 100), 0) / 100) * (height - pad * 2);
      const yCount = (count: number) => height - pad - (count / maxCount) * (height - pad * 2);
      const line = (values: number[], yFn: (value: number) => number) => values.map((value, index) => `${x(index)},${yFn(value)}`).join(" ");
      return h("svg", { class: "trend-chart", viewBox: `0 0 ${width} ${height}` }, [
        h("line", { x1: pad, y1: height - pad, x2: width - pad, y2: height - pad, class: "chart-axis" }),
        h("line", { x1: pad, y1: pad, x2: pad, y2: height - pad, class: "chart-axis" }),
        h("polyline", { points: line(list.map((p) => p.quality_score), yScore), class: "trend-line quality" }),
        h("polyline", { points: line(list.map((p) => p.high_risk_count), yCount), class: "trend-line risk" }),
        h("polyline", { points: line(list.map((p) => p.pending_intent_count), yCount), class: "trend-line intent" }),
        ...list.map((point, index) => h("text", { x: x(index), y: height - 10, class: "chart-label", "text-anchor": "middle" }, point.date)),
      ]);
    };
  },
});

const ConversationTable = defineComponent({
  props: {
    items: { type: Array as () => ConversationRow[], default: () => [] },
    selectedId: { type: Number, default: null },
  },
  emits: ["select"],
  setup(props, { emit }) {
    return () =>
      h("div", { class: "data-table" }, [
        h("div", { class: "data-head cols-7" }, ["时间", "客户", "客服", "商品", "消息数", "质检状态", "操作"].map((text) => h("span", text))),
        ...props.items.map((item) =>
          h("button", { class: ["data-row cols-7 clickable", { active: props.selectedId === item.id }], onClick: () => emit("select", item) }, [
            h("span", formatTime(item.start_time)),
            h("span", item.customer_account || item.buyer_wangwang_masked || "-"),
            h("span", item.staff_name || "-"),
            h("strong", item.product_name || "-"),
            h("span", String(item.message_count || 0)),
            h("span", item.qc_status || "-"),
            h("span", "查看证据"),
          ])
        ),
        props.items.length ? null : h(EmptyState, { text: "暂无会话数据" }),
      ]);
  },
});

const StaffUserTable = defineComponent({
  props: { items: { type: Array as () => StaffUser[], default: () => [] } },
  setup(props) {
    return () =>
      h("div", { class: "data-table" }, [
        h("div", { class: "data-head cols-6" }, ["客服", "千牛账号", "系统账号", "绑定状态", "账号状态", "来源"].map((text) => h("span", text))),
        ...props.items.map((item) =>
          h("div", { class: "data-row cols-6" }, [
            h("strong", item.staff_name),
            h("span", item.primary_account || "-"),
            h("span", item.username || "-"),
            h("span", item.sys_user_id ? "已绑定" : "未绑定"),
            h("span", item.user_status === 1 ? "停用" : "启用"),
            h("span", item.source_system || "-"),
          ])
        ),
        props.items.length ? null : h(EmptyState, { text: "暂无客服账号数据" }),
      ]);
  },
});

const TaskList = defineComponent({
  props: { items: { type: Array as () => QcTask[], default: () => [] } },
  setup(props) {
    return () =>
      h("div", { class: "compact-list" }, [
        ...props.items.slice(0, 8).map((item) =>
          h("div", { class: "compact-row" }, [h("strong", item.task_id), h("span", item.status), h("em", formatTime(item.finished_at || item.created_time))])
        ),
        props.items.length ? null : h(EmptyState, { text: "暂无AI分析任务" }),
      ]);
  },
});

const RuleList = defineComponent({
  props: { items: { type: Array as () => QcRule[], default: () => [] } },
  setup(props) {
    return () =>
      h("div", { class: "compact-list" }, [
        ...props.items.slice(0, 10).map((item) =>
          h("div", { class: "compact-row" }, [h("strong", item.rule_name), h("span", item.category), h("em", `${item.deduction_score}分`)])
        ),
        props.items.length ? null : h(EmptyState, { text: "暂无规则数据" }),
      ]);
  },
});
</script>
