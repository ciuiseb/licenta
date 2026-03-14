import apiClient from './apiClient';

export const pinnAPI = {
  async solveCauchy(formula, conditions, tMax, parameters = {}) {
    return await apiClient.post('/api/math/solve', {
      formula,
      conditions,
      tMax,
      parameters
    }, {
      timeout: 120000,
      retries: 2
    });
  },

  streamTraining(formula, conditions, tMax, parameters = {}) {
    return apiClient.createSSEConnection('/api/math/solve/stream', {
      formula,
      conditions,
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

  async evaluatePoint(t) {
    return await apiClient.post('/api/math/evaluate', {
      t: t
    }, {
      timeout: 5000,
      retries: 1
    });
  }
};

export default pinnAPI;
