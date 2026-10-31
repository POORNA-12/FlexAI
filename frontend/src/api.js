/**
 * API client module communicating with FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errMsg = `HTTP Error ${res.status}: ${res.statusText}`;
      try {
        const errorData = await res.json();
        if (errorData.detail) {
          errMsg = errorData.detail;
        }
      } catch (e) {
        // use default error message
      }
      throw new Error(errMsg);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Request Failed [${endpoint}]:`, err);
    throw err;
  }
}

async function downloadFile(endpoint, defaultFilename) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      let errMsg = `Export request failed (HTTP ${res.status})`;
      try {
        const errorData = await res.json();
        if (errorData.detail) errMsg = errorData.detail;
      } catch (e) {}
      throw new Error(errMsg);
    }

    let filename = defaultFilename;
    const disposition = res.headers.get('content-disposition');
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
    return { success: true, filename };
  } catch (err) {
    console.error(`Export Download Failed [${endpoint}]:`, err);
    throw err;
  }
}

export const api = {
  // Downloads & Exports
  downloadExport: (entityType, format = 'csv', params = {}) => {
    const queryParams = new URLSearchParams({ format, source: 'db', ...params }).toString();
    const defaultFilename = `${entityType}.${format}`;
    return downloadFile(`/export/${entityType}?${queryParams}`, defaultFilename);
  },
  // Dashboard
  getDashboardMetrics: () => request('/dashboard/metrics'),

  // Purchase Orders & Suppliers
  getPurchaseOrders: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/purchase-orders?${q}`);
  },
  getPurchaseOrderDetail: (id) => request(`/purchase-orders/${id}`),
  getSuppliers: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/suppliers?${q}`);
  },

  // Acknowledgements
  getAcknowledgements: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/acknowledgements?${q}`);
  },

  // Change Requests & Approvals
  getChangeRequests: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/change-requests?${q}`);
  },
  approveChangeRequest: (changeId, payload = {}) => {
    return request(`/change-requests/${changeId}/approve`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  rejectChangeRequest: (changeId, payload = {}) => {
    return request(`/change-requests/${changeId}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  // Inventory & Production
  getInventoryPlans: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/inventory-plans?${q}`);
  },
  getProductionOrders: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/production-orders?${q}`);
  },
  getScheduleImpacts: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/schedule-impacts?${q}`);
  },

  // Exceptions & Notifications
  getExceptions: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/exceptions?${q}`);
  },
  resolveException: (id) => {
    return request(`/exceptions/${id}/resolve`, { method: 'POST' });
  },
  getNotifications: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/notifications?${q}`);
  },

  // Data Quality & Admin
  getDataQualitySummary: () => request('/data-quality/summary'),
  getReproducibilityReport: () => request('/data-quality/reproducibility'),
  seedDataset: (scale = 'full', confirm = true) => {
    return request(`/data-generator/seed?scale=${scale}&confirm=${confirm}`, { method: 'POST' });
  }
};

