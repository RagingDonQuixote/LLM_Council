/**
 * API client for the LLM Council backend.
 */

const API_BASE = 'http://localhost:8001';

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Test model latency.
   */
  async testLatency(modelId) {
    const response = await fetch(
      `${API_BASE}/api/test-latency/${encodeURIComponent(modelId)}`
    );
    if (!response.ok) {
      throw new Error('Failed to test latency');
    }
    return response.json();
  },

  /**
   * Get current configuration.
   */
  async getConfig() {
    const response = await fetch(`${API_BASE}/api/config`);
    if (!response.ok) {
      throw new Error('Failed to get configuration');
    }
    return response.json();
  },

  /**
   * Update configuration.
   */
  async updateConfig(config) {
    const response = await fetch(`${API_BASE}/api/config`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      throw new Error('Failed to update configuration');
    }
    return response.json();
  },

  /**
   * Get model metadata for specific models.
   */
  async getModelsMetadata(modelIds) {
    // We already fetch all models in getAvailableModels.
    // To simplify, we'll use that instead of a dedicated metadata endpoint.
    const response = await fetch(`${API_BASE}/api/available-models`);
    if (!response.ok) {
      throw new Error('Failed to get model metadata');
    }
    const data = await response.json();
    const metadataMap = {};
    data.models.forEach(m => {
      if (modelIds.includes(m.id)) {
        metadataMap[m.id] = m;
      }
    });
    return metadataMap;
  },

  /**
   * List all task templates.
   */
  async listTemplates() {
    const response = await fetch(`${API_BASE}/api/templates`);
    if (!response.ok) {
      throw new Error('Failed to list templates');
    }
    return response.json();
  },

  /**
   * Save a template.
   */
  async saveTemplate(template) {
    const response = await fetch(`${API_BASE}/api/templates`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(template),
    });
    if (!response.ok) {
      throw new Error('Failed to save template');
    }
    return response.json();
  },

  /**
   * List all AI boards.
   */
  async listBoards() {
    const response = await fetch(`${API_BASE}/api/boards`);
    if (!response.ok) {
      throw new Error('Failed to list boards');
    }
    return response.json();
  },

  /**
   * Save an AI board.
   */
  async saveBoard(board) {
    const response = await fetch(`${API_BASE}/api/boards`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(board),
    });
    if (!response.ok) {
      throw new Error('Failed to save board');
    }
    return response.json();
  },

  /**
   * Delete an AI board.
   */
  async deleteBoard(boardId) {
    const response = await fetch(`${API_BASE}/api/boards/${boardId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete board');
    }
    return response.json();
  },

  /**
   * List all prompts.
   */
  async listPrompts() {
    const response = await fetch(`${API_BASE}/api/prompts`);
    if (!response.ok) {
      throw new Error('Failed to list prompts');
    }
    return response.json();
  },

  /**
   * Save a prompt.
   */
  async savePrompt(prompt) {
    const response = await fetch(`${API_BASE}/api/prompts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(prompt),
    });
    if (!response.ok) {
      throw new Error('Failed to save prompt');
    }
    return response.json();
  },

  /**
   * Delete a prompt.
   */
  async deletePrompt(promptId) {
    const response = await fetch(`${API_BASE}/api/prompts/${promptId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete prompt');
    }
    return response.json();
  },

  /**
   * Track prompt usage.
   */
  async trackPromptUsage(promptId) {
    const response = await fetch(`${API_BASE}/api/prompts/${promptId}/use`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to track prompt usage');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content, onEvent) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6));
            onEvent(data);
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }
    }
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },

  /**
   * Get current council configuration.
   */
  async getVersion() {
    const response = await fetch(`${API_BASE}/api/version`);
    if (!response.ok) throw new Error('Failed to fetch version');
    return response.json();
  },



  /**
   * Archive a conversation.
   */
  async archiveConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/archive`,
      { method: 'POST' }
    );
    if (!response.ok) {
      throw new Error('Failed to archive conversation');
    }
    return response.json();
  },

  /**
   * Delete a conversation permanently.
   */
  async deleteConversationPermanent(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/permanent`,
      { method: 'DELETE' }
    );
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
    return response.json();
  },

  /**
   * Get fail lists.
   */
  async getFailLists() {
    const response = await fetch(`${API_BASE}/api/fail-lists`);
    if (!response.ok) {
      throw new Error('Failed to get fail lists');
    }
    return response.json();
  },

  /**
   * Activate a fail list.
   */
  async activateFailList(id) {
    const response = await fetch(`${API_BASE}/api/fail-lists/${id}/activate`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to activate fail list');
    }
    return response.json();
  },

  /**
   * Test models availability.
   */
  async testModelsAvailability(modelIds) {
    const response = await fetch(`${API_BASE}/api/models/test-availability`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(modelIds),
    });
    if (!response.ok) {
      throw new Error('Failed to test models availability');
    }
    return response.json();
  },

  /**
   * Get all available models (filtered by active fail list).
   */
  async getAvailableModels() {
    const response = await fetch(`${API_BASE}/api/available-models`);
    if (!response.ok) {
      throw new Error('Failed to get available models');
    }
    return response.json();
  },

  /**
   * Submit human chairman feedback and receive streaming updates.
   */
  async submitHumanFeedbackStream(conversationId, feedback, onEvent) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/human-feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ feedback, continue_discussion: true }),
    });

    if (!response.ok) {
      throw new Error('Failed to submit feedback stream');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },

  /**
   * Submit human chairman feedback (non-streaming for end session).
   */
  async submitHumanFeedback(conversationId, feedback) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/human-feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ feedback, continue_discussion: false }),
    });
    if (!response.ok) {
      throw new Error('Failed to submit feedback');
    }
    return response.json();
  },

  /**
   * End session with rating.
   */
  async endSession(conversationId, rating) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/end-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ rating }),
    });
    if (!response.ok) {
      throw new Error('Failed to end session');
    }
    return response.json();
  },
};
