/**
 * Singleton WebSocket Manager
 * Ensures only one WebSocket connection is shared across all components
 */

type MessageHandler = (data: any) => void;

interface WebSocketManagerOptions {
  url: string;
  reconnectInterval?: number;
}

class WebSocketManager {
  private static instance: WebSocketManager | null = null;
  private ws: WebSocket | null = null;
  private url: string = '';
  private reconnectInterval: number = 5000;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private isConnecting: boolean = false;
  private connectionCount: number = 0;

  private constructor() {}

  static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      WebSocketManager.instance = new WebSocketManager();
    }
    return WebSocketManager.instance;
  }

  /**
   * Initialize and connect (called by first component)
   */
  connect(options?: WebSocketManagerOptions): void {
    this.connectionCount++;
    
    if (options?.url) {
      this.url = options.url;
    }
    if (options?.reconnectInterval) {
      this.reconnectInterval = options.reconnectInterval;
    }

    // Auto-detect URL if not provided
    if (!this.url) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      const port = process.env.REACT_APP_BACKEND_URL?.split(':')[2]?.replace(/\D/g, '') || '5051';
      this.url = `${protocol}//${host}:${port}/ws/status`;
    }

    // Only connect if not already connected or connecting
    if (!this.ws && !this.isConnecting) {
      this.doConnect();
    }
  }

  private doConnect(): void {
    if (this.isConnecting) return;
    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.isConnecting = false;
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Notify all handlers
          this.messageHandlers.forEach(handler => {
            try {
              handler(data);
            } catch (e) {
              console.error('[WSManager] Handler error:', e);
            }
          });
        } catch (e) {
          // Ignore parse errors
        }
      };

      this.ws.onclose = () => {
        this.isConnecting = false;
        this.stopHeartbeat();
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.isConnecting = false;
        this.stopHeartbeat();
      };
    } catch (e) {
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    // Only reconnect if there are still active subscribers
    if (this.connectionCount > 0) {
      this.reconnectTimeout = setTimeout(() => {
        this.doConnect();
      }, this.reconnectInterval);
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ action: 'ping' }));
        } catch (e) {
          // Will reconnect on close
        }
      }
    }, 30000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Subscribe to messages
   */
  subscribe(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    
    // Return unsubscribe function
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  /**
   * Disconnect (called when component unmounts)
   */
  disconnect(): void {
    this.connectionCount--;
    
    // Only actually disconnect if no more subscribers
    if (this.connectionCount <= 0) {
      this.connectionCount = 0;
      this.stopHeartbeat();
      
      if (this.reconnectTimeout) {
        clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = null;
      }
      
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }
    }
  }

  /**
   * Send a message
   */
  send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Force reconnect
   */
  reconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.doConnect();
  }
}

export const wsManager = WebSocketManager.getInstance();
export default WebSocketManager;
