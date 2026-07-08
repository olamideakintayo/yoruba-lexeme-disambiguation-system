import type { CustomEntry, CustomEntryInput, KeyboardResponse, SearchResponse, WordValidationResponse } from './types';

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

type RequestOptions = {
  method?: string;
  token?: string;
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  if (options.token) headers['X-Admin-Token'] = options.token;

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function searchLexemes(query: string): Promise<SearchResponse> {
  return request<SearchResponse>(`/api/search?q=${encodeURIComponent(query)}`);
}

export function getKeyboard(): Promise<KeyboardResponse> {
  return request<KeyboardResponse>('/api/keyboard');
}

export function validateCustomWord(word: string, token: string): Promise<WordValidationResponse> {
  return request<WordValidationResponse>('/api/admin/validate-word', {
    method: 'POST',
    token,
    body: { word },
  });
}

export function getCustomEntries(token: string): Promise<CustomEntry[]> {
  return request<CustomEntry[]>('/api/admin/custom-entries', { token });
}

export function createCustomEntry(input: CustomEntryInput, token: string): Promise<CustomEntry> {
  return request<CustomEntry>('/api/admin/custom-entries', {
    method: 'POST',
    token,
    body: input,
  });
}

export function deleteCustomEntry(id: string, token: string): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(`/api/admin/custom-entries/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    token,
  });
}
