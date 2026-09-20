import React, { useState } from "react";
import { Button, Input, Text } from "@fluentui/react-components";
import { Dismiss20Regular } from "@fluentui/react-icons";
import { theme } from "./theme";

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  badge?: string;
  description: string;
  latency?: string;
}

export const AVAILABLE_MODELS: ModelOption[] = [
  {
    id: "auto",
    name: "Auto",
    provider: "ExcelPilot",
    badge: "Default",
    latency: "~0.7s",
    description: "Routes to Mercury for everyday edits; Luna only when the task is complex.",
  },
  {
    id: "inception/mercury-2.5",
    name: "Mercury 2.5",
    provider: "Inception",
    badge: "Fastest",
    latency: "0.7s",
    description: "Fastest measured model for Excel tools. Parallel calls, no reasoning tax.",
  },
  {
    id: "qwen/qwen3.5-flash-02-23",
    name: "Qwen 3.5 Flash",
    provider: "Alibaba",
    badge: "Cheap",
    latency: "1.3s",
    description: "Inexpensive flash model. Good for formatting and simple formulas.",
  },
  {
    id: "openai/gpt-4o-mini",
    name: "GPT-4o mini",
    provider: "OpenAI",
    badge: "Cheap",
    latency: "~1s",
    description: "Small, reliable tool-caller. Low cost for cleanup and lookups.",
  },
  {
    id: "google/gemini-2.5-flash",
    name: "Gemini 2.5 Flash",
    provider: "Google",
    badge: "Cheap",
    latency: "~1s",
    description: "High-speed, large context. Some Gemini variants ignore reasoning=off.",
  },
  {
    id: "deepseek/deepseek-chat",
    name: "DeepSeek V3",
    provider: "DeepSeek",
    badge: "Value",
    latency: "~1.5s",
    description: "Low-cost general model. Fine for data transforms.",
  },
  {
    id: "openai/gpt-5.6-luna",
    name: "GPT-5.6 Luna",
    provider: "OpenAI",
    badge: "Capable",
    latency: "1.7s",
    description: "Used automatically for hard tasks. More accurate, still inexpensive.",
  },
];

