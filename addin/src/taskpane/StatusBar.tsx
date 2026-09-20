import React from "react";
import { Badge, Text } from "@fluentui/react-components";

interface StatusBarProps {
  bridgeConnected: boolean;
  modelTier: string;
  jevBackend: string;
  sessionCost: number;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  bridgeConnected,
  modelTier,
  jevBackend,
  sessionCost,
}) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "6px 12px",
        backgroundColor: "#ffffff",
        borderBottom: "1px solid #e0e0e0",
        fontSize: "12px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span
          style={{
            height: "8px",
            width: "8px",
            borderRadius: "50%",
            backgroundColor: bridgeConnected ? "#107c41" : "#d83b01",
            display: "inline-block",
          }}
        />
        <Text size={200} weight="semibold">
          {bridgeConnected ? "Excel Live" : "Connecting..."}
        </Text>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <Badge size="small" appearance="tint" color="informative">
          {modelTier}
        </Badge>
        <Badge
          size="small"
          appearance="tint"
          color={jevBackend === "offline" ? "severe" : "success"}
        >
          Jev: {jevBackend}
        </Badge>
        <Text size={200} style={{ color: "#616161" }}>
          ${sessionCost.toFixed(4)}
        </Text>
      </div>
    </div>
  );
};
