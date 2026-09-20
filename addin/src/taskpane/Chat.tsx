import React, { useState } from "react";
import { Button, Input, Text } from "@fluentui/react-components";

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
}

interface ChatProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  isLoading: boolean;
}

export const Chat: React.FC<ChatProps> = ({ messages, onSendMessage, isLoading }) => {
  const [input, setInput] = useState<string>("");

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
      {/* Quick Action Chips */}
      <div
        style={{
          display: "flex",
          gap: "6px",
          padding: "8px 12px",
          overflowX: "auto",
          backgroundColor: "#fbfbfb",
          borderBottom: "1px solid #f0f0f0",
        }}
      >
        <Button size="small" appearance="outline" onClick={() => onSendMessage("Analyze this workbook")}>
          Analyze
        </Button>
        <Button size="small" appearance="outline" onClick={() => onSendMessage("Explain selected formula")}>
          Explain Formula
        </Button>
        <Button size="small" appearance="outline" onClick={() => onSendMessage("Clean whitespace in selection")}>
          Clean Data
        </Button>
        <Button size="small" appearance="outline" onClick={() => onSendMessage("Create pivot table from selection")}>
          Pivot Table
        </Button>
      </div>

      {/* Message Stream */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              alignSelf: m.sender === "user" ? "flex-end" : "flex-start",
              maxWidth: "85%",
              padding: "8px 12px",
              borderRadius: "8px",
              backgroundColor: m.sender === "user" ? "#0078d4" : "#ffffff",
              color: m.sender === "user" ? "#ffffff" : "#242424",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              fontSize: "13px",
              lineHeight: "1.4",
              whiteSpace: "pre-wrap",
            }}
          >
            {m.text}
          </div>
        ))}
        {isLoading && (
          <Text size={200} italic style={{ color: "#616161" }}>
            ExcelPilot is thinking...
          </Text>
        )}
      </div>

      {/* Input Box */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          padding: "10px 12px",
          backgroundColor: "#ffffff",
          borderTop: "1px solid #e0e0e0",
        }}
      >
        <Input
          style={{ flex: 1 }}
          placeholder="Ask ExcelPilot (e.g. Total sales by region)..."
          value={input}
          onChange={(_, data) => setInput(data.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <Button appearance="primary" onClick={handleSend} disabled={isLoading || !input.trim()}>
          Send
        </Button>
      </div>
    </div>
  );
};
