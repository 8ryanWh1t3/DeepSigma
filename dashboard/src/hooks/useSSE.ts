import { useEffect, useRef, useCallback } from 'react';
import { useOverwatchStore } from '../store';
import {
  fetchRealEpisodes,
  fetchRealDrifts,
  fetchRealAgents,
  generateMockEpisodes,
  generateMockDrifts,
  generateAgentMetrics,
} from '../mockData';

const SSE_URL = '/api/sse';
const API_BASE = 'http://localhost:8000';

/**
 * Custom hook that establishes an SSE connection for real-time dashboard updates.
 * Falls back to HTTP polling (5s) if SSE is unavailable, then to mock data.
 */
export function useSSE(autoRefresh: boolean) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const setEpisodes = useOverwatchStore((s) => s.setEpisodes);
  const setDrifts = useOverwatchStore((s) => s.setDrifts);
  const setAgents = useOverwatchStore((s) => s.setAgents);
  const setMGGraph = useOverwatchStore((s) => s.setMGGraph);
  const setConnection = useOverwatchStore((s) => s.setConnection);

  const pollData = useCallback(async () => {
    const [realEps, realDrifts, realAgents] = await Promise.all([
      fetchRealEpisodes(),
      fetchRealDrifts(),
      fetchRealAgents(),
    ]);
    if (realEps && realEps.length > 0) {
      setEpisodes(realEps);
      setDrifts(realDrifts ?? generateMockDrifts(20));
      setAgents(realAgents ?? generateAgentMetrics());
      setConnection({ dataSource: 'api', lastEvent: new Date().toLocaleTimeString() });
    } else {
      setEpisodes(generateMockEpisodes(100));
      setDrifts(generateMockDrifts(100));
      setAgents(generateAgentMetrics());
      setConnection({ dataSource: 'mock', lastEvent: new Date().toLocaleTimeString() });
    }
  }, [setEpisodes, setDrifts, setAgents, setConnection]);

  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return;
    setConnection({ status: 'polling' });
    pollData();
    pollIntervalRef.current = setInterval(pollData, 5000);
  }, [pollData, setConnection]);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const connectSSE = useCallback(() => {
    // Try SSE first
    try {
      const es = new EventSource(`${API_BASE}${SSE_URL}`);
      eventSourceRef.current = es;

      es.onopen = () => {
        setConnection({ status: 'connected', dataSource: 'sse' });
        stopPolling();
      };

      es.addEventListener('episodes', (e) => {
        try {
          setEpisodes(JSON.parse(e.data));
          setConnection({ lastEvent: new Date().toLocaleTimeString() });
        } catch { /* ignore parse errors */ }
      });

      es.addEventListener('drifts', (e) => {
        try { setDrifts(JSON.parse(e.data)); } catch { /* */ }
      });

      es.addEventListener('agents', (e) => {
        try { setAgents(JSON.parse(e.data)); } catch { /* */ }
      });

      es.addEventListener('mg', (e) => {
        try {
          const data = JSON.parse(e.data);
          setMGGraph(data.nodes || [], data.edges || []);
        } catch { /* */ }
      });

      es.onerror = () => {
        setConnection({ status: 'reconnecting' });
        es.close();
        eventSourceRef.current = null;
        // Fall back to polling
        startPolling();
      };
    } catch {
      // SSE not supported or connection failed — fall back to polling
      startPolling();
    }
  }, [setConnection, setEpisodes, setDrifts, setAgents, setMGGraph, stopPolling, startPolling]);

  useEffect(() => {
    if (!autoRefresh) {
      // Not auto-refreshing — do a single load then stop
      pollData();
      return;
    }

    connectSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      stopPolling();
    };
  }, [autoRefresh, connectSSE, pollData, stopPolling]);

  return { refresh: pollData };
}
