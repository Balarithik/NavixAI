/**
 * NavixAI API Client
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = { error: `Server error: ${response.statusText} (${response.status})` };
    }
    const err = new Error(errorData.error || errorData.message || 'API request failed');
    err.status = response.status;
    err.data = errorData;
    throw err;
  }

  return response.json();
}

export const api = {
  // Buildings & Floors
  getBuildings: () => request('/api/building/'),
  getFloors: () => request('/api/floors/'),

  // Nodes
  getNodes: (params = {}) => {
    const query = new URLSearchParams();
    if (params.floor) query.append('floor', params.floor);
    if (params.type) query.append('type', params.type);
    if (params.q) query.append('q', params.q);
    const qs = query.toString();
    return request(`/api/nodes/${qs ? `?${qs}` : ''}`);
  },

  getNodeDetail: (nodeId) => request(`/api/nodes/${encodeURIComponent(nodeId)}/`),

  // QR Scanning
  scanQRCode: (payload) =>
    request('/api/scan/', {
      method: 'POST',
      body: JSON.stringify({ payload }),
    }),

  // Routing
  getRoute: (fromNodeId, toNodeId, mode = 'any') => {
    const query = new URLSearchParams({
      from: fromNodeId,
      to: toNodeId,
      mode,
    });
    return request(`/api/routes/?${query.toString()}`);
  },

  // QR image URL helper
  getQRCodeImageUrl: (nodeId) => `${BASE_URL}/api/qr/${encodeURIComponent(nodeId)}/`,
};
