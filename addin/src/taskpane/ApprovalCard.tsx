import React from "react";
import { Button, Text, ProgressBar } from "@fluentui/react-components";

interface ApprovalCardProps {
  toolName: string;
  args: any;
  probs: Record<string, number>;
  cells?: number;
  onApprove: () => void;
  onReject: () => void;
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  toolName,
  args,
  probs,
  cells,
  onApprove,
  onReject,
}) => {
  return (
    <div
      style={{
        margin: "8px 12px",
        padding: "10px",
        backgroundColor: "#f4f6f9",
        border: "1px solid #c3cedc",
        borderRadius: "8px",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div>
        <Text weight="semibold" size={300} style={{ color: "#1e293b" }}>
          Confirm this change
        </Text>
        <div style={{ fontSize: "12px", marginTop: "4px", color: "#475569" }}>
          {toolName} on {args?.sheet || ""}!{args?.address || ""}
          {cells ? ` · ${cells} cells` : ""}
        </div>
      </div>

      <div style={{ fontSize: "11px", color: "#616161" }}>
        Review before Excel is changed.
      </div>

      <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
        <Button size="small" appearance="secondary" onClick={onReject}>
          Decline
        </Button>
        <Button size="small" appearance="primary" onClick={onApprove}>
          Apply
        </Button>
      </div>
    </div>
  );
};
