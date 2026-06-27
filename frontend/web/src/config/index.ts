/** SmartQA front-end product configuration. */

import { MenuThemeEnum, MenuTypeEnum, SystemThemeEnum } from "@/enums/appEnum";
import { SystemConfig } from "@/types/config";
import { headerBarConfig } from "./modules/headerBar";

const appConfig: SystemConfig = {
  systemInfo: {
    name: "SmartQA Service Cloud",
  },
  systemThemeStyles: {
    [SystemThemeEnum.LIGHT]: { className: "" },
    [SystemThemeEnum.DARK]: { className: SystemThemeEnum.DARK },
  },
  settingThemeList: [
    {
      name: "Light",
      theme: SystemThemeEnum.LIGHT,
      color: ["#fff", "#fff"],
      leftLineColor: "#EDEEF0",
      rightLineColor: "#EDEEF0",
    },
    {
      name: "Dark",
      theme: SystemThemeEnum.DARK,
      color: ["#22252A"],
      leftLineColor: "#3F4257",
      rightLineColor: "#3F4257",
    },
    {
      name: "System",
      theme: SystemThemeEnum.AUTO,
      color: ["#fff", "#22252A"],
      leftLineColor: "#EDEEF0",
      rightLineColor: "#3F4257",
    },
  ],
  menuLayoutList: [
    { name: "Left", value: MenuTypeEnum.LEFT },
    { name: "Top", value: MenuTypeEnum.TOP },
    { name: "Mixed", value: MenuTypeEnum.TOP_LEFT },
    { name: "Dual Column", value: MenuTypeEnum.DUAL_MENU },
  ],
  themeList: [
    {
      theme: MenuThemeEnum.DESIGN,
      background: "#FFFFFF",
      systemNameColor: "var(--fa-gray-800)",
      iconColor: "#6B6B6B",
      textColor: "#29343D",
    },
    {
      theme: MenuThemeEnum.DARK,
      background: "#191A23",
      systemNameColor: "#D9DADB",
      iconColor: "#BABBBD",
      textColor: "#BABBBD",
    },
    {
      theme: MenuThemeEnum.LIGHT,
      background: "#ffffff",
      systemNameColor: "var(--fa-gray-800)",
      iconColor: "#6B6B6B",
      textColor: "#29343D",
    },
  ],
  darkMenuStyles: [
    {
      theme: MenuThemeEnum.DARK,
      background: "var(--default-box-color)",
      systemNameColor: "#DDDDDD",
      iconColor: "#BABBBD",
      textColor: "rgba(#FFFFFF, 0.7)",
    },
  ],
  systemMainColor: [
    "#5D87FF",
    "#B48DF3",
    "#1D84FF",
    "#60C041",
    "#38C0FC",
    "#F9901F",
    "#FF80C8",
  ] as const,
  headerBar: headerBarConfig,
};

export default Object.freeze(appConfig);
