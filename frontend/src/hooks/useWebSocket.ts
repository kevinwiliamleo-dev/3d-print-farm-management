/**
 * WebSocket hook for real-time printer status updates
 * Uses singleton WebSocketManager to ensure only one connection
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { wsManager } from '../services/WebSocketManager';

interface PrinterStatus {
  printerId: string;
  printerName: string;
  status: string;
  mqttConnected: boolean;
  queueCount?: number;
  currentJob?: string;
  progress?: number;
  printing?: boolean;
}

interface QueueItem {
  queueId: number;
  jobId: number;
  jobName: string | null;
  position: number;
  currentLoop: number;
  loopCount: number;
  status: string;
}

interface PrinterDetailStatus {
  printer: PrinterStatus;
  queue: QueueItem[];
  timestamp: number;
}

interface WebSocketMessage {
  type: 'status_update' | 'printer_status' | 'printer_update' | 'upload_progress' | 'error' | 'pong';
  printers?: PrinterStatus[];
  printer?: PrinterStatus;
  queue?: QueueItem[];
  status?: any;
  printerId?: string;
  message?: string;
  timestamp?: number;
  progress?: UploadProgress;
}

interface UploadProgress {
  percent: number;
  bytes_sent: number;
  total_bytes: number;
  filename: string;
  status: 'starting' | 'uploading' | 'complete' | 'failed' | 'starting_print' | 'print_started' | 'print_failed';
}

interface UseWebSocketOptions {
  printerId?: string;
  onMessage?: (message: WebSocketMessage) => void;
  onStatusUpdate?: (printers: PrinterStatus[]) => void;
  onPrinterUpdate?: (status: PrinterDetailStatus) => void;
  onUploadProgress?: (printerId: string, progress: UploadProgress) => void;
  reconnectInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    onMessage,
    onStatusUpdate,
    onPrinterUpdate,
    onUploadProgress,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [printers, setPrinters] = useState<PrinterStatus[]>([]);
  const [printerDetail, setPrinterDetail] = useState<PrinterDetailStatus | null>(null);
  
  // Store callbacks in refs to avoid re-subscribing when they change
  const onMessageRef = useRef(onMessage);
  const onStatusUpdateRef = useRef(onStatusUpdate);
  const onPrinterUpdateRef = useRef(onPrinterUpdate);
  const onUploadProgressRef = useRef(onUploadProgress);
  
  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
    onStatusUpdateRef.current = onStatusUpdate;
    onPrinterUpdateRef.current = onPrinterUpdate;
    onUploadProgressRef.current = onUploadProgress;
  }, [onMessage, onStatusUpdate, onPrinterUpdate, onUploadProgress]);

  // Message handler
  const handleMessage = useCallback((data: WebSocketMessage) => {
    setLastMessage(data);
    
    // Call custom handler
    if (onMessageRef.current) {
      try {
        onMessageRef.current(data);
      } catch (err) {
        console.error('[WS] Error in onMessage callback:', err);
      }
    }
    
    // Handle different message types
    switch (data.type) {
      case 'status_update':
        if (data.printers && Array.isArray(data.printers)) {
          try {
            const transformed = data.printers.map((p: any) => ({
              printerId: p.printer_id || p.printerId,
              printerName: p.printer_name || p.printerName,
              status: p.status,
              mqttConnected: p.mqtt_connected || p.mqttConnected,
              queueCount: p.queue_count || p.queueCount,
              currentJob: p.current_job || p.currentJob,
            }));
            setPrinters(transformed);
            if (onStatusUpdateRef.current) {
              onStatusUpdateRef.current(transformed);
            }
          } catch (err) {
            console.error('[WS] Error processing status update:', err);
          }
        }
        break;
        
      case 'printer_status':
        if (data.printer) {
          try {
            const detail: PrinterDetailStatus = {
              printer: {
                printerId: (data.printer as any).printer_id || data.printer.printerId,
                printerName: (data.printer as any).printer_name || data.printer.printerName,
                status: data.printer.status,
                mqttConnected: (data.printer as any).mqtt_connected || data.printer.mqttConnected,
                progress: data.printer.progress,
                printing: data.printer.printing,
              },
              queue: (data.queue || []).map((q: any) => ({
                queueId: q.queue_id || q.queueId,
                jobId: q.job_id || q.jobId,
                jobName: q.job_name || q.jobName,
                position: q.position,
                currentLoop: q.current_loop || q.currentLoop,
                loopCount: q.loop_count || q.loopCount,
                status: q.status,
              })),
              timestamp: data.timestamp || Date.now() / 1000,
            };
            setPrinterDetail(detail);
            if (onPrinterUpdateRef.current) {
              onPrinterUpdateRef.current(detail);
            }
          } catch (err) {
            console.error('Error processing printer status:', err);
          }
        }
        break;
        
      case 'printer_update':
        // Individual printer update - handled silently
        break;
      
      case 'upload_progress':
        const uploadData = data as any;
        if (uploadData.printer_id && uploadData.progress && onUploadProgressRef.current) {
          onUploadProgressRef.current(uploadData.printer_id as string, uploadData.progress);
        }
        break;
        
      case 'pong':
        // Heartbeat response - ignore
        break;
        
      case 'error':
        console.error('WebSocket error message:', data.message);
        break;
    }
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    // Connect to singleton manager
    wsManager.connect();
    
    // Subscribe to messages
    const unsubscribe = wsManager.subscribe(handleMessage);
    
    // Check connection status periodically
    const checkInterval = setInterval(() => {
      setIsConnected(wsManager.isConnected());
    }, 1000);
    
    return () => {
      unsubscribe();
      clearInterval(checkInterval);
      wsManager.disconnect();
    };
  }, [handleMessage]);

  // Handle visibility change
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        if (!wsManager.isConnected()) {
          wsManager.reconnect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const sendMessage = useCallback((message: any) => {
    wsManager.send(message);
  }, []);

  const refresh = useCallback(() => {
    sendMessage({ action: 'refresh' });
  }, [sendMessage]);

  const reconnect = useCallback(() => {
    wsManager.reconnect();
  }, []);

  return {
    isConnected,
    lastMessage,
    printers,
    printerDetail,
    sendMessage,
    refresh,
    disconnect: () => wsManager.disconnect(),
    reconnect,
  };
}

export default useWebSocket;
