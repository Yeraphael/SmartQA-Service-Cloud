<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <ElSwitch v-model="boundOnly" active-text="仅已绑定" @change="loadData" />
      <ElButton :loading="seeding" type="primary" icon="UserFilled" @click="seedUsers">
        初始化客服账号
      </ElButton>
      <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
    </div>

    <ElCard shadow="never">
      <ElTable :loading="loading" :data="rows" row-key="staff_id" height="650">
        <ElTableColumn prop="staff_id" label="ID" width="80" />
        <ElTableColumn prop="staff_name" label="客服" width="120" show-overflow-tooltip />
        <ElTableColumn prop="primary_account" label="千牛账号" min-width="180" show-overflow-tooltip />
        <ElTableColumn prop="username" label="登录账号" min-width="160" show-overflow-tooltip />
        <ElTableColumn prop="nickname" label="系统昵称" width="140" show-overflow-tooltip />
        <ElTableColumn prop="status" label="客服状态" width="110" />
        <ElTableColumn prop="user_status" label="账号状态" width="110">
          <template #default="{ row }">
            <ElTag v-if="row.sys_user_id" :type="row.user_status === 0 ? 'success' : 'warning'">
              {{ row.user_status === 0 ? "启用" : "停用" }}
            </ElTag>
            <ElTag v-else type="info">未绑定</ElTag>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import SmartQAAPI, { type StaffUser } from "@/api/module_smartqa";

const loading = ref(false);
const seeding = ref(false);
const boundOnly = ref(false);
const rows = ref<StaffUser[]>([]);

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.staffUsers(boundOnly.value);
    rows.value = res.data.data || [];
  } finally {
    loading.value = false;
  }
}

async function seedUsers() {
  seeding.value = true;
  try {
    await SmartQAAPI.seedStaffUsers(false);
    await loadData();
  } finally {
    seeding.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped>
.smartqa-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  padding: 12px;
}

.smartqa-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
