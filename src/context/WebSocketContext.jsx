import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';

const WebSocketContext = createContext(null);

export const useWebSocket = () => useContext(WebSocketContext);

export const WebSocketProvider = ({ children, isDevMode }) => {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectAttempt = useRef(0);
  const maxReconnectDelay = 30000; // max 30 seconds

  // Pub/Sub listener registry
  // listeners: { "eventType": [cb1, cb2], "*": [cb3] }
  const listeners = useRef({});

  const url = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

  useEffect(() => {
    if (isDevMode) {
      console.log('WS: Dev Mode - Skipping connection');
      return;
    }

    let isComponentMounted = true;

    const connect = () => {
      if (!isComponentMounted) return;

      console.log(`WS: Connecting to ${url}...`);
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('WS: Connected');
        setIsConnected(true);
        reconnectAttempt.current = 0; // reset backoff
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Filter ping messages and respond silently
          if (data.type === 'ping') {
            ws.send(JSON.stringify({ command: 'pong', params: {} }));
            return;
          }

          // Trigger subscribers
          const eventType = data.type;
          
          // Specific listeners
          if (eventType && listeners.current[eventType]) {
            listeners.current[eventType].forEach(cb => cb(data));
          }
          
          // Wildcard listeners (for DevOverlay etc)
          if (listeners.current['*']) {
            listeners.current['*'].forEach(cb => cb(data));
          }

        } catch (err) {
          console.error('WS: Parse error', err);
        }
      };

      ws.onclose = () => {
        if (!isComponentMounted) return;
        setIsConnected(false);
        
        // Exponential backoff: 1s, 2s, 4s, 8s...
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempt.current), maxReconnectDelay);
        console.log(`WS: Disconnected. Reconnecting in ${delay}ms...`);
        reconnectAttempt.current++;
        setTimeout(connect, delay);
      };

      ws.onerror = (err) => {
        console.error('WS: Error', err);
        ws.close(); // Force onclose to trigger reconnect
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      isComponentMounted = false;
      if (wsRef.current) {
        // Prevent onclose from triggering reconnect during unmount
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [url, isDevMode]);

  // Command sending with strictly typed payload format
  const sendCommand = useCallback((command, params = {}, sessionId = null) => {
    if (isDevMode) {
      console.log('WS [DEV MODE SIMULATION] Sent:', { command, params, session_id: sessionId });
      return;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const payload = {
        command: command,
        params: params,
      };
      if (sessionId) {
        payload.session_id = sessionId;
      }
      const msg = JSON.stringify(payload);
      wsRef.current.send(msg);
      console.log('WS: Sent', msg);
    } else {
      console.warn('WS: Cannot send, not connected');
    }
  }, [isDevMode]);

  // Pub/Sub methods
  const subscribe = useCallback((eventType, callback) => {
    if (!listeners.current[eventType]) {
      listeners.current[eventType] = [];
    }
    listeners.current[eventType].push(callback);
    return () => unsubscribe(eventType, callback); // Return unsubscribe function
  }, []);

  const unsubscribe = useCallback((eventType, callback) => {
    if (listeners.current[eventType]) {
      listeners.current[eventType] = listeners.current[eventType].filter(cb => cb !== callback);
    }
  }, []);

  const subscribeAll = useCallback((callback) => {
    return subscribe('*', callback);
  }, [subscribe]);

  return (
    <WebSocketContext.Provider value={{ 
      isConnected, 
      sendCommand, 
      subscribe, 
      unsubscribe, 
      subscribeAll 
    }}>
      {children}
    </WebSocketContext.Provider>
  );
};
