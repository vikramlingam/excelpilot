import React from "react";
import { Button, Text, Tooltip } from "@fluentui/react-components";
import { Settings20Regular } from "@fluentui/react-icons";
import { theme } from "./theme";

interface HeaderProps {
  bridgeConnected: boolean;
  selectedModelName: string;
  sessionCost: number;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  bridgeConnected,
  selectedModelName,
  sessionCost,
  onOpenSettings,
}) => {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 16px",
        paddingRight: 52,
        background: "linear-gradient(180deg, #071525 0%, #0b1f3a 100%)",
        borderBottom: "1px solid rgba(147, 180, 245, 0.25)",
        fontFamily: theme.font,
      }}
    >
      {/* Brand & Connection Status */}
      <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Text weight="semibold" size={300} style={{ color: "#f8fbff", letterSpacing: "-0.2px" }}>
              ExcelPilot
            </Text>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                padding: "2px 7px",
                borderRadius: 999,
                backgroundColor: bridgeConnected ? "rgba(16, 185, 129, 0.18)" : "rgba(180, 35, 24, 0.2)",
                border: `1px solid ${bridgeConnected ? "rgba(52, 211, 153, 0.45)" : "rgba(248, 113, 113, 0.45)"}`,
                fontSize: 10,
                fontWeight: 600,
                color: bridgeConnected ? "#6ee7b7" : "#fca5a5",
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  backgroundColor: bridgeConnected ? "#34d399" : "#f87171",
                  animation: bridgeConnected ? "pulse 2s infinite" : "none",
                }}
              />
              {bridgeConnected ? "Connected" : "Offline"}
            </div>
          </div>
        </div>
      </div>

      {/* Right Controls: Model Pill & Settings Button */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        {/* Clickable Model Badge */}
        <Tooltip content="Change model" relationship="label">
          <button
            onClick={onOpenSettings}
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "4px 9px",
              borderRadius: 6,
              border: "1px solid rgba(147, 180, 245, 0.35)",
              backgroundColor: "rgba(255,255,255,0.08)",
              fontSize: 11,
              fontWeight: 600,
              color: "#dbe7ff",
              cursor: "pointer",
              outline: "none",
              fontFamily: theme.font,
              maxWidth: 120,
            }}
          >
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {selectedModelName}
            </span>
          </button>
        </Tooltip>

        {/* Cost Tag (if > 0) */}
        {sessionCost > 0 && (
          <span
            style={{
              fontSize: "11px",
              color: "#93b4f5",
              padding: "2px 6px",
              backgroundColor: "transparent",
              borderRadius: "4px",
              fontWeight: 500,
            }}
          >
            ${sessionCost.toFixed(4)}
          </span>
        )}

        {/* Settings Gear Button */}
        <Tooltip content="Settings" relationship="label">
          <Button
            appearance="subtle"
            size="small"
            icon={<Settings20Regular style={{ color: "#dbe7ff" }} />}
            onClick={onOpenSettings}
            aria-label="Settings"
            style={{ minWidth: "28px", padding: "4px" }}
          />
        </Tooltip>
      </div>
    </header>
  );
};
