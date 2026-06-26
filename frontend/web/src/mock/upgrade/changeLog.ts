export interface UpgradeLog {
  version: string;
  title: string;
  date: string;
  detail?: string[];
  requireReLogin?: boolean;
  remark?: string;
}

export const upgradeLogList = ref<UpgradeLog[]>([
  {
    version: "1.0.0",
    title: "SmartQA P0",
    date: "2026-06-26",
    detail: [
      "老板端：工作台、千牛数据源、会话、AI质检任务、质检结果、客服表现、质检规则、客服账号。",
      "客服端：我的工作台、我的会话、我的质检结果、我的改进建议。",
      "数据链路：千牛源库同步、ODS入库、DIM/DWD扩表、AI质检和证据追溯。",
    ],
  },
]);
