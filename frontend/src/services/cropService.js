import { apiRequest } from './apiClient';

export const cropService = {
  async getCrops(category = null, search = null) {
    let query = '';
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (search) params.append('search', search);
    if (params.toString()) query = `?${params.toString()}`;
    const res = await apiRequest(`/crops${query}`);
    return res.data;
  },

  async getCropById(cropId) {
    const res = await apiRequest(`/crops/${cropId}`);
    return res.data;
  },

  async matchCropProfile(selection) {
    const res = await apiRequest('/crops/match', {
      method: 'POST',
      body: JSON.stringify(selection),
    });
    return res.data;
  },
};

export const storageBatchService = {
  async getBatches(status = null) {
    const query = status ? `?status=${status}` : '';
    const res = await apiRequest(`/batches${query}`);
    return res.data;
  },

  async getBatchById(batchId) {
    const res = await apiRequest(`/batches/${batchId}`);
    return res.data;
  },

  async createBatch(payload) {
    const res = await apiRequest('/batches', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  async updateBatch(batchId, payload) {
    const res = await apiRequest(`/batches/${batchId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  async closeBatch(batchId) {
    const res = await apiRequest(`/batches/${batchId}/close`, {
      method: 'POST',
    });
    return res.data;
  },
};
