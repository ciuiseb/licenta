import { useState, useEffect, useRef, useCallback } from 'react';

const useRealTimeTraining = (baseUrl = 'http://127.0.0.1:5000') => {
  const [isTraining, setIsTraining] = useState(false);
  const [trainingData, setTrainingData] = useState(null);
  const [lossData, setLossData] = useState(null);
  const [progress, setProgress] = useState({ current: 0, total: 5000, completed: false });
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // disconnected, connecting, connected, error
  const [trainingStats, setTrainingStats] = useState({
    startTime: null,
    elapsedTime: 0,
    epochsPerSecond: 0
  });
  const [error, setError] = useState(null);
  
  const eventSourceRef = useRef(null);
  const abortControllerRef = useRef(null);
  const statsIntervalRef = useRef(null);
  const lastEpochTimeRef = useRef(null);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
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

  const startTraining = useCallback(async (payload) => {
    try {
      setError(null);
      setIsTraining(true);
      setProgress({ current: 0, total: 5000, completed: false });
      setTrainingData(null);
      setLossData(null);
      setConnectionStatus('connecting');
      setTrainingStats({
        startTime: Date.now(),
        elapsedTime: 0,
        epochsPerSecond: 0
      });

      console.log('Starting training with payload:', payload);

      // Create AbortController for this training session
      abortControllerRef.current = new AbortController();

      // Send training data via POST first to start the process
      const response = await fetch(`${baseUrl}/api/math/solve/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: abortControllerRef.current.signal
      });

      console.log('POST response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // The response might be SSE format, not JSON
      const responseText = await response.text();
      console.log('POST response text:', responseText.substring(0, 200));

      // If it's SSE format, we don't need to parse it as JSON
      // Just proceed to create EventSource connection
      if (responseText.startsWith('data:')) {
        console.log('Backend returned SSE format, proceeding with EventSource');
      } else {
        try {
          const result = JSON.parse(responseText);
          console.log('POST response data:', result);
        } catch (e) {
          console.log('Response is not JSON, treating as SSE stream');
        }
      }

      // Now start SSE connection to listen for updates
      // Note: SSE uses GET, not POST, and we need to add the payload as query params
      const params = new URLSearchParams({
        formula: payload.formula,
        conditions: JSON.stringify(payload.conditions),
        tMax: payload.tMax.toString()
      });

      const streamUrl = `${baseUrl}/api/math/solve/stream?${params}`;
      console.log('Connecting to SSE stream:', streamUrl);

      eventSourceRef.current = new EventSource(streamUrl);

      eventSourceRef.current.onopen = () => {
        console.log('SSE connection opened');
        setConnectionStatus('connected');
      };

      eventSourceRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('SSE data received:', data);
          
          switch (data.type) {
            case 'epoch_update':
              const epochTime = Date.now();
              if (lastEpochTimeRef.current) {
                const timeDiff = (epochTime - lastEpochTimeRef.current) / 1000;
                const epochsPerSecond = 1 / timeDiff;
                setTrainingStats(prev => ({
                  ...prev,
                  epochsPerSecond: epochsPerSecond
                }));
              }
              lastEpochTimeRef.current = epochTime;

              setProgress(prev => ({
                ...prev,
                current: data.epoch || 0,
                total: 5000
              }));
              
              if (data.function_data && data.function_data.function_data) {
                setTrainingData({
                  function_data: data.function_data.function_data,
                  metadata: data.function_data.metadata
                });
              }
              
              if (data.loss) {
                setLossData(data.loss);
              }
              break;
              
            case 'training_complete':
              console.log('Training completed:', data);
              setProgress(prev => ({ ...prev, completed: true }));
              setIsTraining(false);
              setConnectionStatus('disconnected');
              
              if (data.final_data) {
                setTrainingData({
                  function_data: data.final_data.function_data,
                  metadata: data.final_data.metadata
                });
              }
              
              // Stop stats updates
              if (statsIntervalRef.current) {
                clearInterval(statsIntervalRef.current);
                statsIntervalRef.current = null;
              }
              break;
              
            case 'training_error':
              console.error('Training error:', data.error);
              setError(data.error || 'Training failed');
              setIsTraining(false);
              setConnectionStatus('error');
              cleanup();
              break;
              
            default:
              console.log('Unknown update type:', data.type);
          }
        } catch (err) {
          console.error('Error parsing SSE message:', err, event.data);
        }
      };

      eventSourceRef.current.onerror = (err) => {
        console.error('SSE connection error:', err);
        setConnectionStatus('error');
        setError('Connection to training server lost. Check if backend is running.');
        setIsTraining(false);
        cleanup();
      };

      // Start stats updates
      statsIntervalRef.current = setInterval(updateStats, 1000);

    } catch (err) {
      console.error('Training start error:', err);
      if (err.name !== 'AbortError') {
        setError(err.message);
        setIsTraining(false);
        setConnectionStatus('error');
        cleanup();
      }
    }
  }, [baseUrl, cleanup, updateStats]);

  const stopTraining = useCallback(() => {
    cleanup();
    setIsTraining(false);
    setProgress(prev => ({ ...prev, completed: false }));
    setConnectionStatus('disconnected');
  }, [cleanup]);

  const reset = useCallback(() => {
    cleanup();
    setIsTraining(false);
    setTrainingData(null);
    setLossData(null);
    setProgress({ current: 0, total: 5000, completed: false });
    setTrainingStats({
      startTime: null,
      elapsedTime: 0,
      epochsPerSecond: 0
    });
    setError(null);
    setConnectionStatus('disconnected');
  }, [cleanup]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    isTraining,
    trainingData,
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

export default useRealTimeTraining;
