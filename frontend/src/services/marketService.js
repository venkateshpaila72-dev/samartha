import { apiRequest } from './apiClient';

export const marketService = {
  async getMarketPrices(crop = 'Wheat') {
    const res = await apiRequest(`/market/prices?crop=${encodeURIComponent(crop)}`);
    return res.data;
  },

  async getBatchMarketPrices(batchId) {
    const res = await apiRequest(`/batches/${batchId}/market`);
    return res.data;
  },
};
