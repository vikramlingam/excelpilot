import React, { useState, useRef, useEffect } from "react";
import { Button, Text } from "@fluentui/react-components";
import { Send20Regular, Attach20Regular, Dismiss16Regular, DocumentPdf20Regular } from "@fluentui/react-icons";
import { theme } from "./theme";

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
}

export interface ChatAttachment {
  name: string;
  base64: string;
}

interface ChatProps {
  messages: ChatMessage[];
  onSendMessage: (text: string, attachment?: ChatAttachment) => void;
  isLoading: boolean;
  statusText?: string;
}

export const Chat: React.FC<ChatProps> = ({
  messages,
  onSendMessage,
  isLoading,
  statusText,
}) => {
  const [input, setInput] = useState<string>("");
  const [attachment, setAttachment] = useState<ChatAttachment | null>(null);
  const [attachError, setAttachError] = useState<string>("");
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragDepth = useRef(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, statusText, isLoading]);

  const acceptPdf = async (file: File | undefined | null) => {
    setAttachError("");
    if (!file) return;
    const name = file.name || "document.pdf";
    if (!name.toLowerCase().endsWith(".pdf")) {
      setAttachError("Only PDF files can be attached.");
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      setAttachError("PDF must be 8 MB or smaller.");
      return;
    }
    try {
      const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = String(reader.result || "");
          const comma = result.indexOf(",");
          resolve(comma >= 0 ? result.slice(comma + 1) : result);
        };
        reader.onerror = () => reject(reader.error || new Error("Failed to read file"));
        reader.readAsDataURL(file);
      });
      setAttachment({ name, base64 });
    } catch {
      setAttachError("Could not read that PDF.");
    }
  };

  const handleSend = () => {
    if (isLoading) return;
    const text = input.trim();
    if (!text && !attachment) return;
    onSendMessage(text, attachment || undefined);
    setInput("");
    setAttachment(null);
    setAttachError("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const onDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepth.current += 1;
    if (e.dataTransfer.types.includes("Files")) setIsDragging(true);
  };
  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setIsDragging(false);
  };
  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepth.current = 0;
    setIsDragging(false);
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    void acceptPdf(file);
  };
  const canSend = !isLoading && (!!input.trim() || !!attachment);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        overflow: "hidden",
        backgroundColor: theme.bg,
        fontFamily: theme.font,
        position: "relative",
      }}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {isDragging && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 20,
            backgroundColor: "rgba(37, 99, 235, 0.08)",
            border: `2px dashed ${theme.accent}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              backgroundColor: theme.surface,
              border: `1px solid ${theme.accentBorder}`,
              borderRadius: theme.radius,
              padding: "14px 18px",
              color: theme.accentDark,
              fontWeight: 600,
              fontSize: 13,
              boxShadow: theme.shadowMd,
            }}
          >
            Drop PDF to attach
          </div>
        </div>
      )}
      {/* Message Stream */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 14px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {messages.map((m) => {
          const isUser = m.sender === "user";

          if (m.id === "welcome") {
            return (
              <div
                key={m.id}
                style={{
                  backgroundColor: theme.surface,
                  border: `1px solid ${theme.border}`,
                  borderRadius: theme.radius,
                  padding: "14px 16px",
                  boxShadow: theme.shadow,
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                  marginBottom: "4px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <Text weight="semibold" size={300} style={{ color: theme.slateDark }}>
                    ExcelPilot
                  </Text>
                </div>
                <div style={{ fontSize: "12.5px", color: theme.textMuted, lineHeight: "1.5" }}>
                  {m.text}
                </div>
              </div>
            );
          }

          return (
            <div
              key={m.id}
              style={{
                alignSelf: isUser ? "flex-end" : "flex-start",
                maxWidth: "88%",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              {!isUser && (
                <span
                  style={{
                    fontSize: 10.5,
                    fontWeight: 600,
                    color: theme.textFaint,
                    paddingLeft: 4,
                    letterSpacing: "0.02em",
                  }}
                >
                  ExcelPilot
                </span>
              )}
              <div
                style={{
                  padding: "10px 13px",
                  borderRadius: isUser ? "10px 10px 3px 10px" : "10px 10px 10px 3px",
                  background: isUser
                    ? "linear-gradient(160deg, #1d4ed8 0%, #1239a8 100%)"
                    : theme.surface,
                  color: isUser ? "#f8fbff" : theme.text,
                  border: isUser ? "none" : `1px solid ${theme.border}`,
                  boxShadow: theme.shadow,
                  fontSize: "13px",
                  lineHeight: "1.45",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {m.text}
              </div>
            </div>
          );
        })}

        {/* Live Active Status pill */}
        {isLoading && (
          <div
            style={{
              alignSelf: "flex-start",
              display: "inline-flex",
              alignItems: "center",
              gap: "7px",
              padding: "6px 12px",
              borderRadius: "16px",
              backgroundColor: theme.surface,
              border: `1px solid ${theme.border}`,
              boxShadow: theme.shadow,
              fontSize: "11.5px",
              color: theme.slate,
              fontWeight: 500,
            }}
          >
            <span
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                backgroundColor: theme.accent,
                display: "inline-block",
                animation: "pulse 1.2s infinite",
              }}
            />
            <span>{statusText || "Working on your spreadsheet…"}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div
        style={{
          padding: "10px 12px",
          backgroundColor: theme.surface,
          borderTop: `1px solid ${theme.border}`,
        }}
      >
        {attachment && (
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              marginBottom: 8,
              padding: "4px 8px",
              borderRadius: 16,
              backgroundColor: theme.accentSoft,
              border: `1px solid ${theme.accentBorder}`,
              fontSize: 12,
              color: theme.accentDark,
              fontWeight: 600,
              maxWidth: "100%",
            }}
          >
            <DocumentPdf20Regular />
            <span
              style={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: 220,
              }}
              title={attachment.name}
            >
              {attachment.name}
            </span>
            <button
              type="button"
              onClick={() => setAttachment(null)}
              aria-label="Remove attachment"
              style={{
                border: "none",
                background: "transparent",
                cursor: "pointer",
                padding: 2,
                display: "flex",
                color: theme.textMuted,
              }}
            >
              <Dismiss16Regular />
            </button>
          </div>
        )}
        {attachError ? (
          <div style={{ fontSize: 11, color: theme.danger, marginBottom: 6 }}>{attachError}</div>
        ) : null}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            backgroundColor: theme.surfaceMuted,
            borderRadius: "8px",
            padding: "4px 6px 4px 8px",
            border: `1px solid ${theme.border}`,
            transition: "all 0.15s ease",
          }}
          onFocusCapture={(e) => {
            e.currentTarget.style.borderColor = theme.accent;
            e.currentTarget.style.backgroundColor = theme.surface;
            e.currentTarget.style.boxShadow = "0 0 0 3px rgba(61, 90, 128, 0.15)";
          }}
          onBlurCapture={(e) => {
            e.currentTarget.style.borderColor = theme.border;
            e.currentTarget.style.backgroundColor = theme.surfaceMuted;
            e.currentTarget.style.boxShadow = "none";
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            style={{ display: "none" }}
            onChange={(e) => {
              const file = e.target.files && e.target.files[0];
              void acceptPdf(file);
              e.target.value = "";
            }}
          />
          <Button
            appearance="transparent"
            size="small"
            icon={<Attach20Regular />}
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            style={{
              minWidth: 32,
              width: 32,
              height: 32,
              padding: 0,
              color: attachment ? theme.accent : theme.textMuted,
            }}
            aria-label="Attach PDF"
            title="Attach PDF"
          />
          <textarea
            rows={1}
            style={{
              flex: 1,
              border: "none",
              outline: "none",
              backgroundColor: "transparent",
              fontSize: "13px",
              lineHeight: "1.4",
              resize: "none",
              fontFamily: theme.font,
              color: theme.text,
              padding: "4px 0",
              maxHeight: "80px",
            }}
            placeholder={attachment ? "Add a note, or send to extract tables…" : "Ask about this sheet…"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <Button
            appearance="primary"
            size="small"
            icon={<Send20Regular />}
            onClick={handleSend}
            disabled={!canSend}
            style={{
              borderRadius: "6px",
              width: "32px",
              height: "32px",
              minWidth: "32px",
              padding: 0,
              backgroundColor: theme.accent,
            }}
            aria-label="Send"
          />
        </div>
      </div>
    </div>
  );
};
