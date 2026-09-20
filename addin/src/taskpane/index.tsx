/* global Office */
import React from "react";
import ReactDOM from "react-dom/client";
import { FluentProvider, createLightTheme, BrandVariants, Theme } from "@fluentui/react-components";
import { App } from "./App";

const slate: BrandVariants = {
  10: "#020617",
  20: "#071525",
  30: "#0b1f3a",
  40: "#12305a",
  50: "#16325c",
  60: "#1d4ed8",
  70: "#2563eb",
  80: "#3b82f6",
  90: "#60a5fa",
  100: "#7aa2e8",
  110: "#93b4f5",
  120: "#b6c9ef",
  130: "#c5d4ea",
  140: "#dbe7ff",
  150: "#e4ecf8",
  160: "#eef3fb",
};

const excelPilotTheme: Theme = {
  ...createLightTheme(slate),
  colorNeutralBackground1: "#ffffff",
  colorNeutralBackground2: "#eef2f6",
  colorNeutralForeground1: "#0f172a",
  colorBrandBackground: "#2563eb",
  colorBrandBackgroundHover: "#1d4ed8",
  colorBrandForeground1: "#2563eb",
};

Office.onReady((info) => {
  if (info.host === Office.HostType.Excel) {
    const rootElement = document.getElementById("root");
    if (rootElement) {
      const root = ReactDOM.createRoot(rootElement);
      root.render(
        <FluentProvider theme={excelPilotTheme}>
          <App />
        </FluentProvider>
      );
    }
  }
});
