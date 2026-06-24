/**
 * Minimal typed fetch wrapper targeting the backend API (proxied to
 * http://localhost:8000 via vite.config.ts). No feature logic here.
 */

const API_BASE = "/api/v1";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
