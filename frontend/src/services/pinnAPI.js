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

  async evaluatePoint(modelId, t) {
    return await apiClient.post('/api/math/evaluate', {
      model_id: modelId,
      t: t
    }, {
      timeout: 5000,
      retries: 1
    });
  }
};

export default pinnAPI;
