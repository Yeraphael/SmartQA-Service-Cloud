import "element-plus/dist/index.css";
import "./smartqa/styles.css";

import ElementPlus from "element-plus";
import { createApp } from "vue";

import SmartQAApp from "./smartqa/App.vue";

document.addEventListener("touchstart", function () {}, { passive: false });

createApp(SmartQAApp).use(ElementPlus).mount("#app");
