import apiClient from './apiClient';

export const pinnAPI = {
  streamTraining(formula, conditions, equation_type, tMax, parameters = {}) {
    return apiClient.createSSEConnection('/api/math/solve/stream', {
      formula,
      conditions,
      equation_type,
      tMax,
      parameters
    });
  },

  async stopTraining(modelId) {
    return await apiClient.post('/api/math/stop', {
      model_id: modelId
    }, {
      timeout: 5000,
      retries: 1
    });
  },

  async evaluatePoint(modelId, t) {
    return await apiClient.post('/api/math/evaluate', {
      model_id: modelId,
      t: t
    }, {
      timeout: 5000,
      retries: 1
    });
  },

  async solveSymbolic(formula) {
    return await apiClient.post('/api/math/solve/symbolic', {
      formula
    }, {
      timeout: 30000,
      retries: 0
    });
  }
};

export default pinnAPI;
