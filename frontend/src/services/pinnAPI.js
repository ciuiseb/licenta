import apiClient from './apiClient';

export const pinnAPI = {
  async solveCauchy(formula, conditions, equationType, tMax, parameters = {}) {
    return await apiClient.post('/api/math/solve', {
      formula,
      conditions,
      equation_type: equationType,
      tMax,
      parameters
    }, {
      timeout: 120000,
      retries: 2
    });
  },

  streamTraining(formula, conditions, equation_type, tMax, parameters = {}) {
    return apiClient.createSSEConnection('/api/math/solve/stream', {
      formula,
      conditions,
      equation_type,
      tMax,
      parameters
    });
  },

  async exportData(format, xData, yData, metadata = {}) {
    return await apiClient.post(`/api/math/export/${format}`, {
      x: xData,
      y: yData,
      meta: metadata
    }, {
      timeout: 30000,
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
  }
};

export default pinnAPI;
