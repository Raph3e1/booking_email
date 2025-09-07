const API_BASE_URL = '/api';

export const settingsApi = {
  // Get all email configurations
  getAllConfigs: async () => {
    const response = await fetch(`${API_BASE_URL}/settings/email-configs`);
    if (!response.ok) {
      throw new Error('Failed to fetch email configurations');
    }
    return response.json();
  },

  // Get a specific email configuration
  getConfig: async (id) => {
    const response = await fetch(`${API_BASE_URL}/settings/email-configs/${id}`);
    if (!response.ok) {
      throw new Error('Failed to fetch email configuration');
    }
    return response.json();
  },

  // Create a new email configuration
  createConfig: async (config) => {
    const response = await fetch(`${API_BASE_URL}/settings/email-configs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      throw new Error('Failed to create email configuration');
    }
    return response.json();
  },

  // Update an existing email configuration
  updateConfig: async (id, config) => {
    const response = await fetch(`${API_BASE_URL}/settings/email-configs/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      throw new Error('Failed to update email configuration');
    }
    return response.json();
  },

  // Delete an email configuration
  deleteConfig: async (id) => {
    const response = await fetch(`${API_BASE_URL}/settings/email-configs/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete email configuration');
    }
    return response.json();
  },

  // Get status of all email configurations
  getJobStatuses: async () => {
    const response = await fetch(`${API_BASE_URL}/settings/email-configss/status`);
    if (!response.ok) {
      throw new Error('Failed to fetch email configurations status');
    }
    return response.json();
  },

  // Start fetching emails for a configuration
  startEmailFetch: async (configId) => {
    const response = await fetch(`${API_BASE_URL}/settings/email-configs/${configId}/start`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to start email fetching');
    }
    return response.json();
  },

  // Stop fetching emails for a configuration
  stopEmailFetch: async (configId) => {
    const response = await fetch(`${API_BASE_URL}/settings/email-configs/${configId}/stop`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to stop email fetching');
    }
    return response.json();
  },

  // Run email fetching manually
  runEmailFetch: async (configId) => {
    const response = await fetch(`${API_BASE_URL}/settings/email-configs/${configId}/run`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to run email fetching');
    }
    return response.json();
  },

  // Get global settings
  getGlobalSettings: async () => {
    const response = await fetch(`${API_BASE_URL}/settings/global-settings`);
    if (!response.ok) {
      throw new Error('Failed to fetch global settings');
    }
    return response.json();
  },

  // Update global settings
  updateGlobalSettings: async (settings) => {
    const response = await fetch(`${API_BASE_URL}/settings/global-settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings),
    });
    if (!response.ok) {
      throw new Error('Failed to update global settings');
    }
    return response.json();
  },
};

export const emailApi = {
  getAll: async () => {
    const response = await fetch(`${API_BASE_URL}/emails`);
    if (!response.ok) throw new Error('Failed to fetch emails');
    return response.json();
  },

  add: async (email) => {
    const response = await fetch(`${API_BASE_URL}/emails`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });
    if (!response.ok) throw new Error('Failed to add email');
    return response.json();
  },

  update: async (id, email) => {
    const response = await fetch(`${API_BASE_URL}/emails/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });
    if (!response.ok) throw new Error('Failed to update email');
    return response.json();
  },

  delete: async (id) => {
    const response = await fetch(`${API_BASE_URL}/emails/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete email');
    return response.json();
  },
}; 