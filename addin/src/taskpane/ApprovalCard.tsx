import React from "react";
import { Button, Text, ProgressBar } from "@fluentui/react-components";

interface ApprovalCardProps {
  toolName: string;
  args: any;
  probs: Record<string, number>;
  onApprove: () => void;
  onReject: () => void;
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  toolName,
  args,
  probs,
  onApprove,
  onReject,
}) => {
  return (
    <div
      style={{
        margin: "8px 12px",
        padding: "10px",
        backgroundColor: "#fffdf5",
        border: "1px solid #ffd335",
        borderRadius: "6px",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div>
        <Text weight="semibold" size={300} style={{ color: "#795e00" }}>
          Action Approval Required
        </Text>
        <div style={{ fontSize: "12px", marginTop: "4px" }}>
          Operation: <b>{toolName}</b> on <b>{args?.sheet || ""}!{args?.address || ""}</b>
        </div>
      </div>

      <div style={{ fontSize: "11px", color: "#616161" }}>
        Jev Confidence:
        <div style={{ display: "flex", gap: "10px", marginTop: "2px" }}>
          <span>Requested: {((probs?.requested ?? 0.5) * 100).toFixed(0)}%</span>
          <span>Scoped: {((probs?.scoped ?? 0.5) * 100).toFixed(0)}%</span>
          <span>Reversible: {((probs?.reversible ?? 0.5) * 100).toFixed(0)}%</span>
        </div>
      </div>

      <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
        <Button size="small" appearance="secondary" onClick={onReject}>
          Reject
        </Button>
        <Button size="small" appearance="primary" onClick={onApprove}>
          Approve Change
        </Button>
      </div>
    </div>
  );
};