interface SettingsModalProps {
  isOpen: boolean;
  selectedModel: string;
  onSelectModel: (modelId: string) => void;
  onClose: () => void;
  sessionCost?: number;
  jevBackend?: string;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  selectedModel,
  onSelectModel,
  onClose,
  sessionCost = 0,
  jevBackend = "local",
}) => {
  const [customModelInput, setCustomModelInput] = useState<string>(() => {
    return selectedModel && !AVAILABLE_MODELS.some((m) => m.id === selectedModel)
      ? selectedModel
      : "";
  });
  const [showCustomInput, setShowCustomInput] = useState<boolean>(() => {
    return Boolean(selectedModel && !AVAILABLE_MODELS.some((m) => m.id === selectedModel));
  });

  if (!isOpen) return null;

  const handleSelect = (id: string) => {
    setShowCustomInput(false);
    onSelectModel(id);
    try {
      localStorage.setItem("excelpilot_model", id);
    } catch {
      // ignore
    }
  };

  const handleApplyCustom = () => {
    if (!customModelInput.trim()) return;
    const model = customModelInput.trim();
    onSelectModel(model);
    try {
      localStorage.setItem("excelpilot_model", model);
      localStorage.setItem("excelpilot_custom_model", model);
    } catch {
      // ignore
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.45)",
        backdropFilter: "blur(4px)",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-end",
        animation: "fadeIn 0.2s ease-out",
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: "#ffffff",
          borderTopLeftRadius: "16px",
          borderTopRightRadius: "16px",
          maxHeight: "88vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 -4px 24px rgba(0, 0, 0, 0.15)",
          animation: "slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 16px",
            borderBottom: `1px solid ${theme.border}`,
            background: "linear-gradient(180deg, #071525 0%, #0b1f3a 100%)",
          }}
        >
          <div>
            <Text weight="semibold" size={400} style={{ color: "#f8fafc" }}>
              Model
            </Text>
            <div style={{ fontSize: "11px", color: "#94a3b8" }}>
              Fast, low-cost models. Custom OpenRouter IDs still work.
            </div>
          </div>
          <Button
            appearance="subtle"
            icon={<Dismiss20Regular style={{ color: "#cbd5e1" }} />}
            onClick={onClose}
            aria-label="Close"
          />
        </div>

        {/* Body / Model List */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "14px 16px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            backgroundColor: theme.bg,
          }}
        >
          <div style={{ fontSize: "11px", fontWeight: 600, color: theme.textMuted, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Models
          </div>

          {AVAILABLE_MODELS.map((m) => {
            const isSelected = selectedModel === m.id && !showCustomInput;
            return (
              <div
                key={m.id}
                onClick={() => handleSelect(m.id)}
                style={{
                  padding: "11px 12px",
                  borderRadius: "8px",
                  border: isSelected ? `1.5px solid ${theme.accent}` : `1px solid ${theme.border}`,
                  backgroundColor: isSelected ? theme.accentSoft : theme.surface,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                  position: "relative",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Text weight="semibold" size={300} style={{ color: theme.slateDark }}>
                      {m.name}
                    </Text>
                    {m.latency && (
                      <span style={{ fontSize: 10, color: theme.textMuted }}>{m.latency}</span>
                    )}
                    {m.badge && (
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 600,
                          letterSpacing: "0.03em",
                          textTransform: "uppercase",
                          color: isSelected ? theme.accentDark : theme.textMuted,
                          backgroundColor: isSelected ? "#dce6f0" : theme.surfaceMuted,
                          padding: "2px 6px",
                          borderRadius: 4,
                        }}
                      >
                        {m.badge}
                      </span>
                    )}
                  </div>
                  {isSelected && (
                    <span style={{ fontSize: 11, fontWeight: 600, color: theme.accent }}>Selected</span>
                  )}
                </div>

                <div style={{ fontSize: "12px", color: theme.textMuted, lineHeight: "1.4" }}>
                  {m.description}
                </div>

                <div style={{ fontSize: "10px", color: theme.textFaint, marginTop: "2px" }}>
                  {m.provider}{m.id !== "auto" ? ` · ${m.id}` : ""}
                </div>
              </div>
            );
          })}

          {/* Custom Model Option */}
          <div
            onClick={() => setShowCustomInput(true)}
            style={{
              padding: "11px 12px",
              borderRadius: "8px",
              border: showCustomInput ? `1.5px solid ${theme.accent}` : `1px solid ${theme.border}`,
              backgroundColor: showCustomInput ? theme.accentSoft : theme.surface,
              cursor: "pointer",
              transition: "all 0.15s ease",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <Text weight="semibold" size={300} style={{ color: theme.slateDark }}>
                  Custom OpenRouter ID
                </Text>
                <div style={{ fontSize: "12px", color: theme.textMuted }}>
                  e.g. inception/mercury-2.5
                </div>
              </div>
              {showCustomInput && (
                <span style={{ fontSize: 11, fontWeight: 600, color: theme.accent }}>On</span>
              )}
            </div>

            {showCustomInput && (
              <div
                style={{ display: "flex", gap: "8px", marginTop: "4px" }}
                onClick={(e) => e.stopPropagation()}
              >
                <Input
                  style={{ flex: 1 }}
                  placeholder="provider/model-id"
                  value={customModelInput}
                  onChange={(_, data) => setCustomModelInput(data.value)}
                />
                <Button appearance="primary" size="small" onClick={handleApplyCustom}>
                  Set
                </Button>
              </div>
            )}
          </div>

          {/* Stats Bar in Settings */}
          <div
            style={{
              marginTop: "12px",
              padding: "10px 12px",
              backgroundColor: theme.surface,
              borderRadius: "8px",
              border: `1px solid ${theme.border}`,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "11px",
              color: theme.textMuted,
            }}
          >
            <div>
              <span>Judge: </span>
              <span style={{ fontWeight: 600, color: theme.slate }}>{jevBackend}</span>
            </div>
            <div>
              <span>Session Cost: </span>
              <span style={{ fontWeight: 600, color: theme.slate }}>${sessionCost.toFixed(4)}</span>
            </div>
          </div>

          <div
            style={{
              padding: "12px",
              backgroundColor: theme.surface,
              borderRadius: "8px",
              border: `1px solid ${theme.border}`,
              fontSize: "12px",
              color: theme.textMuted,
              lineHeight: 1.5,
            }}
          >
            <div style={{ fontWeight: 700, color: theme.slateDark, marginBottom: 4 }}>About</div>
            ExcelPilot talks to the open workbook through Office.js. Ask it to format, total,
            chart, or explain a range. Large writes wait for Apply. Support:
            github.com/vikramlingam/excelpilot
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "12px 18px",
            borderTop: `1px solid ${theme.border}`,
            backgroundColor: theme.surface,
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <Button appearance="primary" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  );
};
