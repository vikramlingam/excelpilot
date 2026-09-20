/* global Office */
import React from "react";
import ReactDOM from "react-dom/client";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import { App } from "./App";

Office.onReady((info) => {
  if (info.host === Office.HostType.Excel) {
    const rootElement = document.getElementById("root");
    if (rootElement) {
      const root = ReactDOM.createRoot(rootElement);
      root.render(
        <FluentProvider theme={webLightTheme}>
          <App />
        </FluentProvider>
      );
    }
  }
});
