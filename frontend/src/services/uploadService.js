/**
 * Cloudinary & Asset Upload Service for FarmShield
 */

import { apiRequest } from './apiClient';

/**
 * Upload an image file to Cloudinary via FarmShield backend.
 * @param {File} file - Browser File object.
 * @param {string} folder - Target Cloudinary folder.
 * @returns {Promise<{url: string, secure_url: string, public_id: string, provider: string}>}
 */
export async function uploadImage(file, folder = 'farmshield/crops') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('folder', folder);

  const res = await apiRequest('/uploads', {
    method: 'POST',
    body: formData,
  });
  return res.data;
}

/**
 * Retrieves the current storage provider diagnostics (Cloudinary status).
 */
export async function getStorageStatus() {
  const res = await apiRequest('/uploads/status');
  return res.data;
}
