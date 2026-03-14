import { useState, useEffect, useRef, useCallback } from 'react';
import pinnAPI from '../services/pinnAPI';
import { APIError } from '../services/apiClient';

const useRealTimeTraining = (baseUrl = '') => {
  const [isTraining, setIsTraining] = useState(false);
  const [trainingData, setTrainingData] = useState(null);
  const [numericalData, setNumericalData] = useState(null);
  const [symbolicData, setSymbolicData] = useState(null);
  const [lossData, setLossData] = useState(null);
  const [progress, setProgress] = useState({ current: 0, total: 5000, completed: false });
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [trainingStats, setTrainingStats] = useState({
    startTime: null,
    elapsedTime: 0,
    epochsPerSecond: 0
  });
  const [error, setError] = useState(null);
  
  const sseConnectionRef = useRef(null);
  const statsIntervalRef = useRef(null);
  const lastEpochTimeRef = useRef(null);

  const cleanup = useCallback(() => {
    if (sseConnectionRef.current) {
      sseConnectionRef.current.abort();
      sseConnectionRef.current = null;
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

  const formatError = (error) => {
    if (error instanceof APIError) {
      if (error.isNetworkError()) {
        return 'Network error: Unable to connect to server. Please check if the backend is running.';
      }
      if (error.isValidationError()) {
        return `Validation error: ${error.message}`;
      }
      if (error.isTimeout()) {
        return 'Request timeout: The server took too long to respond.';
      }
      if (error.isServerError()) {
        return `Server error: ${error.message}`;
      }
      return error.message;
    }
    return error?.message || 'An unexpected error occurred';
  };

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

      sseConnectionRef.current = pinnAPI.streamTraining(
        payload.formula,
        payload.conditions,
        payload.tMax,
        payload.parameters
      );

      setConnectionStatus('connected');
      statsIntervalRef.current = setInterval(updateStats, 1000);

      try {
        for await (const data of sseConnectionRef.current.stream()) {
          console.log('SSE data received:', data);
          
          switch (data.type) {
            case 'initial_solutions':
              console.log('Received initial solutions:', data);
              if (data.numerical) {
                setNumericalData(data.numerical);
              }
              if (data.symbolic) {
                setSymbolicData(data.symbolic);
              }
              break;
              
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
              
              if (statsIntervalRef.current) {
                clearInterval(statsIntervalRef.current);
                statsIntervalRef.current = null;
              }
              return;
              
            case 'training_error':
            case 'validation_error':
            case 'server_error':
              console.error('Training error:', data.error);
              setError(data.error || 'Training failed');
              setIsTraining(false);
              setConnectionStatus('error');
              cleanup();
              return;
              
            default:
              console.log('Unknown update type:', data.type);
          }
        }
      } catch (streamError) {
        if (streamError.name === 'AbortError') {
          console.log('Training aborted by user');
          return;
        }
        throw streamError;
      }

    } catch (err) {
      console.error('Training error:', err);
      const errorMessage = formatError(err);
      setError(errorMessage);
      setIsTraining(false);
      setConnectionStatus('error');
      cleanup();
    }
  }, [cleanup, updateStats, formatError]);

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
    setNumericalData(null);
    setSymbolicData(null);
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

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    isTraining,
    trainingData,
    numericalData,
    symbolicData,
    lossData,
    progress,
    connectionStatus,
    trainingStats,
    error,
    startTraining,
    stopTraining,
    reset,
    formatError
  };
};

export default useRealTimeTraining;
