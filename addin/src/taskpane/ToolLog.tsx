import React, { useState } from "react";
import { Button, Text } from "@fluentui/react-components";

export interface ToolLogItem {
  id: string;
  name: string;
  args: any;
  status: "running" | "done" | "error";
  resultPreview?: string;
}

interface ToolLogProps {
  items: ToolLogItem[];
  onSelectRange?: (sheet: string, address: string) => void;
}

export const ToolLog: React.FC<ToolLogProps> = ({ items, onSelectRange }) => {
  const [collapsed, setCollapsed] = useState<boolean>(false);

  if (items.length === 0) return null;

  return (
    <div
      style={{
        margin: "8px 12px",
        backgroundColor: "#f9f9f9",
        border: "1px solid #e5e5e5",
        borderRadius: "6px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "6px 10px",
          backgroundColor: "#f0f0f0",
          cursor: "pointer",
        }}
        onClick={() => setCollapsed(!collapsed)}
      >
        <Text size={200} weight="semibold">
          Tool Execution Trace ({items.length})
        </Text>
        <Text size={100}>{collapsed ? "Expand" : "Collapse"}</Text>
      </div>

      {!collapsed && (
        <div style={{ padding: "6px 10px", display: "flex", flexDirection: "column", gap: "6px" }}>
          {items.map((item) => (
            <div
              key={item.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                fontSize: "11px",
              }}
            >
              <div>
                <Text size={200} weight="medium" style={{ color: "#0078d4" }}>
                  {item.name}
                </Text>
                {item.args?.address && (
                  <Text size={100} style={{ marginLeft: "6px", color: "#616161" }}>
                    ({item.args.sheet || ""}!{item.args.address})
                  </Text>
                )}
              </div>

              {item.args?.address && onSelectRange && (
                <Button
                  size="small"
                  appearance="subtle"
                  onClick={() => onSelectRange(item.args.sheet || "Sheet1", item.args.address)}
                >
                  Locate
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
