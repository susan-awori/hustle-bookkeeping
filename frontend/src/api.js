function normalizeApiBase(raw) {
  const value = (raw || "").trim().replace(/\/+$/, "");
  if (!value) return "";
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  return `https://${value}`;
}

const API = normalizeApiBase(import.meta.env.VITE_API_URL);

const ACCESS = "hustle_access";
const REFRESH = "hustle_refresh";

export function getApiBase() {
  return API;
}

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

export function formatApiError(data, fallback = "Something went wrong") {
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail) && data.detail.length) {
    return data.detail.map((item) => item.msg || String(item)).join(" ");
  }
  if (typeof data.message === "string") return data.message;
  return fallback;
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

  let response;
  try {
    response = await fetch(`${API}${path}`, { ...options, headers });
  } catch {
    const hint = import.meta.env.DEV
      ? "Cannot reach the API. Start Postgres, run the backend on port 8000, then refresh."
      : "Cannot reach the server. Check your connection and try again.";
    throw new Error(hint);
  }

  if (response.status === 401 && retry) {
    const ok = await refreshTokens();
    if (ok) return api(path, options, false);
  }
  return response;
}
