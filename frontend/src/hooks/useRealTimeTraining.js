import { useState, useEffect, useRef, useCallback } from 'react';
import pinnAPI from '../services/pinnAPI';
import { APIError } from '../services/apiClient';

const DEFAULT_PROGRESS = { current: 0, total: 5000, completed: false };
const DEFAULT_TRAINING_STATS = {
  startTime: null,
  elapsedTime: 0,
  epochsPerSecond: 0
};

const useRealTimeTraining = () => {
  const [isTraining, setIsTraining] = useState(false);
  const [trainingData, setTrainingData] = useState(null);
  const [numericalData, setNumericalData] = useState(null);
  const [symbolicData, setSymbolicData] = useState(null);
  const [validationData, setValidationData] = useState(null);
  const [modelId, setModelId] = useState(null);
  const [lossData, setLossData] = useState(null);
  const [progress, setProgress] = useState(DEFAULT_PROGRESS);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [trainingStats, setTrainingStats] = useState(DEFAULT_TRAINING_STATS);
  const [error, setError] = useState(null);

  const sseConnectionRef = useRef(null);
  const statsIntervalRef = useRef(null);
  const lastEpochTimeRef = useRef(null);
  const stopRequestedRef = useRef(false);

  const cleanup = useCallback(() => {
    if (sseConnectionRef.current) {
      sseConnectionRef.current.abort();
      sseConnectionRef.current = null;
    }
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current);
      statsIntervalRef.current = null;
    }
  }, []);

  const resetTrainingSession = useCallback(() => {
    setProgress(DEFAULT_PROGRESS);
    setTrainingData(null);
    setModelId(null);
    setValidationData(null);
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
    setValidationData(null);
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

  const handleEpochUpdate = useCallback((data) => {
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
      total: DEFAULT_PROGRESS.total
    }));

    if (data.function_data) {
      setTrainingData({
        function_data: data.function_data.function_data || data.function_data,
        metadata: data.function_data.metadata
      });
    }

    if (data.loss) {
      setLossData(data.loss);
    }
  }, []);

  const startTraining = useCallback(async (payload) => {
    try {
      setError(null);
      stopRequestedRef.current = false;
      setIsTraining(true);
      resetTrainingSession();
      setConnectionStatus('connecting');

      console.log('Starting training with payload:', payload);

      sseConnectionRef.current = pinnAPI.streamTraining(
          payload.formula,
          payload.conditions,
          payload.equation_type,
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

            case 'epoch_update': {
              handleEpochUpdate(data);
              break;
            }

            case 'model_ready':
              setModelId(data.model_id || null);
              break;

            case 'training_complete':
              console.log('Training completed:', data);
              setProgress(prev => ({ ...prev, completed: true }));
              setIsTraining(false);
              setConnectionStatus('disconnected');
              setModelId(data.model_id || null);

              if (data.final_data) {
                setTrainingData({
                  function_data: data.final_data.function_data,
                  metadata: data.final_data.metadata
                });
              }

              if (data.validation) {
                setValidationData(data.validation);
              }

              stopRequestedRef.current = false;

              cleanup();
              return;

            case 'training_error':
            case 'validation_error':
            case 'server_error':
              console.error('Training error:', data.error);
              setError(data.error || 'Training failed');
              setIsTraining(false);
              setConnectionStatus('error');
              setModelId(null);
              cleanup();
              return;

            default:
              console.log('Unknown update type:', data.type);
          }
        }
      } catch (streamError) {
        if (streamError.name === 'AbortError') {
          console.log('Training aborted by user');
          if (!stopRequestedRef.current) {
            setConnectionStatus('disconnected');
          }
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
  }, [cleanup, resetTrainingSession, updateStats, handleEpochUpdate]);

  const stopTraining = useCallback(async () => {
    if (!modelId) {
      cleanup();
      setIsTraining(false);
      setConnectionStatus('disconnected');
      return;
    }

    try {
      stopRequestedRef.current = true;
      setConnectionStatus('disconnecting');
      await pinnAPI.stopTraining(modelId);
    } catch (err) {
      console.error('Failed to request graceful stop:', err);
      cleanup();
      setIsTraining(false);
      setConnectionStatus('disconnected');
      stopRequestedRef.current = false;
    }
  }, [cleanup, modelId]);

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
    validationData,
    modelId,
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