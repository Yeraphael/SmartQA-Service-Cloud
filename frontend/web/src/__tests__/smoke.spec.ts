import { describe, expect, it } from "vitest";

describe("SmartQA frontend smoke", () => {
  it("keeps system menu enum values used by dynamic routes", async () => {
    const { MenuTypeEnum } = await import("@/enums/system/menu.enum");
    expect(MenuTypeEnum.CATALOG).toBe(1);
    expect(MenuTypeEnum.MENU).toBe(2);
    expect(MenuTypeEnum.BUTTON).toBe(3);
    expect(MenuTypeEnum.EXTLINK).toBe(4);
  });

  it("exposes the SmartQA API module", async () => {
    const mod = await import("@/api/module_smartqa");
    expect(mod.default.dashboardOverview).toBeTypeOf("function");
    expect(mod.default.syncSchedule).toBeTypeOf("function");
    expect(mod.default.conversations).toBeTypeOf("function");
    expect(mod.default.qcTasks).toBeTypeOf("function");
    expect(mod.default.dailyQcSample).toBeTypeOf("function");
  });
});
