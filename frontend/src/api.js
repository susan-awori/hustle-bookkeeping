const API = import.meta.env.VITE_API_URL || "";

const ACCESS = "hustle_access";
const REFRESH = "hustle_refresh";

export function getAccess() {
  return sessionStorage.getItem(ACCESS);
}

export function setTokens(access, refresh) {
  sessionStorage.setItem(ACCESS, access);
  sessionStorage.setItem(REFRESH, refresh);
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS);
  sessionStorage.removeItem(REFRESH);
}

async function refreshTokens() {
  const refresh = sessionStorage.getItem(REFRESH);
  if (!refresh) return false;
  const response = await fetch(`${API}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!response.ok) {
    clearTokens();
    return false;
  }
  const data = await response.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

export async function api(path, options = {}, retry = true) {
  const headers = { ...(options.headers || {}) };
  const token = getAccess();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 401 && retry) {
    const ok = await refreshTokens();
    if (ok) return api(path, options, false);
  }
  return response;
}
