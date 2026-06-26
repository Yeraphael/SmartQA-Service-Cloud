import type { HeaderBarFeatureConfig } from "@/types";

export const headerBarConfig: HeaderBarFeatureConfig = {
  menuButton: {
    enabled: true,
    description: "Show the sidebar collapse button.",
  },
  refreshButton: {
    enabled: true,
    description: "Show the current page refresh button.",
  },
  fastEnter: {
    enabled: false,
    description: "Disabled for SmartQA P0.",
  },
  breadcrumb: {
    enabled: true,
    description: "Show current route breadcrumb.",
  },
  globalSearch: {
    enabled: false,
    description: "Disabled for SmartQA P0.",
  },
  fullscreen: {
    enabled: true,
    description: "Show fullscreen toggle.",
  },
  language: {
    enabled: false,
    description: "SmartQA P0 uses Chinese only.",
  },
  settings: {
    enabled: false,
    description: "Template settings panel is removed.",
  },
  themeToggle: {
    enabled: true,
    description: "Allow light and dark theme switching.",
  },
  sizeSelect: {
    enabled: true,
    description: "Show Element Plus size selector.",
  },
};

export default headerBarConfig;
