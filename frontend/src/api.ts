export type User = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "farmer" | "extension" | "admin";
  district: string;
  phone: string;
  profile_image: string | null;
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

export type LiveWeather = {
  source: string;
  attribution_url: string;
  data_type: "modelled_current_conditions_and_forecast";
  location: { latitude: number; longitude: number };
  timezone: string;
  farm: { id: number; name: string; district: string };
  current: {
    data_type: "modelled_current_conditions";
    time: string;
    temperature_c: number | null;
    feels_like_c: number | null;
    relative_humidity_pct: number | null;
    precipitation_mm: number | null;
    weather_code: number | null;
    condition: string;
    wind_speed_kmh: number | null;
    wind_direction_degrees: number | null;
    cloud_cover_pct: number | null;
    is_day: boolean | null;
  };
  daily_forecast: {
    date: string;
    weather_code: number | null;
    condition: string;
    temperature_max_c: number | null;
    temperature_min_c: number | null;
    precipitation_sum_mm: number | null;
    precipitation_probability_max_pct: number | null;
    et0_mm: number | null;
  }[];
};

export type CropDiseaseResult = {
  crop: string;
  possible_disease: string;
  confidence_pct: number;
  visual_signs: string[];
  analysis_type: "classifier" | "vision_language";
  treatment: string;
  prevention: string;
  disclaimer: string;
};

export type IrrigationPlan = {
  crop: string;
  stage: string;
  crop_coefficient: number;
  farm_area_hectares: number;
  soil_type: string;
  source: string;
  farm: { id: number; name: string; district: string };
  daily: {
    date: string;
    et0_mm: number;
    crop_water_need_mm: number;
    rainfall_mm: number;
    effective_rainfall_mm: number;
    net_irrigation_need_mm: number;
  }[];
  schedule: { date: string; depth_mm: number; volume_liters: number }[];
  totals: {
    crop_water_need_mm: number;
    effective_rainfall_mm: number;
    net_irrigation_need_mm: number;
    net_irrigation_volume_liters: number;
  };
  soil_moisture_pct?: number;
  soil_moisture_status?: "low" | "moderate" | "adequate";
  soil_moisture_note?: string;
  methodology: string;
};

export type HarvestRecord = {
  id: number;
  farm: number;
  farm_name: string;
  crop: string;
  harvest_date: string;
  quantity_kg: string;
  recorded_by: number | null;
  created_at: string;
};

export type YieldForecast = {
  farm: { id: number; name: string; district: string; area_hectares: number };
  crop: string;
  forecast_available: boolean;
  reference_yield_kg_per_hectare: number | null;
  expected_harvest_kg: number | null;
  forecast_basis: "farm_history" | "benchmark" | null;
  benchmark: {
    crop: string;
    district: string;
    reference_year: number;
    yield_kg_per_hectare: string;
    source_title: string;
    source_url: string;
  } | null;
  benchmark_trend: {
    crop: string;
    district: string;
    reference_year: number;
    yield_kg_per_hectare: string;
    source_title: string;
    source_url: string;
  }[];
  harvest_trend: { year: number; quantity_kg: number; harvest_count: number }[];
  harvest_records: HarvestRecord[];
  climate_context: {
    available: boolean;
    detail?: string;
    source?: string;
    period?: { start: string; end: string };
    screening_available?: boolean;
    risks?: { type: string; level: string; observed: number; unit: string; threshold: string; action: string }[];
    coverage?: { rainfall_observations: number; temperature_observations: number; expected_days: number };
    methodology?: string;
  };
  methodology: string;
};

export type MarketPrice = {
  id: number | string;
  commodity: string;
  market: string;
  district: string;
  price: string;
  unit: string;
  currency: string;
  observed_at: string;
  price_type: string;
  source_title: string;
  source_url: string;
};

export type MarketIntelligence = {
  prices: MarketPrice[];
  window_start: string;
  data_note: string;
  wfp_feed_available: boolean;
  latest_wfp_observation: string | null;
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

// Paths that never need an Authorization header and must never trigger a token
// refresh attempt. Sending stale tokens to these endpoints can produce confusing
// 401 / 500 errors that bubble up as sign-in failures.
const PUBLIC_PATHS = ["/auth/token/", "/auth/register/", "/auth/token/refresh/", "/auth/password-reset/"];

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isPublic = PUBLIC_PATHS.some((p) => path.startsWith(p));

  const send = (token: string | null) => {
    const headers = new Headers(options.headers);
    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (token && !isPublic) headers.set("Authorization", `Bearer ${token}`);
    return fetch(`/api${path}`, { ...options, headers });
  };

  let response = await send(isPublic ? null : localStorage.getItem("agri_access"));

  // Only attempt a token refresh for protected endpoints that return 401.
  if (!isPublic && response.status === 401 && localStorage.getItem("agri_refresh")) {
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
