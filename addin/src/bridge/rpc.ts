import { executeBridgeCall } from "./executor";

export class BridgeRpcClient {
  private ws: WebSocket | null = null;
  private url: string;
  private isConnecting: boolean = false;
  private onStatusChange?: (connected: boolean) => void;

  constructor(
    url?: string,
    onStatusChange?: (connected: boolean) => void
  ) {
    if (url && !url.startsWith("/")) {
      this.url = url;
    } else {
      const path = url || "/bridge";
      const isHttps = typeof window !== "undefined" && window.location.protocol === "https:";
      const host = typeof window !== "undefined" && window.location.host ? window.location.host : "127.0.0.1:8765";
      this.url = `${isHttps ? "wss:" : "ws:"}//${host}${path}`;
    }
    this.onStatusChange = onStatusChange;
  }

  public connect(): void {
    if (this.ws || this.isConnecting) return;
    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.isConnecting = false;
        if (this.onStatusChange) this.onStatusChange(true);
      };

      this.ws.onmessage = async (event: MessageEvent) => {
        try {
          const req = JSON.parse(event.data);
          if (req.id !== undefined && req.method) {
            await this.handleServerRequest(req);
          }
        } catch (err) {
          console.error("Error processing bridge message:", err);
        }
      };

      this.ws.onclose = () => {
        this.cleanup();
        setTimeout(() => this.connect(), 2000);
      };

      this.ws.onerror = () => {
        this.cleanup();
      };
    } catch (err) {
      this.cleanup();
      setTimeout(() => this.connect(), 2000);
    }
  }

  private cleanup(): void {
    this.ws = null;
    this.isConnecting = false;
    if (this.onStatusChange) this.onStatusChange(false);
  }

  private async handleServerRequest(req: { id: number; method: string; params: any }): Promise<void> {
    try {
      const result = await executeBridgeCall(req.method, req.params);
      this.sendResponse({ jsonrpc: "2.0", id: req.id, result });
    } catch (err: any) {
      this.sendResponse({
        jsonrpc: "2.0",
        id: req.id,
        error: {
          code: err.code || "BridgeError",
          message: err.message || "Failed to execute bridge call",
          requirementSet: err.requirementSet,
        },
      });
    }
  }

  private sendResponse(payload: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  public sendNotification(method: string, params: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ jsonrpc: "2.0", method, params }));
    }
  }
}
