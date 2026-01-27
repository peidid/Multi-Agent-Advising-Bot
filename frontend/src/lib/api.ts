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
};

// Health check
export async function checkHealth(): Promise<{ status: string; database: string }> {
  const response = await fetch(`${API_URL}/api/health`);
  return response.json();
}
