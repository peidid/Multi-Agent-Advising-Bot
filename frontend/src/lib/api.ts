/**
 * API client for the Multi-Agent Advising backend.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types
export interface User {
  id: string;
  email: string;
  name: string;
  profile?: UserProfile;
}

export interface UserProfile {
  major?: string;
  minors?: string[];
  gpa?: number;
  completed_courses?: string[];
  interests?: string[];
}

export interface Conversation {
  _id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: Message[];
}

export interface Message {
  _id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: {
    agents_used?: string[];
  };
}

export interface ChatResponse {
  conversation_id: string;
  response: string;
  agents_used: string[];
  workflow_details?: {
    conflicts: number;
    risks: number;
  };
}

// Token management
let authToken: string | null = null;

export function setToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
}

export function getToken(): string | null {
  if (!authToken && typeof window !== 'undefined') {
    authToken = localStorage.getItem('auth_token');
  }
  return authToken;
}

// API helper
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auth API
export const auth = {
  async register(email: string, name: string, password: string): Promise<{ user: User; token: string }> {
    const result = await apiFetch<{ user: User; token: string }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, name, password }),
    });
    setToken(result.token);
    return result;
  },

  async login(email: string, password: string): Promise<{ user: User; token: string }> {
    const result = await apiFetch<{ user: User; token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setToken(result.token);
    return result;
  },

  async me(): Promise<User> {
    return apiFetch<User>('/api/auth/me');
  },

  async updateProfile(profile: UserProfile): Promise<{ success: boolean; profile: UserProfile }> {
    return apiFetch('/api/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  },

  logout() {
    setToken(null);
  },
};

// Conversations API
export const conversations = {
  async list(): Promise<{ conversations: Conversation[] }> {
    return apiFetch('/api/conversations');
  },

  async create(title?: string): Promise<Conversation> {
    return apiFetch('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  },

  async get(id: string): Promise<Conversation> {
    return apiFetch(`/api/conversations/${id}`);
  },

  async delete(id: string): Promise<{ success: boolean }> {
    return apiFetch(`/api/conversations/${id}`, {
      method: 'DELETE',
    });
  },
};

// Streaming event types
export interface StreamEvent {
  type: string;
  agent?: string;
  phase?: string;
  message?: string;
  timestamp?: string;
  data?: Record<string, unknown>;
}

export interface WorkflowDetails {
  agents_used: string[];
  agent_details: Record<string, {
    answer: string;
    confidence: number;
    risks: Array<{ type: string; severity: string; description: string }>;
    relevant_policies: string[];
  }>;
  execution_stats?: {
    execution_mode?: string;
    total_execution_time?: number;
    parallel_speedup?: number;
  };
  phase_timing?: Record<string, number>;
  stream_events?: StreamEvent[];
}

export interface StreamCallbacks {
  onEvent?: (event: StreamEvent) => void;
  onAnswer?: (answer: string, conversationId: string, workflowDetails?: WorkflowDetails) => void;
  onError?: (error: string) => void;
  onComplete?: () => void;
}

// Chat API
export const chat = {
  async send(message: string, conversationId?: string): Promise<ChatResponse> {
    return apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });
  },

  /**
   * Send a message with streaming updates.
   * Returns real-time events as the multi-agent workflow progresses.
   */
  async sendStreaming(
    message: string,
    conversationId: string | undefined,
    callbacks: StreamCallbacks
  ): Promise<void> {
    const token = getToken();

    const response = await fetch(`${API_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      callbacks.onError?.(error.detail || `HTTP ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      callbacks.onError?.('No response body');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data.trim()) {
              try {
                const event = JSON.parse(data) as StreamEvent;

                // Handle different event types
                if (event.type === 'answer') {
                  const answerData = event.data as {
                    content: string;
                    conversation_id: string;
                    agents_used?: string[];
                    agent_details?: Record<string, unknown>;
                    execution_stats?: Record<string, unknown>;
                    phase_timing?: Record<string, number>;
                  };
                  const workflowDetails: WorkflowDetails = {
                    agents_used: answerData.agents_used || [],
                    agent_details: (answerData.agent_details || {}) as WorkflowDetails['agent_details'],
                    execution_stats: answerData.execution_stats as WorkflowDetails['execution_stats'],
                    phase_timing: answerData.phase_timing,
                  };
                  callbacks.onAnswer?.(answerData.content, answerData.conversation_id, workflowDetails);
                } else if (event.type === 'error') {
                  const errorData = event.data as { message: string };
                  callbacks.onError?.(errorData.message);
                } else if (event.type === 'done') {
                  callbacks.onComplete?.();
                } else {
                  // All other events (agent status, coordinator, etc.)
                  callbacks.onEvent?.(event);
                }
              } catch (e) {
                console.error('Failed to parse SSE event:', e, data);
              }
            }
          }
        }
      }

      // Handle any remaining data in buffer
      if (buffer.startsWith('data: ')) {
        const data = buffer.slice(6);
        if (data.trim()) {
          try {
            const event = JSON.parse(data) as StreamEvent;
            if (event.type === 'done') {
              callbacks.onComplete?.();
            }
          } catch {
            // Ignore incomplete data
          }
        }
      }

    } catch (error) {
      callbacks.onError?.(error instanceof Error ? error.message : 'Stream error');
    } finally {
      reader.releaseLock();
    }
  },
};

// Health check
export async function checkHealth(): Promise<{ status: string; database: string }> {
  const response = await fetch(`${API_URL}/api/health`);
  return response.json();
}
