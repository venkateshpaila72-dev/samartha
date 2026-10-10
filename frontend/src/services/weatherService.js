import { apiRequest } from './apiClient';

export const weatherService = {
  async getWeather(location = null) {
    const query = location ? `?location=${encodeURIComponent(location)}` : '';
    const res = await apiRequest(`/weather${query}`);
    return res.data;
  },

  async getBatchWeather(batchId) {
    const res = await apiRequest(`/batches/${batchId}/weather`);
    return res.data;
  },
};
