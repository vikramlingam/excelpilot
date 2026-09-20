/* global Excel */
import React, { useEffect, useRef, useState } from "react";
import { BridgeRpcClient } from "../bridge/rpc";
import { ApprovalCard } from "./ApprovalCard";
import { Chat, ChatMessage } from "./Chat";
import { StatusBar } from "./StatusBar";
import { ToolLog, ToolLogItem } from "./ToolLog";

export const App: React.FC = () => {
  const [bridgeConnected, setBridgeConnected] = useState<boolean>(false);
  const [modelTier, setModelTier] = useState<string>("Flash");
  const [jevBackend, setJevBackend] = useState<string>("typesafe");
  const [sessionCost, setSessionCost] = useState<number>(0.0);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Hello! I am ExcelPilot. I can help analyze, format, and automate this Excel workbook.",
    },
  ]);
  const [tools, setTools] = useState<ToolLogItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [approvalReq, setApprovalReq] = useState<any | null>(null);

  const bridgeClientRef = useRef<BridgeRpcClient | null>(null);
  const chatWsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // 1. Initialize Bridge WebSocket
    const bridge = new BridgeRpcClient("ws://127.0.0.1:8765/bridge", (connected) => {
      setBridgeConnected(connected);
    });
    bridge.connect();
    bridgeClientRef.current = bridge;

    // 2. Initialize Chat WebSocket
    const connectChatWs = () => {
      const chatWs = new WebSocket("ws://127.0.0.1:8765/chat");
      chatWs.onmessage = (event) => {
        try {
          const ev = JSON.parse(event.data);
          handleChatEvent(ev);
        } catch (err) {
          console.error("Error parsing chat event:", err);
        }
      };
      chatWs.onclose = () => {
        setTimeout(connectChatWs, 3000);
      };
      chatWsRef.current = chatWs;
    };
    connectChatWs();
  }, []);

  const handleChatEvent = (event: any) => {
    if (event.type === "text_delta") {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.sender === "assistant") {
          return [
            ...prev.slice(0, -1),
            { ...last, text: last.text + (event.delta || "") },
          ];
        } else {
          return [
            ...prev,
            { id: String(Date.now()), sender: "assistant", text: event.delta || "" },
          ];
        }
      });
    } else if (event.type === "tier") {
      setModelTier(event.tier === "capable" ? "Capable" : "Flash");
    } else if (event.type === "approval_required") {
      setApprovalReq(event);
    } else if (event.type === "done") {
      setIsLoading(false);
      if (event.cost_usd) setSessionCost((prev) => prev + event.cost_usd);
    }
  };

  const handleSendMessage = async (text: string) => {
    setMessages((prev) => [
      ...prev,
      { id: String(Date.now()), sender: "user", text },
    ]);
    setIsLoading(true);

    let activeSheet = "Sheet1";
    let selection = "A1";

    try {
      await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getActiveWorksheet();
        const sel = context.workbook.getSelectedRange();
        sheet.load("name");
        sel.load("address");
        await context.sync();
        activeSheet = sheet.name;
        selection = sel.address;
      });
    } catch {
      // Fallback if running outside Excel
    }

    if (chatWsRef.current && chatWsRef.current.readyState === WebSocket.OPEN) {
      chatWsRef.current.send(
        JSON.stringify({
          message: text,
          session_id: "addin_session",
          active_sheet: activeSheet,
          selection,
        })
      );
    }
  };

  const handleSelectRange = async (sheetName: string, address: string) => {
    try {
      await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getItem(sheetName);
        const range = sheet.getRange(address);
        range.select();
        await context.sync();
      });
    } catch (err) {
      console.error("Failed to select range:", err);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <StatusBar
        bridgeConnected={bridgeConnected}
        modelTier={modelTier}
        jevBackend={jevBackend}
        sessionCost={sessionCost}
      />
      <ToolLog items={tools} onSelectRange={handleSelectRange} />
      {approvalReq && (
        <ApprovalCard
          toolName={approvalReq.tool}
          args={approvalReq.args}
          probs={approvalReq.probs}
          onApprove={() => setApprovalReq(null)}
          onReject={() => setApprovalReq(null)}
        />
      )}
      <Chat
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
      />
    </div>
  );
};
