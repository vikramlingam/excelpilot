/* global Excel */
import React, { useEffect, useRef, useState } from "react";
import { BridgeRpcClient } from "../bridge/rpc";
import { ApprovalCard } from "./ApprovalCard";
import { Chat, ChatMessage, ChatAttachment } from "./Chat";
import { Header } from "./Header";
import { SettingsModal, AVAILABLE_MODELS } from "./SettingsModal";
import { ToolLog, ToolLogItem } from "./ToolLog";

export const App: React.FC = () => {
  const [bridgeConnected, setBridgeConnected] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<string>(() => {
    try {
      return localStorage.getItem("excelpilot_model") || "auto";
    } catch {
      return "auto";
    }
  });
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [modelTier, setModelTier] = useState<string>("Flash");
  const [jevBackend, setJevBackend] = useState<string>("local");
  const [sessionCost, setSessionCost] = useState<number>(0.0);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Hello. Ask me to format, total, chart, or explain anything on this sheet. You can also attach a PDF invoice or statement.",
    },
  ]);
  const [tools, setTools] = useState<ToolLogItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [statusText, setStatusText] = useState<string>("");
  const [approvalReq, setApprovalReq] = useState<any | null>(null);

  const bridgeClientRef = useRef<BridgeRpcClient | null>(null);
  const chatWsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const isHttps = typeof window !== "undefined" && window.location.protocol === "https:";
    const host = typeof window !== "undefined" && window.location.host ? window.location.host : "127.0.0.1:8765";
    const wsProto = isHttps ? "wss:" : "ws:";
    const bridgeUrl = `${wsProto}//${host}/bridge`;
    const chatUrl = `${wsProto}//${host}/chat`;

    // 1. Initialize Bridge WebSocket
    const bridge = new BridgeRpcClient(bridgeUrl, (connected) => {
      setBridgeConnected(connected);
    });
    bridge.connect();
    bridgeClientRef.current = bridge;

    // 2. Initialize Chat WebSocket
    const connectChatWs = () => {
      const chatWs = new WebSocket(chatUrl);
      chatWs.onmessage = (event) => {
        try {
          const ev = JSON.parse(event.data);
          handleChatEvent(ev);
        } catch (err) {
          console.error("Error parsing chat event:", err);
        }
      };
      chatWs.onerror = () => {
        setStatusText("Chat socket error");
      };
      chatWs.onclose = () => {
        setIsLoading((was) => {
          if (was) {
            setStatusText("");
            setMessages((prev) => [
              ...prev,
              {
                id: String(Date.now()),
                sender: "assistant",
                text: "Lost connection to ExcelPilot while working. Wait for Connected, then send again.",
              },
            ]);
          }
          return false;
        });
        setTimeout(connectChatWs, 1500);
      };
      chatWsRef.current = chatWs;
    };
    connectChatWs();

    fetch("/health")
      .then((r) => r.json())
      .then((h) => {
        const backend = h?.jev?.backend;
        if (backend) setJevBackend(backend);
      })
      .catch(() => undefined);

    const hideOfficeInfo = () => {
      // 1. Hide any element injected directly into body that is not #root
      document.querySelectorAll("body > *:not(#root)").forEach((el) => {
        const html = el as HTMLElement;
        html.style.setProperty("display", "none", "important");
        html.style.setProperty("visibility", "hidden", "important");
        html.style.setProperty("opacity", "0", "important");
        html.style.setProperty("pointer-events", "none", "important");
      });

      // 2. Scan all elements for info / floating characteristics in the top right
      document.querySelectorAll("button, a, div, span, svg").forEach((el) => {
        const html = el as HTMLElement;
        if (html.closest("#root header")) return;
        const label = `${html.getAttribute("aria-label") || ""} ${html.getAttribute("title") || ""} ${html.className || ""} ${html.id || ""}`.toLowerCase();
        const text = (html.innerText || html.textContent || "").trim().toLowerCase();
        const isInfo = label.includes("info") || label.includes("task pane information") || text === "i" || text === "🛈" || text === "ℹ";
        if (isInfo) {
          const rect = html.getBoundingClientRect();
          if (rect.top < 80 && rect.right > window.innerWidth - 80) {
            html.style.setProperty("display", "none", "important");
            html.style.setProperty("visibility", "hidden", "important");
            html.style.setProperty("pointer-events", "none", "important");
            try { html.remove(); } catch {}
          }
        }
      });

      // 3. Scan for any fixed/absolute floating element in the top right corner
      document.querySelectorAll("body *").forEach((el) => {
        const html = el as HTMLElement;
        if (html.id === "root" || html.closest("#root header")) return;
        const style = window.getComputedStyle(html);
        if (style.position === "fixed" || style.position === "absolute") {
          const rect = html.getBoundingClientRect();
          if (rect.top < 60 && rect.right > window.innerWidth - 60 && rect.width < 70 && rect.height < 70) {
            html.style.setProperty("display", "none", "important");
            html.style.setProperty("visibility", "hidden", "important");
            try { html.remove(); } catch {}
          }
        }
      });
    };
    hideOfficeInfo();
    const timer = window.setInterval(hideOfficeInfo, 600);
    const observer = new MutationObserver(() => hideOfficeInfo());
    observer.observe(document.documentElement, { childList: true, subtree: true });
    return () => {
      window.clearInterval(timer);
      observer.disconnect();
    };
  }, []);

  const handleChatEvent = (event: any) => {
    if (event.type === "status") {
      setStatusText(event.message || "");
    } else if (event.type === "intent") {
      setStatusText(`Intent: ${event.intent} — selecting tools...`);
    } else if (event.type === "text_delta") {
      setStatusText(""); // Clear status once streaming text starts
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.sender === "assistant" && last.id !== "welcome") {
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
      const label = event.model ? event.model.split("/").pop() : event.tier;
      setStatusText(`Model: ${label} — executing...`);
    } else if (event.type === "approval_required") {
      setApprovalReq(event);
      setStatusText("Waiting for your approval…");
    } else if (event.type === "tool_call") {
      setStatusText(`Running ${event.tool || "tool"}…`);
      setTools((prev) => [
        ...prev,
        {
          id: event.id || String(Date.now()),
          name: event.tool || "tool",
          args: event.args || {},
          status: "running",
        },
      ]);
    } else if (event.type === "tool_result") {
      setStatusText(`Finished ${event.tool || "tool"}`);
      setTools((prev) =>
        prev.map((t) =>
          t.id === event.id || t.name === event.tool
            ? { ...t, status: "done", resultPreview: event.result }
            : t
        )
      );
    } else if (event.type === "error") {
      setIsLoading(false);
      setStatusText("");
      setMessages((prev) => [
        ...prev,
        { id: String(Date.now()), sender: "assistant", text: `Error: ${event.message}` },
      ]);
    } else if (event.type === "done") {
      setIsLoading(false);
      setStatusText("");
      if (event.cost_usd) setSessionCost((prev) => prev + event.cost_usd);
      const reply = String(event.full_text || "").trim();
      const toolsUsed: string[] = event.tools_used || [];
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        const alreadyStreamed =
          last && last.sender === "assistant" && last.id !== "welcome" && last.text.trim().length > 0;
        if (alreadyStreamed) {
          if (reply && reply.length > last.text.trim().length) {
            return [...prev.slice(0, -1), { ...last, text: reply }];
          }
          return prev;
        }
        const fallback =
          toolsUsed.length > 0
            ? `Done. Applied ${toolsUsed.join(", ")}.`
            : "Done — no sheet changes.";
        return [...prev, { id: String(Date.now()), sender: "assistant", text: reply || fallback }];
      });
    }
  };

  const handleSendMessage = async (text: string, attachment?: ChatAttachment) => {
    const display = attachment
      ? text
        ? `${text}\n📎 ${attachment.name}`
        : `📎 ${attachment.name}`
      : text;
    setMessages((prev) => [
      ...prev,
      { id: String(Date.now()), sender: "user", text: display },
    ]);
    setIsLoading(true);
    setStatusText(attachment ? "Reading PDF…" : "Connecting...");
    setApprovalReq(null);

    if (!chatWsRef.current || chatWsRef.current.readyState !== WebSocket.OPEN) {
      setIsLoading(false);
      setStatusText("");
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now()),
          sender: "assistant",
          text: "Still connecting to ExcelPilot backend. Please ensure the server is running.",
        },
      ]);
      return;
    }

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

    chatWsRef.current.send(
      JSON.stringify({
        message: text,
        session_id: "addin_session",
        active_sheet: activeSheet,
        selection,
        model: selectedModel,
        ...(attachment
          ? { file_name: attachment.name, file_base64: attachment.base64 }
          : {}),
      })
    );
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

  const handleSelectModel = (modelId: string) => {
    setSelectedModel(modelId);
  };

  const getModelDisplayName = (): string => {
    if (selectedModel === "auto") return "Auto";
    const found = AVAILABLE_MODELS.find((m) => m.id === selectedModel);
    if (found) {
      // Return short badge name
      return found.name.split(" ")[0] + (found.name.split(" ")[1] ? " " + found.name.split(" ")[1] : "");
    }
    return selectedModel.split("/").pop() || selectedModel;
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        backgroundColor: "#eef3fb",
        position: "relative",
      }}
    >
      <Header
        bridgeConnected={bridgeConnected}
        selectedModelName={getModelDisplayName()}
        sessionCost={sessionCost}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      <ToolLog items={tools} onSelectRange={handleSelectRange} />

      {approvalReq && (
        <ApprovalCard
          toolName={approvalReq.tool}
          args={approvalReq.args}
          probs={approvalReq.probs}
          cells={approvalReq.cells}
          onApprove={() => {
            chatWsRef.current?.send(
              JSON.stringify({ type: "approval", session_id: "addin_session", approved: true })
            );
            setApprovalReq(null);
            setStatusText("Approved — applying change…");
          }}
          onReject={() => {
            chatWsRef.current?.send(
              JSON.stringify({ type: "approval", session_id: "addin_session", approved: false })
            );
            setApprovalReq(null);
            setStatusText("Change declined");
          }}
        />
      )}

      <Chat
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        statusText={statusText}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        selectedModel={selectedModel}
        onSelectModel={handleSelectModel}
        onClose={() => setIsSettingsOpen(false)}
        sessionCost={sessionCost}
        jevBackend={jevBackend}
      />
    </div>
  );
};
