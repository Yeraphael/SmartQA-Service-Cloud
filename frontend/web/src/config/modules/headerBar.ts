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
  breadcrumb: {
    enabled: true,
    description: "Show current route breadcrumb.",
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
    description: "SmartQA does not expose a settings panel.",
  },
  themeToggle: {
    enabled: true,
    description: "Allow light and dark theme switching.",
  },
};

export default headerBarConfig;
