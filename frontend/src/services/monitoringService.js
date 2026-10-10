import { apiRequest } from './apiClient';

export const monitoringService = {
  async getMonitoringSummary(batchId) {
    const res = await apiRequest(`/batches/${batchId}/monitoring`);
    return res.data;
  },

  async getReadings(batchId, limit = 50) {
    const res = await apiRequest(`/batches/${batchId}/readings?limit=${limit}`);
    return res.data;
  },

  async ingestReading(batchId, readingData) {
    const res = await apiRequest(`/batches/${batchId}/readings`, {
      method: 'POST',
      body: JSON.stringify(readingData),
    });
    return res.data;
  },

  async getAlerts(batchId = null, status = null) {
    const params = new URLSearchParams();
    if (batchId) params.append('batch_id', batchId);
    if (status) params.append('status', status);
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await apiRequest(`/alerts${query}`);
    return res.data;
  },

  async updateAlertStatus(alertId, newStatus) {
    const res = await apiRequest(`/alerts/${alertId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    });
    return res.data;
  },

  async dispatchWhatsAppAlert(alertId) {
    const res = await apiRequest(`/alerts/${alertId}/dispatch-whatsapp`, {
      method: 'POST',
    });
    return {
      success: res?.success ?? res?.data?.dispatched ?? false,
      message: res?.message || (res?.data?.dispatched ? 'WhatsApp notification dispatched via Twilio.' : 'WhatsApp notification failed.'),
      data: res?.data || res,
      status: res?.data?.status || res?.status,
      ...res,
    };
  },
};

export const diaryService = {
  async getBatchEntries(batchId) {
    const res = await apiRequest(`/batches/${batchId}/diary`);
    return res.data;
  },

  async createEntry(batchId, entryData) {
    const res = await apiRequest(`/batches/${batchId}/diary`, {
      method: 'POST',
      body: JSON.stringify(entryData),
    });
    return res.data;
  },

  async deleteEntry(entryId) {
    const res = await apiRequest(`/diary/${entryId}`, {
      method: 'DELETE',
    });
    return res.data;
  },
};

export const chatbotService = {
  async getConversations() {
    const res = await apiRequest('/chat/conversations');
    return res.data;
  },

  async createConversation(payload) {
    const res = await apiRequest('/chat/conversations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  async getMessages(conversationId) {
    const res = await apiRequest(`/chat/conversations/${conversationId}/messages`);
    return res.data;
  },

  async sendMessage(conversationId, payload) {
    const res = await apiRequest(`/chat/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data;
  },
};

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

export const adminService = {
  async getDashboard() {
    const res = await apiRequest('/admin/dashboard');
    return res.data;
  },

  async getUsers() {
    const res = await apiRequest('/admin/users');
    return res.data;
  },

  async verifyCrop(cropId) {
    const res = await apiRequest(`/admin/crops/${cropId}/verify`, {
      method: 'POST',
    });
    return res.data;
  },
};
