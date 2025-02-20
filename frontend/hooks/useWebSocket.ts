import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketOptions {
  reconnectAttempts?: number;
  reconnectDelay?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

interface WebSocketState<T> {
  data: T | null;
  error: Error | null;
  isConnected: boolean;
  send: (message: any) => void;
  reconnect: () => void;
}

export function useWebSocket<T>(url: string, options: WebSocketOptions = {}): WebSocketState<T> {
  const {
    reconnectAttempts = 5,
    reconnectDelay = 3000,
    onConnect,
    onDisconnect,
    onError
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectCount.current = 0;
        onConnect?.();
      };

      ws.current.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          setData(parsedData);
        } catch (e) {
          setError(new Error('Failed to parse WebSocket message'));
        }
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        onDisconnect?.();

        // Attempt to reconnect
        if (reconnectCount.current < reconnectAttempts) {
          reconnectTimeout.current = setTimeout(() => {
            reconnectCount.current += 1;
            connect();
          }, reconnectDelay);
        }
      };

      ws.current.onerror = (event) => {
        setError(new Error('WebSocket error occurred'));
        onError?.(event);
      };

    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to connect'));
    }
  }, [url, reconnectAttempts, reconnectDelay, onConnect, onDisconnect, onError]);

  const disconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close();
    }
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
  }, []);

  const send = useCallback((message: any) => {
    if (ws.current && isConnected) {
      ws.current.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }, [isConnected]);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectCount.current = 0;
    connect();
  }, [connect, disconnect]);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    data,
    error,
    isConnected,
    send,
    reconnect
  };
}

