export type User = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "farmer" | "extension" | "admin";
  district: string;
  phone: string;
};

export type Farm = {
  id: number;
  name: string;
  district: string;
  crop: string;
  size_hectares: string;
  latitude: string;
  longitude: string;
  soil_type: string;
  owner_name?: string;
};

export type Observation = {
  date: string;
  values: Record<string, { value: number; unit: string; label: string }>;
};

export type Weather = {
  source: string;
  data_type: "historical_observations";
  is_forecast: false;
  period: { start: string; end: string };
  observations: Observation[];
};

export type Recommendation = {
  id: number;
  crop: string;
  guidance: string;
  basis: string[];
  risks: string[];
  created_at: string;
};

export type NotificationItem = {
  id: number;
  farm: number | null;
  title: string;
  message: string;
  level: string;
  read_at: string | null;
  created_at: string;
};

export type FarmQuestion = {
  id: number;
  farm: number;
  farm_name: string;
  district: string;
  asked_by: number;
  asked_by_name: string;
  question: string;
  answer: string;
  status: "open" | "responded";
  answered_by_name: string;
  created_at: string;
  answered_at: string | null;
};

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const send = (token: string | null) => {
    const headers = new Headers(options.headers);
    if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(`/api${path}`, { ...options, headers });
  };
  let response = await send(localStorage.getItem("agri_access"));
  if (response.status === 401 && localStorage.getItem("agri_refresh")) {
    const refreshResponse = await fetch("/api/auth/token/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: localStorage.getItem("agri_refresh") }),
    });
    if (refreshResponse.ok) {
      const tokens = (await refreshResponse.json()) as { access: string };
      localStorage.setItem("agri_access", tokens.access);
      response = await send(tokens.access);
    } else {
      localStorage.removeItem("agri_access");
      localStorage.removeItem("agri_refresh");
    }
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      const values = Object.values(body).flat().map((value) => typeof value === "string" ? value : "");
      message = body.detail || values.join(" ") || message;
    } catch {
      // Keep the HTTP status message if the server response is not JSON.
    }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}
