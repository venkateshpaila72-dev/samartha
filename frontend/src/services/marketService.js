import { apiRequest } from './apiClient';

function buildQuery({ crop, state, district, limit = 50, skip = 0 } = {}) {
  const params = new URLSearchParams();
  if (crop) params.set('crop', crop);
  if (state) params.set('state', state);
  if (district) params.set('district', district);
  params.set('limit', String(limit));
  params.set('skip', String(skip));
  return params.toString();
}

export const marketService = {
  async getMarketPrices(crop, location = {}, pagination = {}) {
    if (!crop || !String(crop).trim()) {
      throw new Error('Select a crop before searching for market prices.');
    }
    const query = buildQuery({
      crop: String(crop).trim(),
      state: location.state,
      district: location.district,
      ...pagination,
    });
    const response = await apiRequest(`/market/prices?${query}`);
    return response.data;
  },

  async getBatchMarketPrices(batchId, location = {}, pagination = {}) {
    if (!batchId) throw new Error('Select a batch to view its market prices.');
    const query = buildQuery({
      state: location.state,
      district: location.district,
      ...pagination,
    });
    const response = await apiRequest(`/batches/${encodeURIComponent(batchId)}/market?${query}`);
    return response.data;
  },
};
