import { auth } from "../firebase";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * Custom Error class with user-friendly retry hints
 */
export class ApiError extends Error {
  constructor(message, status = 500, retryable = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryable = retryable;
  }
}

/**
 * Base authenticated fetch wrapper
 */
async function request(endpoint, options = {}) {
  let token = null;
  if (auth.currentUser) {
    try {
      token = await auth.currentUser.getIdToken(true);
    } catch (err) {
      console.warn("Could not retrieve fresh ID token:", err);
    }
  }

  const headers = { ...(options.headers || {}) };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint}`;

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (netErr) {
    console.error("Network error connecting to API:", netErr);
    throw new ApiError(
      "Unable to connect to recycling server. Please verify network or server connection.",
      0,
      true
    );
  }

  if (response.status === 429 || response.status === 503) {
    throw new ApiError("AI is busy, try again in a few seconds", response.status, true);
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const detail = data?.detail || `Server error (${response.status})`;
    const retryable = data?.retryable || response.status >= 500;
    throw new ApiError(detail, response.status, retryable);
  }

  return data;
}

/**
 * Drop item at kiosk
 * POST /api/drop (multipart/form-data)
 */
export async function dropItem({ imageBlob, weightG, machineId = "sim-machine-01" }) {
  const formData = new FormData();
  formData.append("image", imageBlob, "item_capture.jpg");
  formData.append("weight_g", weightG.toString());
  formData.append("machine_id", machineId);

  return await request("/api/drop", {
    method: "POST",
    body: formData,
  });
}

/**
 * Fetch authenticated user profile & balance
 * GET /api/me
 */
export async function getMyProfile() {
  return await request("/api/me", {
    method: "GET",
  });
}

/**
 * Fetch user's recent recycling drops
 * GET /api/drops?limit=20
 */
export async function getMyDrops(limit = 20) {
  return await request(`/api/drops?limit=${encodeURIComponent(limit)}`, {
    method: "GET",
  });
}
