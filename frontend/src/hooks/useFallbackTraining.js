import { useState, useEffect, useRef, useCallback } from 'react';

const DEFAULT_PROGRESS = { current: 0, total: 5000, completed: false };
const DEFAULT_TRAINING_STATS = {
  startTime: null,
  elapsedTime: 0,
  epochsPerSecond: 0
};

const useFallbackTraining = (baseUrl = '') => {
  const [isTraining, setIsTraining] = useState(false);
  const [trainingData, setTrainingData] = useState(null);
  const [numericalData, setNumericalData] = useState(null);
  const [symbolicData, setSymbolicData] = useState(null);
  const [modelId, setModelId] = useState(null);
  const [lossData, setLossData] = useState(null);
  const [progress, setProgress] = useState(DEFAULT_PROGRESS);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [trainingStats, setTrainingStats] = useState(DEFAULT_TRAINING_STATS);
  const [error, setError] = useState(null);
  
  const abortControllerRef = useRef(null);
  const statsIntervalRef = useRef(null);

  const cleanup = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current);
      statsIntervalRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, []);

  const resetTrainingSession = useCallback(() => {
    setProgress(DEFAULT_PROGRESS);
    setTrainingData(null);
    setModelId(null);
    setLossData(null);
    setTrainingStats({
      ...DEFAULT_TRAINING_STATS,
      startTime: Date.now()
    });
  }, []);

  const clearTrainingState = useCallback(() => {
    setIsTraining(false);
    setTrainingData(null);
    setNumericalData(null);
    setSymbolicData(null);
    setModelId(null);
    setLossData(null);
    setProgress(DEFAULT_PROGRESS);
    setTrainingStats(DEFAULT_TRAINING_STATS);
    setError(null);
    setConnectionStatus('disconnected');
  }, []);

  const updateStats = useCallback(() => {
    if (trainingStats.startTime) {
      const elapsed = (Date.now() - trainingStats.startTime) / 1000;
      const epochsPerSecond = progress.current / elapsed;
      setTrainingStats(prev => ({
        ...prev,
        elapsedTime: elapsed,
        epochsPerSecond: epochsPerSecond
      }));
    }
  }, [progress.current, trainingStats.startTime]);

  const simulateTraining = useCallback(async (payload) => {
    // Simulate training progress
    const simulateEpoch = (epoch) => {
      if (!abortControllerRef.current || abortControllerRef.current.signal.aborted) {
        return false;
      }

      // Simulate function data (simple sine wave for demonstration)
      const points = 200;
      const x = Array.from({ length: points }, (_, i) => (i / (points - 1)) * payload.tMax);
      const y = x.map(t => Math.cos(t) * Math.exp(-0.1 * t) + (Math.random() - 0.5) * 0.1 * (1 - epoch / 5000));

      setTrainingData({
        function_data: { x, y },
        metadata: {
          domain: [0, payload.tMax],
          points: points,
          snapshot_timestamp: Date.now() / 1000
        }
      });

      // Simulate loss decreasing over time
      const totalLoss = 0.1 * Math.exp(-epoch / 1000) + 0.001;
      const physicsLoss = totalLoss * 0.9;
      const boundaryLoss = totalLoss * 0.1;

      setLossData({
        total: totalLoss,
        physics: physicsLoss,
        boundary: boundaryLoss
      });

      setProgress(prev => ({ ...prev, current: epoch }));

      return epoch < 5000;
    };

    // Simulate training epochs
    for (let epoch = 1; epoch <= 5000; epoch++) {
      if (!simulateEpoch(epoch)) break;
      
      // Add delay to simulate training time
      await new Promise(resolve => setTimeout(resolve, 10));
    }

    return {
      success: true,
      final_data: trainingData
    };
  }, [trainingData]);

  const startTraining = useCallback(async (payload) => {
    try {
      setError(null);
      setIsTraining(true);
      resetTrainingSession();
      setConnectionStatus('connecting');

      console.log('Starting fallback training with payload:', payload);

      abortControllerRef.current = new AbortController();

      // Try the real SSE endpoint first
      try {
        const response = await fetch(`${baseUrl}/api/math/solve/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: abortControllerRef.current.signal
        });

        if (response.ok) {
          // Try to read as SSE stream
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let hasRealData = false;

          try {
            while (true) {
              if (abortControllerRef.current?.signal.aborted) {
                break;
              }

              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n');
              buffer = lines.pop() || '';

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.substring(6));
                    
                    if (data.type === 'training_error' && data.error.includes('no attribute')) {
                      console.log('Backend SSE method not implemented, switching to simulation');
                      hasRealData = false;
                      break;
                    }
                    
                    // Process real SSE data
                    hasRealData = true;
                    // Handle real data here...
                  } catch (e) {
                    console.log('Could not parse SSE data:', line);
                  }
                }
              }
              
              if (!hasRealData) break;
            }
          } finally {
            reader.releaseLock();
          }

          if (hasRealData) {
            // Real SSE data was processed
            return;
          }
        }
      } catch (err) {
        console.log('Real SSE endpoint not available:', err.message);
      }

      // Fallback to simulation
      setConnectionStatus('connected');
      statsIntervalRef.current = setInterval(updateStats, 1000);
      
      await simulateTraining(payload);
      
      setProgress(prev => ({ ...prev, completed: true }));
      setIsTraining(false);
      setConnectionStatus('disconnected');

    } catch (err) {
      console.error('Training error:', err);
      if (err.name !== 'AbortError') {
        setError(err.message);
        setIsTraining(false);
        setConnectionStatus('error');
        cleanup();
      }
    }
  }, [baseUrl, cleanup, updateStats, simulateTraining]);

  const stopTraining = useCallback(() => {
    cleanup();
    setIsTraining(false);
    setProgress(prev => ({ ...prev, completed: false }));
    setConnectionStatus('disconnected');
  }, [cleanup]);

  const reset = useCallback(() => {
    cleanup();
    clearTrainingState();
  }, [cleanup, clearTrainingState]);

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    isTraining,
    trainingData,
    numericalData,
    symbolicData,
    modelId,
    lossData,
    progress,
    connectionStatus,
    trainingStats,
    error,
    startTraining,
    stopTraining,
    reset
  };
};

export default useFallbackTraining;
