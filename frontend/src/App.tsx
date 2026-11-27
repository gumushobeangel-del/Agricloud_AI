import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import LandingPage from "./LandingPage";
import {
  Activity, BarChart3, Bell, Bug, CalendarDays, Check, ChevronDown, ChevronRight, LogOut, Pencil,
  CloudSun, Droplets, Ellipsis, Leaf, MapPin, Menu, Plus, Search, ShieldAlert, Store, Upload, Wind,
  MessageCircleQuestion, Sprout, Sun, Thermometer, Tractor, TrendingUp, X, Users, ShieldCheck,
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { api, ApiError, CropDiseaseResult, Farm, FarmQuestion, HarvestRecord, IrrigationPlan, LiveWeather, MarketIntelligence, MarketPrice, NotificationItem, Recommendation, User, Weather, YieldForecast } from "./api";

type Page = "overview" | "admin" | "farms" | "weather" | "advisor" | "disease" | "irrigation" | "yield" | "markets" | "map" | "assistant" | "questions" | "alerts" | "analytics" | "profile";
const mainLinks: { id: Page; label: string; icon: typeof Activity }[] = [
  { id: "overview", label: "Dashboard", icon: Activity },
  { id: "admin", label: "Administration", icon: ShieldCheck },
  { id: "farms", label: "Crop management", icon: Tractor },
  { id: "weather", label: "Weather", icon: CloudSun },
  { id: "advisor", label: "Planting advisor", icon: Sprout },
  { id: "disease", label: "Crop disease check", icon: Bug },
  { id: "irrigation", label: "Smart irrigation", icon: Droplets },
  { id: "yield", label: "Yield forecast", icon: BarChart3 },
  { id: "markets", label: "Market intelligence", icon: Store },
  { id: "map", label: "Field monitoring", icon: MapPin },
  { id: "assistant", label: "AI assistant", icon: Ellipsis },
  { id: "questions", label: "Farmer questions", icon: MessageCircleQuestion },
  { id: "alerts", label: "Alerts", icon: ShieldAlert },
  { id: "analytics", label: "Reports", icon: TrendingUp },
];
const pageTitles: Record<Page, string> = {
  overview: "Overview", admin: "System administration", farms: "My farms", weather: "Weather intelligence", advisor: "Planting advisor",
  disease: "Crop disease detection", irrigation: "Smart irrigation",
  yield: "Crop yield forecast", markets: "Market intelligence",
  map: "Farm map", assistant: "AI farming assistant", questions: "Farmer questions", alerts: "Climate risk alerts",
  analytics: "Farm analytics", profile: "Profile settings",
};

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [page, setPage] = useState<Page>("overview");
  const [booting, setBooting] = useState(Boolean(localStorage.getItem("agri_access")));
  const [authError, setAuthError] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  // Show landing page when no session exists and user hasn't clicked through yet.
  const [showLanding, setShowLanding] = useState(!localStorage.getItem("agri_access"));

  const loadWorkspace = async () => {
    try {
      const current = await api<User>("/auth/me/");
      setUser(current);
      setPage(current.role === "admin" ? "admin" : "overview");
    } catch (error) {
      // Always clear stale tokens on any auth or server error.
      localStorage.removeItem("agri_access");
      localStorage.removeItem("agri_refresh");
      setUser(null);
      // Only surface a message for server errors. A 401 just means the session
      // expired — the user will sign in again without seeing a confusing error.
      if (error instanceof ApiError && error.status >= 500) {
        setAuthError("The server is temporarily unavailable. Please try signing in again.");
      } else {
        setAuthError("");
      }
      setBooting(false);
      return;
    }
    try {
      setFarms(await api<Farm[]>("/farms/"));
      setAuthError("");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        localStorage.removeItem("agri_access");
        localStorage.removeItem("agri_refresh");
        setUser(null);
      }
      setAuthError(error instanceof Error ? error.message : "Unable to load farm records.");
    } finally { setBooting(false); }
  };

  useEffect(() => {
    if (localStorage.getItem("agri_access")) void loadWorkspace();
    else setBooting(false);
  }, []);

  const refreshFarms = async () => setFarms(await api<Farm[]>("/farms/"));

  async function signIn(username: string, password: string) {
    setAuthError("");
    const tokens = await api<{ access: string; refresh: string }>("/auth/token/", {
      method: "POST", body: JSON.stringify({ username, password }),
    });
    localStorage.setItem("agri_access", tokens.access);
    localStorage.setItem("agri_refresh", tokens.refresh);
    await loadWorkspace();
  }

  async function register(data: Record<string, string>) {
    const tokens = await api<{ access: string; refresh: string; user: User }>("/auth/register/", {
      method: "POST", body: JSON.stringify(data),
    });
    localStorage.setItem("agri_access", tokens.access);
    localStorage.setItem("agri_refresh", tokens.refresh);
    await loadWorkspace();
  }

  async function signOut() {
    let notice = "";
    const refresh = localStorage.getItem("agri_refresh");
    if (refresh) {
      try { await api<{ detail: string }>("/auth/logout/", { method: "POST", body: JSON.stringify({ refresh }) }); }
      catch { notice = "This device was signed out, but server-side token revocation could not be confirmed."; }
    }
    localStorage.removeItem("agri_access");
    localStorage.removeItem("agri_refresh");
    setUser(null);
    setFarms([]);
    setPage("overview");
    setAuthError(notice);
  }

  if (booting) return <div className="boot-screen"><div className="brand-mark"><Leaf size={18} /></div><span className="spinner" />Restoring your workspace…</div>;
  if (!user && showLanding) return <LandingPage onGetStarted={() => setShowLanding(false)} />;
  if (!user) return <AuthPage onSignIn={signIn} onRegister={register} error={authError} />;

  return (
    <div className="app-shell">
      {mobileNav && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
      <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
        <div className="brand"><div className="brand-mark"><Leaf size={18} fill="currentColor" /></div><span>agricloud<span className="brand-ai">.ai</span></span></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {mainLinks.slice(0, 2).filter((item) => item.id !== "admin" || user.role === "admin").map((item) => <NavItem key={item.id} item={item} active={page === item.id} onClick={() => { setPage(item.id); setMobileNav(false); }} />)}
          {mainLinks.slice(2, 4).map((item) => <NavItem key={item.id} item={item} active={page === item.id} onClick={() => { setPage(item.id); setMobileNav(false); }} />)}
          <div className="nav-section">FIELD TOOLS</div>
          {mainLinks.slice(4).filter((item) => item.id !== "questions" || user.role !== "farmer").map((item) => <NavItem key={item.id} item={item} active={page === item.id} onClick={() => { setPage(item.id); setMobileNav(false); }} />)}
        </nav>
        <div className="sidebar-bottom">
          <div className="season-card"><div className="season-icon"><Sun size={16} /></div><div><strong>Season watch</strong><span>Local climate context</span></div><ChevronRight size={15} /></div>
          <button className={`nav-item ${page === "profile" ? "active" : ""}`} onClick={() => setPage("profile")}><UserAvatar user={user} className="avatar" /><span className="profile-label"><strong>{user.first_name || user.username}</strong><small>Settings · {roleLabel(user.role)}</small></span><ChevronDown size={14} /></button>
        </div>
      </aside>
      <main className="main-shell">
        <header className="topbar">
          <button className="icon-btn mobile-menu" aria-label="Open menu" onClick={() => setMobileNav(true)}><Menu size={19} /></button>
          <div className="breadcrumbs"><span>Workspace</span><ChevronRight size={13} /><strong>{pageTitles[page]}</strong></div>
          <div className="topbar-actions"><div className="searchbox"><Search size={16} /><input placeholder="Search farms, crops..." aria-label="Search" /><kbd>⌘ K</kbd></div><button className="icon-btn notification-btn" aria-label="Notifications" onClick={() => setPage("alerts")}><Bell size={18} /></button><button className="top-add-farm" onClick={() => setPage("farms")} aria-label="Open farm management"><Plus size={16} /><span>Add farm</span></button><button className="user-chip" onClick={() => setPage("profile")} aria-label="Open profile settings"><UserAvatar user={user} className="top-avatar" /><span className="user-chip-copy"><strong>{user.first_name || user.username}</strong><small>{roleLabel(user.role)}</small></span><ChevronDown size={13} /></button><button className="icon-btn logout-btn" aria-label="Sign out" title="Sign out" onClick={() => void signOut()}><LogOut size={16} /></button></div>
        </header>
        <div className="content">
          {page === "overview" && <Dashboard user={user} farms={farms} go={setPage} />}
          {page === "admin" && user.role === "admin" && <AdminPage user={user} farms={farms} go={setPage} />}
          {page === "farms" && <FarmsPage farms={farms} refresh={refreshFarms} readOnly={user.role === "extension"} />}
          {page === "weather" && <WeatherPage farms={farms} />}
          {page === "advisor" && <AdvisorPage farms={farms} />}
          {page === "disease" && <CropDiseasePage />}
          {page === "irrigation" && <IrrigationPage farms={farms} />}
          {page === "yield" && <YieldPage farms={farms} user={user} />}
          {page === "markets" && <MarketPage />}
          {page === "map" && <MapPage farms={farms} />}
          {page === "assistant" && <AssistantPage user={user} farms={farms} onAskExtension={() => setPage("questions")} />}
          {page === "questions" && <QuestionsPage user={user} farms={farms} />}
          {page === "alerts" && <AlertsPage />}
          {page === "analytics" && <AnalyticsPage farms={farms} />}
          {page === "profile" && <ProfilePage user={user} onUpdated={setUser} />}
        </div>
      </main>
    </div>
  );
}

function NavItem({ item, active, onClick }: { item: (typeof mainLinks)[number]; active: boolean; onClick: () => void }) {
  const Icon = item.icon;
  return <button className={`nav-item ${active ? "active" : ""}`} onClick={onClick}><Icon size={17} strokeWidth={1.8} /><span>{item.label}</span></button>;
}

function PageHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1><p>{description}</p></div>{action}</div>;
}

function Dashboard({ user, farms, go }: { user: User; farms: Farm[]; go: (page: Page) => void }) {
  const [weather, setWeather] = useState<Weather | null>(null);
  const [weatherError, setWeatherError] = useState("");
  const [liveWeather, setLiveWeather] = useState<LiveWeather | null>(null);
  const [liveWeatherError, setLiveWeatherError] = useState("");
  const [analytics, setAnalytics] = useState<{ farm_count: number; total_hectares: number; crop_distribution: { crop: string; count: number }[] } | null>(null);
  const [recentRecommendation, setRecentRecommendation] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.allSettled([
      api<NonNullable<typeof analytics>>("/analytics/"),
      farms.length ? api<Weather>(`/weather/?farm_id=${farms[0].id}`) : Promise.resolve(null),
      api<Recommendation[]>("/recommendations/list/"),
      farms.length ? api<LiveWeather>(`/weather/current/?farm_id=${farms[0].id}`) : Promise.resolve(null),
    ]).then(([statsResult, weatherResult, recommendationsResult, liveWeatherResult]) => {
      if (!active) return;
      if (statsResult.status === "fulfilled") setAnalytics(statsResult.value);
      if (weatherResult.status === "fulfilled") {
        setWeather(weatherResult.value);
        if (weatherResult.value) setWeatherError("");
      } else setWeatherError(weatherResult.reason instanceof Error ? weatherResult.reason.message : "Could not load climate observations.");
      if (recommendationsResult.status === "fulfilled") setRecentRecommendation(recommendationsResult.value[0] ?? null);
      if (liveWeatherResult.status === "fulfilled") {
        setLiveWeather(liveWeatherResult.value);
        setLiveWeatherError("");
      } else {
        setLiveWeather(null);
        setLiveWeatherError(liveWeatherResult.reason instanceof Error ? liveWeatherResult.reason.message : "Could not load current weather.");
      }
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [farms]);
  useEffect(() => {
    if (!farms.length) return;
    const interval = window.setInterval(() => {
      api<LiveWeather>(`/weather/current/?farm_id=${farms[0].id}`)
        .then((data) => { setLiveWeather(data); setLiveWeatherError(""); })
        .catch((err: Error) => setLiveWeatherError(err.message));
    }, 15 * 60 * 1000);
    return () => window.clearInterval(interval);
  }, [farms]);
  const latestObservation = weather?.observations.at(-1);
  const latest = latestObservation?.values;
  const current = liveWeather?.current;
  const rainfallValues = weather?.observations
    .map((day) => day.values.PRECTOTCORR?.value)
    .filter((value): value is number => value !== undefined && Number.isFinite(value)) ?? [];
  const rainfall = rainfallValues.length ? rainfallValues.reduce((sum, value) => sum + value, 0) : null;
  const chartData = weather?.observations.map((day) => ({
    date: day.date.slice(5),
    rain: day.values.PRECTOTCORR?.value ?? null,
    temp: day.values.T2M?.value ?? null,
  })) ?? [];
  const cropData = analytics?.crop_distribution ?? [];
  const name = user.first_name || user.username;
  const dateLabel = new Intl.DateTimeFormat("en-UG", { weekday: "short", day: "numeric", month: "short" }).format(new Date());
  const farm = farms[0];
  const actions: { title: string; detail: string; icon: ReactNode; page: Page }[] = [
    {
      title: farms.length ? "Review farm records" : "Add your first farm",
      detail: farms.length ? `${farms.length} location${farms.length === 1 ? "" : "s"} saved in your workspace.` : "Save coordinates to enable local climate observations.",
      icon: <MapPin size={15} />,
      page: "farms",
    },
    {
      title: recentRecommendation ? `Review ${recentRecommendation.crop} guidance` : "Generate planting guidance",
      detail: recentRecommendation ? recentRecommendation.guidance : "Compare a crop plan with historical farm conditions.",
      icon: <Sprout size={15} />,
      page: "advisor",
    },
    {
      title: weather ? "Explore climate history" : "View weather intelligence",
      detail: weather ? `Historical observations through ${latestObservation?.date ?? weather.period.end}.` : "Review NASA POWER observations for a registered farm.",
      icon: <CloudSun size={15} />,
      page: "weather",
    },
  ];

  return <>
    <div className="dashboard-heading">
      <div><div className="eyebrow">{dateLabel} · FIELD INTELLIGENCE</div><h1>Welcome back, {name}</h1><p>Here’s what’s happening across your farms today.</p></div>
      <button className="button button-primary" onClick={() => go("farms")}><Plus size={16} /> Add a farm</button>
    </div>
    <section className="metric-grid">
      <MetricCard icon={<Tractor size={17} />} label="Total fields" value={analytics?.farm_count ?? (loading ? "—" : farms.length)} note="Registered farm locations" tone="green" />
      <MetricCard icon={<Sprout size={17} />} label="Total area" value={analytics ? `${analytics.total_hectares.toLocaleString()} ha` : "—"} note="Across saved farm records" tone="lime" />
      <MetricCard icon={<Leaf size={17} />} label="Crop types" value={analytics ? cropData.length : "—"} note="Reported across your farms" tone="blue" />
      <MetricCard icon={<CloudSun size={17} />} label="Observed days" value={weather ? weather.observations.length : "—"} note={weather ? `${weather.source} · historical` : "Add a farm for local data"} tone="orange" />
    </section>
    <section className="dashboard-overview-grid">
      <section className="panel dashboard-field-panel">
        <div className="panel-heading"><div><h3>Field conditions</h3><p>Latest available climate observation</p></div><button className="more-btn" aria-label="View weather intelligence" onClick={() => go("weather")}><Ellipsis size={18} /></button></div>
        <div className="field-condition-summary">
          <div className="condition-orbit"><div className="orbit"><div className="orbit-inner"><CloudSun size={22} /><b>{latest?.T2M ? `${latest.T2M.value.toFixed(0)}°` : "—"}</b><small>air temp</small></div></div></div>
          <div className="field-condition-copy"><span className="condition-status"><i /> {latestObservation ? "Observation available" : "Awaiting farm data"}</span><strong>{farm?.name || "No farm selected"}</strong><small>{farm ? `${farm.district} district` : "Add a farm to get local readings."}</small><small>{latestObservation?.date ? `Observed ${latestObservation.date}` : "NASA POWER historical data"}</small></div>
        </div>
        <div className="dashboard-condition-list">
          <Condition icon={<Droplets size={14} />} label="Rainfall" value={latest?.PRECTOTCORR ? `${latest.PRECTOTCORR.value.toFixed(1)} mm` : "No reading"} />
          <Condition icon={<Activity size={14} />} label="Humidity" value={latest?.RH2M ? `${latest.RH2M.value.toFixed(0)}%` : "No reading"} />
          <Condition icon={<Sun size={14} />} label="Solar radiation" value={latest?.ALLSKY_SFC_SW_DWN ? `${latest.ALLSKY_SFC_SW_DWN.value.toFixed(1)} kWh/m²` : "No reading"} />
        </div>
        <div className="dashboard-data-note">Historical observations · not a forecast or soil test</div>
      </section>

      <section className="panel dashboard-map-panel">
        <div className="panel-heading"><div><h3>Field monitoring</h3><p>Registered farm locations</p></div><button className="subtle-button" onClick={() => go("map")}>Open map <ChevronRight size={14} /></button></div>
        <div className="dashboard-map-area">
          <FarmMap farms={farms} compact />
          {!farms.length && <div className="map-empty-overlay"><span className="empty-icon"><MapPin size={18} /></span><strong>No farm locations yet</strong><span>Add coordinates to see your farms here.</span><button className="button button-secondary button-small" onClick={() => go("farms")}><Plus size={14} /> Add a farm</button></div>}
          {farms.length > 0 && <div className="map-location-tag"><MapPin size={13} /><span>{farms.length} registered location{farms.length === 1 ? "" : "s"}</span></div>}
        </div>
        <div className="map-legend"><span className="map-pip" /> Farm locations <span className="map-count">{farm?.district || "Uganda"}</span></div>
      </section>

      <div className="dashboard-right-stack">
        <section className="panel dashboard-weather-panel">
          <div className="panel-heading"><div><h3>Current weather</h3><p>{current ? `${current.condition} · ${liveWeather?.farm.district}` : "Model-based conditions at your farm"}</p></div><CloudSun size={17} className="panel-heading-icon" /></div>
          {liveWeatherError && <InlineNotice message={liveWeatherError} />}
          {current ? <>
            <div className="weather-reading-grid dashboard-live-grid">
              <div className="weather-reading weather-temperature"><Thermometer size={15} /><span>Temperature</span><strong>{current.temperature_c === null ? "—" : `${current.temperature_c.toFixed(1)}°C`}</strong></div>
              <div className="weather-reading"><Droplets size={15} /><span>Precipitation</span><strong>{current.precipitation_mm === null ? "—" : `${current.precipitation_mm.toFixed(1)} mm`}</strong></div>
              <div className="weather-reading"><Activity size={15} /><span>Humidity</span><strong>{current.relative_humidity_pct === null ? "—" : `${current.relative_humidity_pct.toFixed(0)}%`}</strong></div>
              <div className="weather-reading"><Wind size={15} /><span>Wind</span><strong>{current.wind_speed_kmh === null ? "—" : `${current.wind_speed_kmh.toFixed(0)} km/h`}</strong></div>
            </div>
            <div className="dashboard-data-note">Modelled conditions · refreshes every 15 minutes · {current.time.replace("T", " ")} local time · <a href={liveWeather.attribution_url} target="_blank" rel="noreferrer">Open-Meteo</a></div>
          </> : !liveWeatherError && <div className="live-weather-empty">{loading ? "Loading current conditions…" : farms.length ? "Current weather is not available right now." : "Add a farm to see local weather."}</div>}
        </section>

        <section className="panel dashboard-soil-panel">
          <div className="panel-heading"><div><h3>Farm profile</h3><p>{farm?.name || "Saved field details"}</p></div><Sprout size={17} className="panel-heading-icon" /></div>
          {farm ? <><div className="soil-profile-grid"><div><span>Soil type</span><strong>{farm.soil_type.replace(/_/g, " ") || "Not recorded"}</strong></div><div><span>Main crop</span><strong>{farm.crop || "Not recorded"}</strong></div></div><div className="soil-profile-foot"><span>{farm.size_hectares} ha · {farm.district}</span><button className="subtle-button" onClick={() => go("farms")}>Manage <ChevronRight size={13} /></button></div><p className="soil-profile-note">Farmer-recorded details; no sensor-based soil test is connected.</p></> : <div className="soil-empty"><Sprout size={20} /><strong>No farm profile yet</strong><span>Add a farm to record its soil and crop details.</span><button className="subtle-button" onClick={() => go("farms")}>Add farm <ChevronRight size={13} /></button></div>}
        </section>
      </div>

      <section className="panel dashboard-actions-panel">
        <div className="panel-heading"><div><h3>Recommended next steps</h3><p>Actions based on your workspace</p></div></div>
        <div className="dashboard-action-list">{actions.map((action) => <button className="dashboard-action" key={action.title} onClick={() => go(action.page)}><span className="dashboard-action-icon">{action.icon}</span><span className="dashboard-action-copy"><strong>{action.title}</strong><small>{action.detail}</small></span><ChevronRight size={15} /></button>)}</div>
      </section>

      <section className="panel dashboard-trend-panel">
        <div className="panel-heading"><div><h3>Climate trend</h3><p>{weather ? `${weather.period.start} – ${weather.period.end} · historical observations` : "Rainfall and temperature at your farm"}</p></div><button className="subtle-button" onClick={() => go("weather")}>Details <ChevronRight size={13} /></button></div>
        {weatherError && <InlineNotice message={weatherError} />}
        {chartData.length ? <ClimateChart data={chartData} /> : <EmptyState loading={loading} title={farms.length ? "Climate data unavailable" : "No observations yet"} text={farms.length ? "Historical observations could not be loaded. Try the weather page again." : "Add a farm to retrieve location-specific NASA POWER observations."} />}
        <div className="chart-legend"><span><i className="legend-rain" /> Rainfall <small>mm/day</small></span><span><i className="legend-temp" /> Temperature <small>°C</small></span><span className="source-label"><span className="source-dot" /> Observed · not forecast</span></div>
        {rainfall !== null && <div className="trend-total">Rainfall total in period <strong>{rainfall.toFixed(1)} mm</strong></div>}
      </section>

      <section className="panel dashboard-crops-panel">
        <div className="panel-heading"><div><h3>Crop distribution</h3><p>Registered farms by reported crop</p></div><button className="more-btn" aria-label="View farm reports" onClick={() => go("analytics")}><Ellipsis size={18} /></button></div>
        {cropData.length ? <CropDistributionChart data={cropData} /> : <EmptyState loading={loading} title="No crop records yet" text="Add crop details to your farms to build this view." />}
        <button className="outlook-link" onClick={() => go("analytics")}>View reports <ChevronRight size={14} /></button>
      </section>
    </section>
  </>;
}

const cropChartColors = ["#16a34a", "#84cc16", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ec4899"];

function CropDistributionChart({ data }: { data: { crop: string; count: number }[] }) {
  const total = data.reduce((sum, item) => sum + item.count, 0);
  return <div className="crop-chart-layout">
    <div className="crop-chart-visual">
      <ResponsiveContainer width="100%" height="100%"><PieChart>
        <Pie data={data} dataKey="count" nameKey="crop" innerRadius="61%" outerRadius="83%" paddingAngle={2} stroke="none">
          {data.map((item, index) => <Cell key={item.crop} fill={cropChartColors[index % cropChartColors.length]} />)}
        </Pie>
        <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: 9, color: "#111827", fontSize: 10 }} formatter={(value: number) => [`${value} farm${value === 1 ? "" : "s"}`, "Recorded"]} />
      </PieChart></ResponsiveContainer>
      <div className="crop-chart-total"><strong>{total}</strong><span>farms</span></div>
    </div>
    <div className="crop-chart-legend">{data.slice(0, 5).map((item, index) => <div key={item.crop}><span><i style={{ backgroundColor: cropChartColors[index % cropChartColors.length] }} />{item.crop}</span><strong>{item.count}</strong></div>)}</div>
  </div>;
}

type AdminSummary = { users: number; farmers: number; extension_workers: number; farms: number; open_questions: number; active_crops: number; verified_crops: number; market_records: number };
type AdminUser = User & { is_active: boolean; date_joined: string };
type CropRecord = { id: number; name: string; local_names: string; category: string; guidance_notes: string; source_title: string; source_url: string; verified: boolean; active: boolean };

function AdminPage({ user, farms, go }: { user: User; farms: Farm[]; go: (page: Page) => void }) {
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [crops, setCrops] = useState<CropRecord[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [cropForm, setCropForm] = useState({ name: "", local_names: "", category: "", guidance_notes: "", source_title: "", source_url: "", verified: false, active: true });
  const [savingCrop, setSavingCrop] = useState(false);
  const loadAdmin = async () => {
    setLoading(true); setError("");
    try {
      const [overview, directory, catalog] = await Promise.all([
        api<AdminSummary>("/admin/overview/"), api<AdminUser[]>("/admin/users/"), api<CropRecord[]>("/crops/"),
      ]);
      setSummary(overview); setUsers(directory); setCrops(catalog);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load administration data."); }
    finally { setLoading(false); }
  };
  useEffect(() => { void loadAdmin(); }, []);
  const filteredUsers = users.filter((person) => `${person.first_name} ${person.last_name} ${person.username} ${person.email} ${person.district}`.toLowerCase().includes(search.toLowerCase()));
  async function updateUser(id: number, changes: Partial<Pick<AdminUser, "role" | "is_active">>) {
    setBusyId(id); setError(""); setNotice("");
    try {
      const updated = await api<AdminUser>(`/admin/users/${id}/`, { method: "PATCH", body: JSON.stringify(changes) });
      setUsers((current) => current.map((person) => person.id === id ? updated : person));
      setNotice("Account permissions updated.");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update this account."); }
    finally { setBusyId(null); }
  }
  async function saveCrop(event: FormEvent) {
    event.preventDefault(); setSavingCrop(true); setError(""); setNotice("");
    try {
      const created = await api<CropRecord>("/crops/", { method: "POST", body: JSON.stringify(cropForm) });
      setCrops((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSummary((current) => current ? { ...current, active_crops: current.active_crops + (created.active ? 1 : 0), verified_crops: current.verified_crops + (created.active && created.verified ? 1 : 0) } : current);
      setCropForm({ name: "", local_names: "", category: "", guidance_notes: "", source_title: "", source_url: "", verified: false, active: true });
      setNotice("Crop added to the system catalog.");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not save this crop."); }
    finally { setSavingCrop(false); }
  }
  async function toggleCrop(crop: CropRecord, key: "active" | "verified") {
    setError(""); setNotice("");
    try {
      const updated = await api<CropRecord>(`/crops/${crop.id}/`, { method: "PATCH", body: JSON.stringify({ [key]: !crop[key] }) });
      setCrops((current) => current.map((item) => item.id === crop.id ? updated : item));
      setNotice(`${crop.name} ${key === "active" ? (updated.active ? "activated" : "archived") : (updated.verified ? "verified" : "verification removed")}.`);
      void loadAdmin();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update the crop catalog."); }
  }
  const shortcuts: { label: string; detail: string; icon: ReactNode; page: Page }[] = [
    { label: "Farm network", detail: "Review and maintain registered farms", icon: <Tractor size={18} />, page: "farms" },
    { label: "Farmer support", detail: "Respond to open field questions", icon: <MessageCircleQuestion size={18} />, page: "questions" },
    { label: "Platform reports", detail: "Explore system wide farm analytics", icon: <TrendingUp size={18} />, page: "analytics" },
    { label: "Market intelligence", detail: "Review market data and sources", icon: <Store size={18} />, page: "markets" },
  ];
  return <>
    <div className="admin-welcome"><div><div className="eyebrow">AGRICLOUD · CONTROL ROOM</div><h1>System administration</h1><p>Manage farmer accounts, field records, and the verified crop knowledge behind AgriCloud.</p></div><div className="admin-welcome-badge"><ShieldCheck size={20} /><span><strong>Administrator</strong><small>Signed in as {user.first_name || user.username}</small></span></div></div>
    {error && <InlineNotice message={error} />}{notice && <div className="success-message"><Check size={15} />{notice}</div>}
    <div className="admin-stat-grid">
      <MetricCard icon={<Users size={17} />} label="Accounts" value={summary?.users ?? (loading ? "…" : "—")} note={`${summary?.farmers ?? 0} farmer accounts`} tone="green" />
      <MetricCard icon={<Tractor size={17} />} label="Registered farms" value={summary?.farms ?? (loading ? "…" : farms.length)} note="Across all districts" tone="lime" />
      <MetricCard icon={<MessageCircleQuestion size={17} />} label="Open questions" value={summary?.open_questions ?? (loading ? "…" : "—")} note="Awaiting an expert response" tone="orange" />
      <MetricCard icon={<Sprout size={17} />} label="Verified crops" value={summary ? `${summary.verified_crops} / ${summary.active_crops}` : loading ? "…" : "—"} note="Active catalog entries" tone="blue" />
    </div>
    <section className="admin-shortcuts" aria-label="Administration shortcuts">{shortcuts.map((item) => <button className="admin-shortcut" key={item.page} onClick={() => go(item.page)}><span>{item.icon}</span><div><strong>{item.label}</strong><small>{item.detail}</small></div><ChevronRight size={16} /></button>)}</section>
    <section className="panel admin-users-panel"><div className="panel-heading admin-panel-heading"><div><h3>Account directory</h3><p>Assign system roles and manage account access.</p></div><label className="admin-search"><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search people or districts" /></label></div>
      <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Account</th><th>District</th><th>Role</th><th>Status</th><th>Joined</th><th /></tr></thead><tbody>{filteredUsers.map((person) => <tr key={person.id}><td><div className="admin-person"><UserAvatar user={person} className="avatar" /><span><strong>{person.first_name || person.username}{person.last_name ? ` ${person.last_name}` : ""}</strong><small>{person.email || person.username}</small></span></div></td><td>{person.district || "—"}</td><td><select aria-label={`Role for ${person.username}`} value={person.role} disabled={busyId === person.id || person.id === user.id} onChange={(event) => void updateUser(person.id, { role: event.target.value as User["role"] })}><option value="farmer">Farmer</option><option value="extension">Extension worker</option><option value="admin">Administrator</option></select></td><td><span className={`admin-status ${person.is_active ? "is-active" : "is-paused"}`}><i />{person.is_active ? "Active" : "Paused"}</span></td><td>{new Intl.DateTimeFormat("en-UG", { day: "numeric", month: "short", year: "numeric" }).format(new Date(person.date_joined))}</td><td><button className="admin-toggle" disabled={busyId === person.id || person.id === user.id} onClick={() => void updateUser(person.id, { is_active: !person.is_active })}>{person.id === user.id ? "You" : person.is_active ? "Suspend" : "Restore"}</button></td></tr>)}{!filteredUsers.length && <tr><td colSpan={6} className="admin-empty">{loading ? "Loading account directory…" : "No accounts match this search."}</td></tr>}</tbody></table></div>
    </section>
    <div className="admin-catalog-grid"><section className="panel admin-crops-panel"><div className="panel-heading"><div><h3>Crop knowledge catalog</h3><p>Verified entries are available to the planting advisor.</p></div><span className="admin-count-pill">{crops.length} crops</span></div><div className="admin-crop-list">{crops.map((crop) => <div className="admin-crop-row" key={crop.id}><span className="admin-crop-icon"><Sprout size={16} /></span><span className="admin-crop-copy"><strong>{crop.name}</strong><small>{crop.category || "General crop"} · {crop.source_title || "Source not added"}</small></span><button className={`admin-verify ${crop.verified ? "verified" : ""}`} disabled={!crop.verified && (!crop.source_title || !crop.source_url)} title={!crop.verified && !crop.source_url ? "Add a source title and URL before verification" : "Toggle verified status"} onClick={() => void toggleCrop(crop, "verified")}>{crop.verified ? <><Check size={12} /> Verified</> : "Verify"}</button><button className="admin-toggle" onClick={() => void toggleCrop(crop, "active")}>{crop.active ? "Archive" : "Restore"}</button></div>)}{!crops.length && <div className="admin-empty">No crop records yet. Add a crop to start building the catalog.</div>}</div></section>
      <form className="panel admin-add-crop" onSubmit={(event) => void saveCrop(event)}><div className="panel-heading"><div><h3>Add a crop</h3><p>Source details are required before an entry can be verified.</p></div></div><div className="admin-crop-form"><label>Crop name<input required value={cropForm.name} onChange={(event) => setCropForm({ ...cropForm, name: event.target.value })} placeholder="e.g. Cassava" /></label><label>Category<input value={cropForm.category} onChange={(event) => setCropForm({ ...cropForm, category: event.target.value })} placeholder="Root crop" /></label><label>Local names<input value={cropForm.local_names} onChange={(event) => setCropForm({ ...cropForm, local_names: event.target.value })} placeholder="Names used locally" /></label><label>Guidance notes<textarea value={cropForm.guidance_notes} onChange={(event) => setCropForm({ ...cropForm, guidance_notes: event.target.value })} placeholder="Validated growing guidance" rows={3} /></label><label>Source title<input value={cropForm.source_title} onChange={(event) => setCropForm({ ...cropForm, source_title: event.target.value })} placeholder="Agricultural source" /></label><label>Source URL<input type="url" value={cropForm.source_url} onChange={(event) => setCropForm({ ...cropForm, source_url: event.target.value })} placeholder="https://" /></label></div><label className="admin-check-label"><input type="checkbox" checked={cropForm.verified} onChange={(event) => setCropForm({ ...cropForm, verified: event.target.checked })} /> Mark as verified (requires both source fields)</label><button className="button button-primary" disabled={savingCrop}>{savingCrop ? "Adding crop…" : <><Plus size={15} /> Add to catalog</>}</button></form></div>
    <div className="admin-footnote"><ShieldCheck size={14} /><span>Role changes take effect immediately. Your own administrator account is protected, and the system always keeps at least one active administrator.</span></div>
  </>;
}

function MetricCard({ icon, label, value, note, tone }: { icon: ReactNode; label: string; value: ReactNode; note: string; tone: string }) {
  return <div className="metric-card"><div className="metric-top"><span className={`metric-icon ${tone}`}>{icon}</span><button className="more-btn" aria-label={`${label} options`}><Ellipsis size={17} /></button></div><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></div>;
}

function Condition({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="condition-row"><span className="condition-label">{icon}{label}</span><strong>{value}</strong></div>;
}

function ClimateChart({ data }: { data: { date: string; rain: number | null; temp: number | null }[] }) {
  return <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 10, right: 4, bottom: 0, left: -20 }}>
    <defs><linearGradient id="rainFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#16a34a" stopOpacity={0.25} /><stop offset="100%" stopColor="#16a34a" stopOpacity={0} /></linearGradient><linearGradient id="tempFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f59e0b" stopOpacity={0.18} /><stop offset="100%" stopColor="#f59e0b" stopOpacity={0} /></linearGradient></defs>
    <CartesianGrid stroke="#f3f4f6" vertical={false} /><XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={30} /><YAxis yAxisId="rain" tick={{ fill: "#9ca3af", fontSize: 10 }} tickLine={false} axisLine={false} /><YAxis yAxisId="temp" orientation="right" tick={{ fill: "#9ca3af", fontSize: 10 }} tickLine={false} axisLine={false} /><Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: 10, color: "#111827", fontSize: 12 }} labelStyle={{ color: "#6b7280" }} />
    <Area yAxisId="rain" type="monotone" dataKey="rain" name="Rainfall (mm/day)" stroke="#16a34a" strokeWidth={2} fill="url(#rainFill)" connectNulls /><Area yAxisId="temp" type="monotone" dataKey="temp" name="Temperature (°C)" stroke="#f59e0b" strokeWidth={2} fill="url(#tempFill)" connectNulls />
  </AreaChart></ResponsiveContainer></div>;
}

function EmptyState({ title, text, action, loading = false }: { title: string; text: string; action?: ReactNode; loading?: boolean }) {
  return <div className="empty-state">{loading ? <span className="spinner" /> : <span className="empty-icon"><Sprout size={20} /></span>}<strong>{loading ? "Loading observations…" : title}</strong><p>{text}</p>{!loading && action}</div>;
}

function InlineNotice({ message }: { message: string }) { return <div className="inline-notice"><ShieldAlert size={15} />{message}</div>; }

function FarmsPage({ farms, refresh, readOnly }: { farms: Farm[]; refresh: () => Promise<void>; readOnly: boolean }) {
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ name: "", district: "", crop: "", size_hectares: "", latitude: "", longitude: "", soil_type: "unknown" });
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await api<Farm>(editingId ? `/farms/${editingId}/` : "/farms/", { method: editingId ? "PATCH" : "POST", body: JSON.stringify(form) });
      setForm({ name: "", district: "", crop: "", size_hectares: "", latitude: "", longitude: "", soil_type: "unknown" });
      setEditingId(null);
      setAdding(false); await refresh();
    } catch (err) { setError(err instanceof Error ? err.message : "Farm could not be saved."); }
    finally { setBusy(false); }
  }
  function edit(farm: Farm) {
    setForm({ name: farm.name, district: farm.district, crop: farm.crop, size_hectares: farm.size_hectares, latitude: farm.latitude, longitude: farm.longitude, soil_type: farm.soil_type });
    setEditingId(farm.id);
    setAdding(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  async function remove(farm: Farm) {
    if (!window.confirm(`Delete ${farm.name}? This also removes its saved recommendations.`)) return;
    try { await api(`/farms/${farm.id}/`, { method: "DELETE" }); await refresh(); }
    catch (err) { setError(err instanceof Error ? err.message : "Farm could not be deleted."); }
  }
  return <>
    <PageHeading eyebrow="FIELD REGISTER" title={readOnly ? "Farmer farm register" : "My farms"} description={readOnly ? "Review registered farm locations and reported field details." : "Keep your farm locations, crops and field details in one place."} action={!readOnly && <button className="button button-primary" onClick={() => { setAdding((value) => !value); setEditingId(null); setForm({ name: "", district: "", crop: "", size_hectares: "", latitude: "", longitude: "", soil_type: "unknown" }); }}><Plus size={16} /> Add a farm</button>} />
    {error && <InlineNotice message={error} />}
    {adding && !readOnly && <form className="panel farm-form" onSubmit={submit}><div className="panel-heading"><div><h3>{editingId ? "Edit farm details" : "New farm details"}</h3><p>Coordinates help retrieve location-specific NASA POWER observations.</p></div><button type="button" className="icon-btn" onClick={() => { setAdding(false); setEditingId(null); }} aria-label="Close form"><X size={17} /></button></div><div className="form-grid">
      <label>Farm name<input required maxLength={120} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Green Valley" /></label>
      <label>District<input required maxLength={100} value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} placeholder="e.g. Wakiso" /></label>
      <label>Main crop<input value={form.crop} maxLength={100} onChange={(e) => setForm({ ...form, crop: e.target.value })} placeholder="e.g. Maize" /></label>
      <label>Size (hectares)<input required type="number" min="0.01" step="0.01" value={form.size_hectares} onChange={(e) => setForm({ ...form, size_hectares: e.target.value })} placeholder="1.5" /></label>
      <label>Latitude<input required type="number" min="-1.5" max="4.2" step="any" value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} placeholder="e.g. 0.3476  (Uganda: -1.5 to 4.2)" title="Uganda latitude range: -1.5 (south) to 4.2 (north)" /></label>
      <label>Longitude<input required type="number" min="29.5" max="35.1" step="any" value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} placeholder="e.g. 32.5825  (Uganda: 29.5 to 35.1)" title="Uganda longitude range: 29.5 (west) to 35.1 (east)" /></label>
      <label>Soil type<select value={form.soil_type} onChange={(e) => setForm({ ...form, soil_type: e.target.value })}><option value="unknown">Not specified</option><option value="clay">Clay</option><option value="loam">Loam</option><option value="sandy">Sandy</option><option value="volcanic">Volcanic</option></select></label>
    </div><div className="form-actions"><span>Coordinates must be within Uganda (Lat: -1.5 to 4.2, Lon: 29.5 to 35.1). Get them from Google Maps by right-clicking your farm location.</span><button className="button button-primary" disabled={busy}>{busy ? "Saving…" : editingId ? "Save changes" : "Save farm"}</button></div></form>}
    <div className="section-title-row"><div><h2>Registered locations</h2><p>{farms.length} farm{farms.length === 1 ? "" : "s"} in your workspace</p></div></div>
    {farms.length ? <div className="farm-card-grid">{farms.map((farm, index) => <article className="farm-card" key={farm.id}><div className={`farm-card-art art-${index % 3}`}><span className="art-chip"><MapPin size={13} /> {farm.district}</span><span className="art-orbit"><Leaf size={23} /></span></div><div className="farm-card-body"><div className="farm-card-top"><div><h3>{farm.name}</h3><p>{farm.crop || "No crop recorded"} · {farm.soil_type}</p>{readOnly && <p>Farmer: {farm.owner_name || "Name not provided"}</p>}</div>{!readOnly && <div className="farm-actions"><button className="delete-btn" onClick={() => edit(farm)} aria-label={`Edit ${farm.name}`}><Pencil size={14} /></button><button className="delete-btn" onClick={() => void remove(farm)} aria-label={`Delete ${farm.name}`}><X size={16} /></button></div>}</div><div className="farm-card-meta"><span><Sprout size={14} /> {farm.size_hectares} ha</span><span><MapPin size={14} /> {Number(farm.latitude).toFixed(3)}, {Number(farm.longitude).toFixed(3)}</span></div><div className="farm-card-footer"><span><span className="live-dot" /> Location saved</span><span>NASA POWER ready</span></div></div></article>)}</div> : <div className="panel large-empty"><EmptyState title={readOnly ? "No farmer farms registered" : "Your farm register is empty"} text={readOnly ? "Registered farms will be available for climate monitoring when farmers create records." : "Add a farm with its location to start exploring climate conditions and planting guidance."} action={!readOnly && <button className="button button-primary" onClick={() => setAdding(true)}><Plus size={15} /> Add your first farm</button>} /></div>}
  </>;
}

function WeatherPage({ farms }: { farms: Farm[] }) {
  const [selectedId, setSelectedId] = useState<number | "">(farms[0]?.id ?? "");
  const [weather, setWeather] = useState<Weather | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [period, setPeriod] = useState(30);
  const [liveWeather, setLiveWeather] = useState<LiveWeather | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState("");
  const [liveRefreshCooldown, setLiveRefreshCooldown] = useState(0);
  useEffect(() => { if (!selectedId && farms.length) setSelectedId(farms[0].id); }, [farms, selectedId]);
  async function loadLiveWeather() {
    if (!selectedId) return;
    setLiveLoading(true); setLiveError("");
    try { setLiveWeather(await api<LiveWeather>(`/weather/current/?farm_id=${selectedId}`)); }
    catch (err) { setLiveError(err instanceof Error ? err.message : "Could not load current weather."); }
    finally { setLiveLoading(false); }
  }
  async function refreshLiveWeather() {
    if (liveRefreshCooldown > 0 || liveLoading) return;
    await loadLiveWeather();
    // 60-second cooldown after a manual refresh to protect the rate limit.
    setLiveRefreshCooldown(60);
    const tick = window.setInterval(() => {
      setLiveRefreshCooldown((prev) => {
        if (prev <= 1) { window.clearInterval(tick); return 0; }
        return prev - 1;
      });
    }, 1000);
  }
  useEffect(() => {
    if (!selectedId) {
      setLiveWeather(null);
      return;
    }

    setLiveWeather(null);
    void loadLiveWeather();
  }, [selectedId]);
  async function load() {
    if (!selectedId) return;
    setLoading(true); setError("");
    const end = new Date(); end.setDate(end.getDate() - 1);
    const start = new Date(end); start.setDate(start.getDate() - period);
    const fmt = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    try { setWeather(await api<Weather>(`/weather/?farm_id=${selectedId}&start=${fmt(start)}&end=${fmt(end)}`)); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not load historical observations."); }
    finally { setLoading(false); }
  }
  useEffect(() => { if (selectedId) void load(); }, [selectedId, period]);
  const chartData = useMemo(() => weather?.observations.map((day) => ({ date: day.date.slice(5), rain: day.values.PRECTOTCORR?.value ?? null, temp: day.values.T2M?.value ?? null })) ?? [], [weather]);
  const selectedFarm = farms.find((farm) => farm.id === Number(selectedId));
  return <>
    <PageHeading eyebrow="LIVE CONDITIONS · HISTORICAL DATA" title="Weather intelligence" description="See current model-based weather and a 7-day forecast separately from NASA POWER historical observations." action={<div className="weather-controls"><select aria-label="Select farm" value={selectedId} onChange={(e) => setSelectedId(Number(e.target.value))}>{farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name} · {farm.district}</option>)}</select><select aria-label="Observation period" value={period} onChange={(e) => setPeriod(Number(e.target.value))}><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={365}>Last year</option></select></div>} />
    {farms.length > 0 && <section className="panel current-weather-panel">
      <div className="panel-heading">
        <div><div className="eyebrow">CURRENT CONDITIONS · MODEL ESTIMATE</div><h3>{selectedFarm?.name || "Selected farm"} · {selectedFarm?.district || "Uganda"}</h3><p>{liveWeather ? `Updated ${liveWeather.current.time.replace("T", " ")} · ${liveWeather.timezone}` : "Weather conditions and seven-day outlook"}</p></div>
        <button className="button button-secondary button-small" disabled={liveLoading || liveRefreshCooldown > 0} onClick={() => void refreshLiveWeather()}>{liveLoading ? "Refreshing…" : liveRefreshCooldown > 0 ? `Retry in ${liveRefreshCooldown}s` : "Refresh current weather"}</button>
      </div>
      {liveError && <InlineNotice message={liveError} />}
      {liveWeather ? <>
        <div className="current-weather-overview">
          <div className="current-weather-summary"><span className="current-weather-icon"><CloudSun size={24} /></span><div><span>Current temperature</span><strong>{liveWeather.current.temperature_c === null ? "—" : `${liveWeather.current.temperature_c.toFixed(1)}°C`}</strong><p>{liveWeather.current.condition}{liveWeather.current.feels_like_c === null ? "" : ` · Feels like ${liveWeather.current.feels_like_c.toFixed(1)}°C`}</p></div></div>
          <div className="current-weather-stats">
            <div className="current-weather-stat"><Activity size={15} /><span>Humidity</span><strong>{liveWeather.current.relative_humidity_pct === null ? "—" : `${liveWeather.current.relative_humidity_pct.toFixed(0)}%`}</strong></div>
            <div className="current-weather-stat"><Droplets size={15} /><span>Precipitation</span><strong>{liveWeather.current.precipitation_mm === null ? "—" : `${liveWeather.current.precipitation_mm.toFixed(1)} mm`}</strong></div>
            <div className="current-weather-stat"><Wind size={15} /><span>Wind speed</span><strong>{liveWeather.current.wind_speed_kmh === null ? "—" : `${liveWeather.current.wind_speed_kmh.toFixed(0)} km/h`}</strong></div>
            <div className="current-weather-stat"><CloudSun size={15} /><span>Cloud cover</span><strong>{liveWeather.current.cloud_cover_pct === null ? "—" : `${liveWeather.current.cloud_cover_pct.toFixed(0)}%`}</strong></div>
          </div>
        </div>
        <div className="forecast-heading"><h4>7-day forecast</h4><span>Daily model forecast · local farm time</span></div>
        <div className="forecast-grid">{liveWeather.daily_forecast.map((day) => <article className="forecast-day" key={day.date}><strong>{forecastDayLabel(day.date)}</strong><span>{day.condition}</span><div className="forecast-temperatures"><b>{day.temperature_max_c === null ? "—" : `${day.temperature_max_c.toFixed(0)}°`}</b><small>{day.temperature_min_c === null ? "—" : `${day.temperature_min_c.toFixed(0)}°`}</small></div><small>Rain chance {day.precipitation_probability_max_pct === null ? "—" : `${day.precipitation_probability_max_pct.toFixed(0)}%`}</small><small>{day.precipitation_sum_mm === null ? "—" : `${day.precipitation_sum_mm.toFixed(1)} mm`} rain</small></article>)}</div>
        <div className="current-weather-note">Current conditions are model estimates, not readings from a local weather station. Farm coordinates are sent to Open-Meteo to retrieve this data. <a href={liveWeather.attribution_url} target="_blank" rel="noreferrer">Weather data by Open-Meteo</a>.</div>
      </> : !liveError && <div className="live-weather-empty">{liveLoading ? "Loading current conditions and forecast…" : "Current weather is not available right now."}</div>}
    </section>}
    <div className="data-banner"><span className="source-dot" /><strong>Historical observations</strong><span>NASA POWER · Daily point data</span><span className="banner-separator">|</span><span>Not a forecast</span></div>
    {error && <InlineNotice message={error} />}
    {farms.length ? <><div className="panel climate-panel full-panel"><div className="panel-heading"><div><h3>Rainfall & air temperature</h3><p>{weather ? `${weather.period.start} to ${weather.period.end} · ${weather.observations.length} observation days` : "Waiting for climate observations"}</p></div><button className="button button-secondary button-small" disabled={loading} onClick={() => void load()}>{loading ? "Updating…" : "Refresh data"}</button></div>{chartData.length ? <ClimateChart data={chartData} /> : <EmptyState loading={loading} title="No observations loaded" text={error || "NASA POWER data will appear here when available."} />}{weather && <div className="chart-legend"><span><i className="legend-rain" /> Precipitation <small>mm/day</small></span><span><i className="legend-temp" /> Temperature <small>°C</small></span><span className="source-label">Source: NASA POWER</span></div>}</div><div className="data-notes"><div className="note-icon"><Activity size={18} /></div><div><strong>Understanding these observations</strong><p>POWER daily point values are gridded satellite and model-informed estimates for this location. They describe the selected historical period and should not be interpreted as a local station reading or forecast.</p></div></div></> : <div className="panel large-empty"><EmptyState title="Add a farm to explore weather" text="Climate data is requested for saved farm coordinates—no sample or simulated live readings are shown here." /></div>}
  </>;
}

function AdvisorPage({ farms }: { farms: Farm[] }) {
  const [farmId, setFarmId] = useState(farms[0]?.id ?? "");
  const [crop, setCrop] = useState(farms[0]?.crop ?? "");
  const [date, setDate] = useState("");
  const [result, setResult] = useState<Recommendation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError(""); setResult(null);
    try { setResult(await api<Recommendation>("/recommendations/", { method: "POST", body: JSON.stringify({ farm_id: farmId, crop, planting_date: date || null }) })); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not build guidance."); }
    finally { setBusy(false); }
  }
  return <>
    <PageHeading eyebrow="EXPLAINABLE · CLIMATE-INFORMED" title="Planting advisor" description="Get cautious, transparent planning guidance grounded in your farm details and available NASA observations." />
    <div className="advisor-layout"><form className="panel advisor-form" onSubmit={submit}><div className="form-heading-icon"><Sprout size={19} /></div><h3>Tell us about your plan</h3><p>We use historical conditions as context—not as a prediction of future rainfall.</p><label>Choose a farm<select required value={farmId} onChange={(e) => setFarmId(Number(e.target.value))}><option value="">Select a farm</option>{farms.map((farm) => <option value={farm.id} key={farm.id}>{farm.name} · {farm.district}</option>)}</select></label><label>Crop to consider<input required maxLength={100} value={crop} onChange={(e) => setCrop(e.target.value)} placeholder="e.g. beans, maize, cassava" /></label><label>Intended planting date <span className="optional">(optional)</span><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>{error && <InlineNotice message={error} />}<button className="button button-primary full-button" disabled={busy || !farms.length}>{busy ? <><span className="spinner small" /> Reviewing conditions…</> : <><Sprout size={16} /> Generate guidance</>}</button><small className="privacy-note"><ShieldAlert size={13} /> For planning support only. Confirm with a local extension worker.</small></form>
      <div className="advisor-result">{result ? <div className="panel guidance-card"><div className="panel-heading"><div><div className="eyebrow">YOUR FARMING GUIDANCE</div><h3>{result.crop} · {farms.find((farm) => farm.id === Number(farmId))?.district}</h3></div><span className="status-pill"><span /> Advisory</span></div><div className="guidance-copy"><div className="guidance-badge"><Sprout size={17} /></div><p>{result.guidance}</p></div><h4>What informed this guidance</h4><ul className="basis-list">{result.basis.map((item, index) => <li key={index}><Check size={15} />{item}</li>)}</ul>{result.risks.length > 0 && <><h4 className="risk-title"><ShieldAlert size={15} /> Conditions to keep in mind</h4><ul className="risk-list">{result.risks.map((item, index) => <li key={index}>{item}</li>)}</ul></>}<div className="advice-disclaimer">General rules-based information only. The system does not establish a planting date, predict yield, or replace district-specific agronomic advice.</div></div> : <div className="panel advisor-placeholder"><div className="placeholder-art"><div className="placeholder-orbit orbit-one" /><div className="placeholder-orbit orbit-two" /><div className="placeholder-core"><Sprout size={31} /></div></div><h3>Guidance with its reasoning</h3><p>Your result will show the climate observations and farm details considered, along with any limitations or risks.</p><div className="placeholder-list"><span><Check size={14} /> Historical data, clearly labeled</span><span><Check size={14} /> Transparent rules, not a mystery score</span><span><Check size={14} /> Uncertainty and risks made visible</span></div></div>}</div>
    </div>
  </>;
}

function CropDiseasePage() {
  const [crop, setCrop] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState<CropDiseaseResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!image) { setPreview(""); return; }
    const url = URL.createObjectURL(image);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!image) return;
    setBusy(true); setError(""); setResult(null);
    const data = new FormData();
    data.append("crop", crop);
    data.append("image", image);
    try { setResult(await api<CropDiseaseResult>("/crop-disease/", { method: "POST", body: data })); }
    catch (err) { setError(err instanceof Error ? err.message : "The crop image could not be analyzed."); }
    finally { setBusy(false); }
  }
  return <>
    <PageHeading eyebrow="COMPUTER VISION · ADVISORY" title="Crop disease detection" description="Upload a clear crop photo for an AI-assisted check of visible signs and cautious next steps." />
    <div className="feature-layout">
      <form className="panel feature-form" onSubmit={(event) => void submit(event)}>
        <div className="form-heading-icon"><Bug size={19} /></div><h3>Check a crop image</h3>
        <p>Photograph the affected leaf or plant in good light. Include only the crop in the frame where possible.</p>
        <label>Crop name<input required maxLength={100} value={crop} onChange={(event) => setCrop(event.target.value)} placeholder="e.g. maize, beans, cassava" /></label>
        <label className="upload-field">Crop image
          <input required type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => { setImage(event.target.files?.[0] ?? null); setResult(null); setError(""); }} />
          <span className="upload-prompt"><Upload size={18} /><strong>{image?.name || "Choose or take a crop photo"}</strong><small>JPEG, PNG or WebP · Up to 5 MB</small></span>
        </label>
        {preview && <img className="crop-image-preview" src={preview} alt="Selected crop for visual assessment" />}
        {error && <InlineNotice message={error} />}
        <button className="button button-primary full-button" disabled={busy || !image || !crop.trim()}>{busy ? <><span className="spinner small" /> Reviewing image…</> : <><Bug size={15} /> Analyze crop image</>}</button>
        <div className="feature-privacy-note"><ShieldAlert size={14} /> Your image is sent to the AI provider configured by the service operator for analysis. It is not saved by AgriCloud.</div>
      </form>
      <div className="feature-result">
        {result ? <article className="panel disease-result">
          <div className="panel-heading"><div><div className="eyebrow">POSSIBLE VISUAL MATCH</div><h3>{result.possible_disease}</h3><p>{result.crop} · AI image assessment</p></div><Bug size={18} className="panel-heading-icon" /></div>
          <div className="confidence-head"><span>Model-reported confidence</span><strong>{result.confidence_pct.toFixed(1)}%</strong></div>
          <div className="confidence-meter" role="meter" aria-label="Model-reported confidence" aria-valuemin={0} aria-valuemax={100} aria-valuenow={result.confidence_pct}><i style={{ width: `${Math.min(100, Math.max(0, result.confidence_pct))}%` }} /></div>
          <h4>{result.analysis_type === "classifier" ? "Classifier output" : "Visible signs reported"}</h4>
          {result.visual_signs.length ? <ul className="basis-list">{result.visual_signs.map((sign, index) => <li key={index}><Check size={14} />{sign}</li>)}</ul> : <p className="feature-copy">{result.analysis_type === "classifier" ? "This classifier reports a class and score, not individual symptoms or lesions." : "No clear visual signs were returned."}</p>}
          <div className="disease-advice"><section><h4>Suggested next steps</h4><p>{result.treatment}</p></section><section><h4>Prevention</h4><p>{result.prevention}</p></section></div>
          <div className="advice-disclaimer">{result.disclaimer}</div>
        </article> : <div className="panel feature-placeholder"><span className="placeholder-core"><Bug size={26} /></span><h3>Image-based crop check</h3><p>After analysis, possible conditions, confidence, visible signs, and general care recommendations will appear here.</p><div className="placeholder-list"><span><Check size={14} /> Confidence shown with uncertainty</span><span><Check size={14} /> Practical prevention suggestions</span><span><Check size={14} /> No pesticide rates or confirmed diagnosis</span></div></div>}
      </div>
    </div>
  </>;
}

function IrrigationPage({ farms }: { farms: Farm[] }) {
  const [farmId, setFarmId] = useState<number | "">(farms[0]?.id ?? "");
  const [crop, setCrop] = useState(farms[0]?.crop ?? "");
  const [stage, setStage] = useState("mid");
  const [soilMoisture, setSoilMoisture] = useState("");
  const [result, setResult] = useState<IrrigationPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!farmId && farms.length) {
      setFarmId(farms[0].id);
      setCrop(farms[0].crop);
    }
  }, [farmId, farms]);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setResult(null);
    try {
      setResult(await api<IrrigationPlan>("/irrigation/", {
        method: "POST",
        body: JSON.stringify({
          farm_id: farmId,
          crop,
          stage,
          ...(soilMoisture === "" ? {} : { soil_moisture_pct: Number(soilMoisture) }),
        }),
      }));
    } catch (err) { setError(err instanceof Error ? err.message : "The irrigation plan could not be calculated."); }
    finally { setBusy(false); }
  }
  return <>
    <PageHeading eyebrow="7-DAY WATER BALANCE · WEATHER MODEL" title="Smart irrigation" description="Estimate crop water demand and plan irrigation using your farm area, crop stage, and local weather forecast." />
    <div className="advisor-layout irrigation-layout">
      <form className="panel advisor-form" onSubmit={(event) => void submit(event)}>
        <div className="form-heading-icon"><Droplets size={19} /></div><h3>Set field conditions</h3>
        <p>Forecast-based water estimates are indicative; sensor readings and local advice take precedence.</p>
        <label>Choose a farm<select required value={farmId} onChange={(event) => { const id = Number(event.target.value); setFarmId(id); setCrop(farms.find((farm) => farm.id === id)?.crop ?? ""); setResult(null); }}><option value="">Select a farm</option>{farms.map((farm) => <option value={farm.id} key={farm.id}>{farm.name} · {farm.district}</option>)}</select></label>
        <label>Crop<input required maxLength={100} value={crop} onChange={(event) => setCrop(event.target.value)} placeholder="e.g. maize, beans, rice" /></label>
        <label>Growth stage<select value={stage} onChange={(event) => setStage(event.target.value)}><option value="initial">Initial</option><option value="development">Development</option><option value="mid">Mid-season</option><option value="late">Late-season</option></select></label>
        <label>Soil moisture <span className="optional">(optional farmer estimate, %)</span><input type="number" min="0" max="100" step="1" value={soilMoisture} onChange={(event) => setSoilMoisture(event.target.value)} placeholder="Not measured" /></label>
        {error && <InlineNotice message={error} />}
        <button className="button button-primary full-button" disabled={busy || !farms.length || !crop.trim()}>{busy ? <><span className="spinner small" /> Calculating forecast…</> : <><Droplets size={15} /> Calculate water plan</>}</button>
        <small className="privacy-note"><ShieldAlert size={13} /> Weather estimates are not on-farm sensor measurements.</small>
      </form>
      <div className="feature-result">
        {result ? <>
          <div className="metric-grid irrigation-metrics">
            <MetricCard icon={<Sun size={16} />} label="Crop water need" value={`${result.totals.crop_water_need_mm.toFixed(1)} mm`} note="7-day estimate · ETc" tone="lime" />
            <MetricCard icon={<CloudSun size={16} />} label="Effective rainfall" value={`${result.totals.effective_rainfall_mm.toFixed(1)} mm`} note="Estimated from forecast rain" tone="blue" />
            <MetricCard icon={<Droplets size={16} />} label="Net irrigation" value={`${result.totals.net_irrigation_need_mm.toFixed(1)} mm`} note={`${result.totals.net_irrigation_volume_liters.toLocaleString()} L for ${result.farm_area_hectares} ha`} tone="green" />
          </div>
          <section className="panel irrigation-result">
            <div className="panel-heading"><div><div className="eyebrow">SUGGESTED SCHEDULE</div><h3>{result.crop} · {result.farm.name}</h3><p>Crop coefficient {result.crop_coefficient} · {result.stage} stage</p></div><CalendarDays size={18} className="panel-heading-icon" /></div>
            {result.schedule.length ? <div className="irrigation-schedule">{result.schedule.map((item) => <article className="schedule-row" key={item.date}><span className="schedule-icon"><Droplets size={15} /></span><div><strong>{forecastDayLabel(item.date)}</strong><small>{item.depth_mm.toFixed(1)} mm net water</small></div><b>{item.volume_liters.toLocaleString()} L</b></article>)}</div> : <div className="schedule-empty">No irrigation trigger in the forecast window. Keep checking field conditions, especially if rainfall differs from the forecast.</div>}
            <h4>Daily forecast balance</h4>
            <div className="irrigation-days">{result.daily.map((day) => <div className="irrigation-day" key={day.date}><strong>{forecastDayLabel(day.date)}</strong><span>ETc {day.crop_water_need_mm.toFixed(1)} mm</span><span>Rain {day.rainfall_mm.toFixed(1)} mm</span><b>{day.net_irrigation_need_mm.toFixed(1)} mm net</b></div>)}</div>
            {result.soil_moisture_note && <p className="soil-estimate-note">Entered soil moisture: {result.soil_moisture_pct}% · {result.soil_moisture_status} · {result.soil_moisture_note}</p>}
            <div className="advice-disclaimer">{result.methodology} <a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Weather data by Open-Meteo</a>.</div>
          </section>
        </> : farms.length ? <div className="panel feature-placeholder"><span className="placeholder-core"><Droplets size={26} /></span><h3>Forecast-led water planning</h3><p>Select a farm and crop to estimate reference evapotranspiration, crop demand, effective rainfall, and net water needs.</p><div className="placeholder-list"><span><Check size={14} /> Adjusted for crop and growth stage</span><span><Check size={14} /> Farm area translated to litres</span><span><Check size={14} /> Seven-day rainfall factored in</span></div></div> : <div className="panel feature-placeholder"><span className="placeholder-core"><Droplets size={26} /></span><h3>Add a farm to get started</h3><p>Farm coordinates, area, crop, and soil type are used to prepare a forecast-based irrigation guide.</p></div>}
      </div>
    </div>
  </>;
}

function MapPage({ farms }: { farms: Farm[] }) {
  return <>
    <PageHeading eyebrow="OPENSTREETMAP" title="Farm map" description="See registered farm locations across Uganda. Map tiles are provided by OpenStreetMap." />
    {farms.length ? <div className="panel map-panel"><FarmMap farms={farms} /><div className="map-legend"><span className="map-pip" /> Your registered farms <span className="map-count">{farms.length} location{farms.length === 1 ? "" : "s"}</span></div></div> : <div className="panel large-empty"><EmptyState title="No mapped farms yet" text="Register farm coordinates to see your growing locations on the map." /></div>}
  </>;
}

function FarmMap({ farms, compact = false }: { farms: Farm[]; compact?: boolean }) {
  const validFarms = farms.filter((f) => {
    const lat = Number(f.latitude), lon = Number(f.longitude);
    return lat >= -1.5 && lat <= 4.2 && lon >= 29.5 && lon <= 35.1;
  });
  const displayFarms = validFarms.length > 0 ? validFarms : farms;
  const center: [number, number] = displayFarms.length
    ? [Number(displayFarms[0].latitude), Number(displayFarms[0].longitude)]
    : [1.3733, 32.2903];
  return <MapContainer center={center} zoom={displayFarms.length === 1 ? 12 : 7} scrollWheelZoom={!compact} className={`leaflet-map${compact ? " dashboard-leaflet-map" : ""}`}>
    <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    {farms.map((farm) => <CircleMarker key={farm.id} center={[Number(farm.latitude), Number(farm.longitude)]} radius={9} pathOptions={{ color: "#09241d", fillColor: "#2cde91", fillOpacity: 0.9, weight: 3 }}><Popup><strong>{farm.name}</strong><br />{farm.district} · {farm.crop || "Crop unspecified"}<br />{farm.size_hectares} ha</Popup></CircleMarker>)}
  </MapContainer>;
}

function AssistantPage({ user, farms, onAskExtension }: { user: User; farms: Farm[]; onAskExtension: () => void }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string; sources?: string[]; grounded?: boolean }[]>([
    { role: "assistant", text: "Ask a farming question or follow up naturally. I'll use verified sources when available and clearly label general guidance when they aren't. Your saved farm and account details are not sent to the AI provider." },
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function send(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    const asked = question.trim();
    const history = messages.slice(1).slice(-8).map((item) => ({ role: item.role, content: item.text }));
    setMessages((items) => [...items, { role: "user", text: asked }]);
    setQuestion("");
    setBusy(true);
    setError("");
    try {
      const reply = await api<{ answer: string; sources: string[]; grounded: boolean }>("/assistant/chat/", {
        method: "POST",
        body: JSON.stringify({ message: asked, history }),
      });
      setMessages((items) => [...items, { role: "assistant", text: reply.answer, sources: reply.sources, grounded: reply.grounded }]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "The assistant could not respond.";
      setError(message);
      setMessages((items) => [...items, { role: "assistant", text: "I couldn't reach the assistant right now. Please try again later or check with your local extension worker." }]);
    } finally { setBusy(false); }
  }
  return <><PageHeading eyebrow="FARMING SUPPORT" title="AI farming assistant" description="Chat naturally, ask follow-up questions, and get clear notes when an answer isn't backed by a verified local source." /><div className="assistant-layout"><section className="panel chat-panel"><div className="chat-header"><div className="assistant-avatar"><Sprout size={18} /></div><div><strong>AgriCloud field assistant</strong><span><i /> Sources when available</span></div><span className="status-pill">Conversational support</span></div><div className="chat-messages">{messages.map((message, index) => <div key={index} className={`chat-message ${message.role}`}><span className="chat-avatar">{message.role === "assistant" ? <Sprout size={14} /> : "You"}</span><div><p>{message.text}</p>{message.sources?.length ? <div className="chat-sources">Sources: {message.sources.join(" · ")}</div> : message.role === "assistant" && message.grounded === false ? <div className="chat-sources chat-unsourced">No verified source matched · general guidance, not locally verified.</div> : null}</div></div>)}{busy && <div className="chat-loading"><span className="spinner small" /> Thinking…</div>}</div>{error && <div className="chat-error"><ShieldAlert size={13} />{error}</div>}<form className="chat-input" onSubmit={(event) => void send(event)}><input aria-label="Ask a farming question" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about crops, planting, or soil…" /><button className="button button-primary" disabled={!question.trim() || busy}>Send <ChevronRight size={15} /></button></form><div className="chat-safety"><ShieldAlert size={13} /> Your message goes to the configured AI provider. Do not include personal or sensitive details; saved farm and account data are never sent.</div></section><aside className="panel assistant-context"><h3>Your farm context</h3><p>Farm records remain private to your workspace.</p>{farms.length ? farms.map((farm) => <div className="context-row" key={farm.id}><span className="farm-glyph glyph-0"><Leaf size={16} /></span><div><strong>{farm.name}</strong><small>{farm.district} · {farm.crop || "Crop not specified"}</small></div></div>) : <div className="context-empty">Register a farm to see your local context in this workspace.</div>}<div className="context-note"><strong>Language support</strong><span>English interface. Luganda and other local languages should be enabled with validated agricultural content.</span></div>{user.role === "farmer" && <button className="outlook-link extension-link" onClick={onAskExtension}>Ask an extension worker <ChevronRight size={14} /></button>}</aside></div></>;
}

function QuestionsPage({ user, farms }: { user: User; farms: Farm[] }) {
  const [questions, setQuestions] = useState<FarmQuestion[]>([]);
  const [farmId, setFarmId] = useState<number | "">(farms[0]?.id ?? "");
  const [questionText, setQuestionText] = useState("");
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const farmer = user.role === "farmer";

  async function loadQuestions() {
    try { setQuestions(await api<FarmQuestion[]>("/questions/")); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not load questions."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void loadQuestions(); }, []);
  useEffect(() => { if (!farmId && farms.length) setFarmId(farms[0].id); }, [farmId, farms]);

  async function submitQuestion(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      const created = await api<FarmQuestion>("/questions/", { method: "POST", body: JSON.stringify({ farm: farmId, question: questionText }) });
      setQuestions((items) => [created, ...items]);
      setQuestionText("");
    } catch (err) { setError(err instanceof Error ? err.message : "Question could not be submitted."); }
    finally { setBusy(false); }
  }

  async function respond(event: FormEvent, questionId: number) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      const updated = await api<FarmQuestion>(`/questions/${questionId}/respond/`, { method: "POST", body: JSON.stringify({ answer: answers[questionId] ?? "" }) });
      setQuestions((items) => items.map((item) => item.id === updated.id ? updated : item));
      setAnswers((items) => ({ ...items, [questionId]: "" }));
    } catch (err) { setError(err instanceof Error ? err.message : "Reply could not be sent."); }
    finally { setBusy(false); }
  }

  return <>
    <PageHeading eyebrow={farmer ? "LOCAL EXTENSION SUPPORT" : "EXTENSION WORKER PORTAL"} title={farmer ? "Ask an extension worker" : "Farmer questions"} description={farmer ? "Send a question to an extension worker for your registered farm." : "Review farmer-submitted questions and share advisory replies."} />
    {error && <InlineNotice message={error} />}
    {farmer && <form className="panel question-form" onSubmit={(event) => void submitQuestion(event)}>
      <h3>Submit a farm question</h3><p>Your question is visible to authorized extension workers and administrators.</p>
      <label>Farm<select required value={farmId} onChange={(event) => setFarmId(Number(event.target.value))}><option value="">Select a farm</option>{farms.map((farm) => <option value={farm.id} key={farm.id}>{farm.name} · {farm.district}</option>)}</select></label>
      <label>Your question<textarea required maxLength={2000} value={questionText} onChange={(event) => setQuestionText(event.target.value)} placeholder="Describe what you would like guidance on…" rows={4} /></label>
      <button className="button button-primary" disabled={busy || !farms.length || !questionText.trim()}><MessageCircleQuestion size={15} />{busy ? "Sending…" : "Send question"}</button>
    </form>}
    <div className="section-title-row"><div><h2>{farmer ? "Your questions" : "Incoming questions"}</h2><p>{questions.length} record{questions.length === 1 ? "" : "s"}</p></div></div>
    {loading ? <div className="panel large-empty"><EmptyState loading title="Loading questions" text="Retrieving authorized question records." /></div>
      : questions.length ? <div className="question-list">{questions.map((item) => <article className="panel question-card" key={item.id}>
        <div className="question-meta"><span className={`question-status ${item.status}`}>{item.status === "open" ? "Awaiting response" : "Responded"}</span><span>{item.farm_name} · {item.district}</span><time>{new Date(item.created_at).toLocaleDateString()}</time></div>
        {!farmer && <div className="question-author">From {item.asked_by_name || "Farmer"}</div>}
        <p className="question-copy">{item.question}</p>
        {item.answer ? <div className="question-answer"><strong>Extension response{item.answered_by_name ? ` · ${item.answered_by_name}` : ""}</strong><p>{item.answer}</p></div>
          : !farmer && <form className="question-reply" onSubmit={(event) => void respond(event, item.id)}><label htmlFor={`answer-${item.id}`}>Write a response</label><textarea id={`answer-${item.id}`} required maxLength={4000} rows={3} value={answers[item.id] ?? ""} onChange={(event) => setAnswers((items) => ({ ...items, [item.id]: event.target.value }))} placeholder="Share practical guidance and note what the farmer should verify locally…" /><button className="button button-primary button-small" disabled={busy || !(answers[item.id] ?? "").trim()}>{busy ? "Sending…" : "Send reply"}</button></form>}
      </article>)}</div>
        : <div className="panel large-empty"><EmptyState title={farmer ? "No questions submitted yet" : "No farmer questions yet"} text={farmer ? "Submit a farm question and an extension worker can follow up." : "Farmer questions will appear here for extension review."} /></div>}
  </>;
}

function AlertsPage() {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [farmId, setFarmId] = useState<number | "">("");
  const [riskData, setRiskData] = useState<{
    period: { start: string; end: string };
    risks: { type: string; level: string; observed: number; unit: string; threshold: string; action: string }[];
    screening_available: boolean;
    coverage: { expected_days: number; rainfall_observations: number; temperature_observations: number };
    methodology: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.allSettled([api<Farm[]>("/farms/"), api<NotificationItem[]>("/notifications/")]).then(([farmResult, notificationResult]) => {
      if (farmResult.status === "fulfilled") { setFarms(farmResult.value); if (farmResult.value.length) setFarmId(farmResult.value[0].id); }
      else setError(farmResult.reason instanceof Error ? farmResult.reason.message : "Could not load farms.");
      if (notificationResult.status === "fulfilled") setNotifications(notificationResult.value);
      else setError(notificationResult.reason instanceof Error ? notificationResult.reason.message : "Could not load notifications.");
    }).finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!farmId) { setRiskData(null); return; }
    let active = true;
    setLoading(true); setError("");
    api<typeof riskData>(`/risks/?farm_id=${farmId}`).then((data) => { if (active) setRiskData(data); }).catch((err: Error) => { if (active) setError(err.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [farmId]);
  async function markRead(notificationId: number) {
    try {
      const updated = await api<NotificationItem>(`/notifications/${notificationId}/read/`, { method: "POST" });
      setNotifications((items) => items.map((item) => item.id === updated.id ? updated : item));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update notification."); }
  }
  return <>
    <PageHeading eyebrow="MONITORING · HISTORICAL INDICATORS" title="Climate risk alerts" description="Preliminary rule-based screens against recent observations. Confirm any concern locally."
      action={farms.length ? <select className="risk-farm-select" aria-label="Select farm for risk screening" value={farmId} onChange={(e) => setFarmId(Number(e.target.value))}>{farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name} · {farm.district}</option>)}</select> : undefined} />
    {error && <InlineNotice message={error} />}
    {farms.length > 0 && <>
      <div className="data-banner"><span className="source-dot" /><strong>Screening window</strong><span>{riskData ? `${riskData.period.start} — ${riskData.period.end}` : "Last 30 days"}</span><span className="banner-separator">|</span><span>NASA POWER historical data · not a forecast</span></div>
      {loading ? <div className="panel large-empty"><EmptyState loading title="Checking observations" text="Applying preliminary thresholds to available historical observations." /></div>
        : riskData?.risks.length ? <div className="risk-card-grid">{riskData.risks.map((risk, index) => <article className={`panel risk-card ${risk.level}`} key={`${risk.type}-${index}`}>
          <div className="risk-card-head"><span className={`risk-symbol ${risk.level}`}><ShieldAlert size={17} /></span><span className={`risk-level ${risk.level}`}>{risk.level === "high" ? "REVIEW SOON" : "WATCH"}</span></div>
          <h3>{risk.type.replaceAll("_", " ")}</h3><div className="risk-observed">{risk.observed} <small>{risk.unit} observed</small></div>
          <div className="risk-threshold">Rule: {risk.threshold}</div><div className="risk-action"><strong>Suggested check</strong><p>{risk.action}</p></div>
        </article>)}</div>
          : <div className="panel large-empty"><EmptyState
            title={!riskData?.screening_available ? "Insufficient observation coverage" : "No screening thresholds triggered"}
            text={!riskData?.screening_available
              ? `Available days — rainfall: ${riskData?.coverage.rainfall_observations ?? 0}/${riskData?.coverage.expected_days ?? 30}; temperature: ${riskData?.coverage.temperature_observations ?? 0}/${riskData?.coverage.expected_days ?? 30}. Incomplete coverage is not treated as low risk.`
              : "No configured screening threshold was triggered in the available observations. This does not guarantee that field conditions are risk-free."} />
          </div>}
      <div className="data-notes"><div className="note-icon"><ShieldAlert size={18} /></div><div><strong>Interpretation and limitations</strong><p>{riskData?.methodology || "These preliminary thresholds require local agronomic validation. A screening signal is not a forecast, diagnosis, or crop-loss prediction; local rainfall, field conditions, and extension advice should guide decisions."}</p></div></div>
    </>}
    {!loading && farms.length === 0 && <div className="panel large-empty"><EmptyState title="No farms to screen" text="Register farm coordinates before checking climate risk indicators." /></div>}
    <div className="section-title-row"><div><h2>Notifications</h2><p>Recommendation updates for your account</p></div></div>
    <section className="panel notification-list">{notifications.length ? notifications.map((notification) => <article className={`notification-row ${notification.read_at ? "read" : ""}`} key={notification.id}><span className="notification-icon"><Bell size={15} /></span><div className="notification-copy"><strong>{notification.title}</strong><p>{notification.message}</p><small>{new Date(notification.created_at).toLocaleString()}</small></div>{!notification.read_at && <button className="subtle-button" onClick={() => void markRead(notification.id)}>Mark read</button>}</article>) : <div className="notification-empty">{loading ? "Loading notifications…" : "You’re all caught up. New recommendation updates will appear here."}</div>}</section>
  </>;
}

function YieldPage({ farms, user }: { farms: Farm[]; user: User }) {
  const [farmId, setFarmId] = useState<number | "">(farms[0]?.id ?? "");
  const [crop, setCrop] = useState(farms[0]?.crop ?? "");
  const [forecast, setForecast] = useState<YieldForecast | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [harvestError, setHarvestError] = useState("");
  const [harvestNotice, setHarvestNotice] = useState("");
  const [harvestDate, setHarvestDate] = useState(new Date().toISOString().slice(0, 10));
  const [quantity, setQuantity] = useState("");
  const selectedFarm = farms.find((farm) => farm.id === Number(farmId));
  const canRecordHarvest = user.role === "farmer" || user.role === "admin";

  async function loadForecast(cropName = crop) {
    if (!farmId || !cropName.trim()) return;
    setLoading(true); setError("");
    try {
      const params = new URLSearchParams({ farm_id: String(farmId), crop: cropName.trim() });
      setForecast(await api<YieldForecast>(`/yield-forecast/?${params.toString()}`));
    } catch (err) {
      setForecast(null);
      setError(err instanceof Error ? err.message : "The yield estimate could not be loaded.");
    } finally { setLoading(false); }
  }
  useEffect(() => { if (farmId && crop.trim()) void loadForecast(); }, [farmId]);

  async function recordHarvest(event: FormEvent) {
    event.preventDefault(); setBusy(true); setHarvestError(""); setHarvestNotice("");
    try {
      await api<HarvestRecord>("/harvests/", {
        method: "POST",
        body: JSON.stringify({ farm: farmId, crop: crop.trim(), harvest_date: harvestDate, quantity_kg: quantity }),
      });
      setQuantity("");
      setHarvestNotice("Harvest record saved.");
      await loadForecast();
    } catch (err) { setHarvestError(err instanceof Error ? err.message : "Harvest record could not be saved."); }
    finally { setBusy(false); }
  }
  const annualData = forecast?.harvest_trend ?? [];
  const climate = forecast?.climate_context;
  return <>
    <PageHeading eyebrow="REFERENCE ESTIMATE · CLIMATE CONTEXT" title="Crop yield forecast" description="Estimate harvest from your farm's past production or a sourced yield benchmark, with recent climate risks shown separately." />
    <form className="panel yield-controls" onSubmit={(event) => { event.preventDefault(); void loadForecast(); }}>
      <label>Farm<select required value={farmId} onChange={(event) => { const id = Number(event.target.value); setFarmId(id); setCrop(farms.find((farm) => farm.id === id)?.crop ?? ""); setForecast(null); }}><option value="">Select a farm</option>{farms.map((farm) => <option value={farm.id} key={farm.id}>{farm.name} · {farm.district}</option>)}</select></label>
      <label>Crop<input required maxLength={100} value={crop} onChange={(event) => setCrop(event.target.value)} placeholder="e.g. maize" /></label>
      <button className="button button-primary" disabled={loading || !farmId || !crop.trim()}>{loading ? "Updating estimate…" : "Update forecast"}</button>
    </form>
    {error && <InlineNotice message={error} />}
    {forecast && <>
      {forecast.forecast_available ? <div className="metric-grid yield-metrics">
        <MetricCard icon={<Sprout size={16} />} label="Expected harvest" value={`${forecast.expected_harvest_kg?.toLocaleString() ?? "—"} kg`} note={`${forecast.farm.area_hectares} ha · ${forecast.crop}`} tone="green" />
        <MetricCard icon={<BarChart3 size={16} />} label="Reference yield" value={`${forecast.reference_yield_kg_per_hectare?.toLocaleString() ?? "—"} kg/ha`} note={forecast.forecast_basis === "farm_history" ? "From recorded annual farm harvests" : `Sourced benchmark · ${forecast.benchmark?.reference_year}`} tone="lime" />
        <MetricCard icon={<CloudSun size={16} />} label="Climate context" value={climate?.available ? `${climate.risks?.length ?? 0} signals` : "Unavailable"} note={climate?.available ? `${climate.source} historical observations` : climate?.detail || "Historical climate not available"} tone="blue" />
      </div> : <div className="panel yield-no-benchmark"><div className="empty-icon"><BarChart3 size={18} /></div><strong>No yield baseline available for {forecast.crop}</strong><p>Record a harvest on this farm or ask an administrator to add a district or national yield benchmark with its source. No quantity is guessed.</p></div>}
      {climate?.available && climate.risks?.length ? <div className="yield-risk-list">{climate.risks.map((risk, index) => <article className={`panel risk-card ${risk.level}`} key={`${risk.type}-${index}`}><div className="risk-level">{risk.level === "high" ? "REVIEW SOON" : "WATCH"}</div><h3>{risk.type.replaceAll("_", " ")}</h3><div className="risk-observed">{risk.observed} <small>{risk.unit} observed</small></div><p>{risk.action}</p></article>)}</div>
        : climate?.available && <div className="yield-climate-note"><CloudSun size={15} /> No configured historical climate screening thresholds were triggered. This does not confirm favorable conditions.</div>}
      {climate && !climate.available && <div className="yield-climate-note"><ShieldAlert size={15} /> Climate context is unavailable: {climate.detail || "No recent observations are available."}</div>}
      <div className="yield-content-grid">
        <section className="panel yield-trend-panel">
          <div className="panel-heading"><div><h3>Recorded production trend</h3><p>Annual harvest totals · {forecast.crop} · {forecast.farm.name}</p></div><TrendingUp size={17} className="panel-heading-icon" /></div>
          {annualData.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={annualData} margin={{ top: 10, right: 4, bottom: 0, left: -20 }}><defs><linearGradient id="harvestFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#16a34a" stopOpacity={0.25} /><stop offset="100%" stopColor="#16a34a" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#f3f4f6" vertical={false} /><XAxis dataKey="year" tick={{ fill: "#9ca3af", fontSize: 10 }} tickLine={false} axisLine={false} /><YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} tickLine={false} axisLine={false} /><Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: 9, color: "#111827", fontSize: 10 }} formatter={(value: number) => [`${value.toLocaleString()} kg`, "Harvest"]} /><Area dataKey="quantity_kg" name="Harvest (kg)" type="monotone" stroke="#16a34a" strokeWidth={2} fill="url(#harvestFill)" /></AreaChart></ResponsiveContainer></div> : <EmptyState title="No production history yet" text="Add actual harvest records to build a season-by-season production trend." />}
          {!!forecast.benchmark_trend.length && <div className="benchmark-history"><strong>Sourced benchmark history</strong>{forecast.benchmark_trend.map((item) => <span key={`${item.reference_year}-${item.district}`}>{item.reference_year} · {Number(item.yield_kg_per_hectare).toLocaleString()} kg/ha · {item.district || "National"} · <a href={item.source_url} target="_blank" rel="noreferrer">{item.source_title}</a></span>)}</div>}
        </section>
        {canRecordHarvest && selectedFarm && <form className="panel harvest-entry" onSubmit={(event) => void recordHarvest(event)}>
          <div className="form-heading-icon"><Sprout size={18} /></div><h3>Record an actual harvest</h3><p>Use the total harvested amount for the season. These records are private to the farm owner and help establish a farm-specific baseline.</p>
          <label>Harvest date<input required type="date" max={new Date().toISOString().slice(0, 10)} value={harvestDate} onChange={(event) => setHarvestDate(event.target.value)} /></label>
          <label>Harvest quantity (kg)<input required type="number" min="0.01" step="0.01" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="e.g. 850" /></label>
          {harvestError && <InlineNotice message={harvestError} />}
          {harvestNotice && <div className="success-message"><Check size={14} />{harvestNotice}</div>}
          <button className="button button-primary" disabled={busy || !quantity}>{busy ? "Saving…" : "Save harvest record"}</button>
        </form>}
      </div>
      <div className="yield-method-note"><ShieldAlert size={15} />{forecast.methodology} {climate?.methodology}</div>
    </>}
    {!farms.length && <div className="panel large-empty"><EmptyState title="Add a farm to forecast production" text="Farm area and crop details are needed to estimate expected harvest." /></div>}
  </>;
}

function MarketPage() {
  const [data, setData] = useState<MarketIntelligence | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [commodity, setCommodity] = useState("");
  const [district, setDistrict] = useState("");
  const [trendMarket, setTrendMarket] = useState("");
  useEffect(() => {
    api<MarketIntelligence>("/market-intelligence/")
      .then((response) => { setData(response); setError(""); })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);
  const prices = data?.prices ?? [];
  const commodities = [...new Set(prices.map((price) => price.commodity))].sort((a, b) => a.localeCompare(b));
  const districts = [...new Set(prices.filter((price) => !commodity || price.commodity.toLowerCase() === commodity.toLowerCase()).map((price) => price.district))].sort((a, b) => a.localeCompare(b));
  const currentPrices = useMemo(() => {
    // Use the latest observation date in the dataset (not today) as the anchor.
    // WFP publishes monthly; anchoring to today would hide all data when the
    // feed is more than 30 days old.
    const latestDate = prices.reduce<string | null>(
      (best, p) => (best === null || p.observed_at > best ? p.observed_at : best),
      null,
    );
    const anchor = latestDate ? new Date(`${latestDate}T00:00:00`) : new Date();
    const cutoff = new Date(anchor);
    cutoff.setDate(cutoff.getDate() - 90); // show up to 90 days before the latest observation
    const current = prices.filter((price) =>
      (!commodity || price.commodity.toLowerCase() === commodity.toLowerCase())
      && (!district || price.district.toLowerCase() === district.toLowerCase())
      && new Date(`${price.observed_at}T00:00:00`) >= cutoff
    );
    const latest = new Map<string, MarketPrice>();
    for (const price of current) {
      const key = `${price.commodity.toLowerCase()}|${price.market.toLowerCase()}|${price.district.toLowerCase()}|${price.currency}|${price.unit.toLowerCase()}|${price.price_type.toLowerCase()}`;
      if (!latest.has(key)) latest.set(key, price);
    }
    return [...latest.values()];
  }, [prices, commodity, district]);
  const opportunities = useMemo(() => {
    const comparable = new Map<string, MarketPrice[]>();
    currentPrices.forEach((price) => {
      const key = `${price.commodity.toLowerCase()}|${price.currency}|${price.unit.toLowerCase()}|${price.price_type.toLowerCase()}`;
      comparable.set(key, [...(comparable.get(key) ?? []), price]);
    });
    return [...comparable.values()].filter((group) => group.length > 1).map((group) => {
      const sorted = [...group].sort((a, b) => Number(a.price) - Number(b.price));
      const low = sorted[0];
      const high = sorted[sorted.length - 1];
      return { low, high, spread: Number(high.price) - Number(low.price), spreadPct: (Number(high.price) - Number(low.price)) / Number(low.price) * 100 };
    }).filter((item) => item.spread > 0);
  }, [currentPrices]);
  const activeMarkets = commodity ? [...new Map(prices.filter((price) =>
    price.commodity.toLowerCase() === commodity.toLowerCase()
    && (!district || price.district.toLowerCase() === district.toLowerCase())
  ).map((price) => {
    const key = JSON.stringify([price.market, price.district, price.price_type]);
    return [key, { key, label: `${price.market} · ${price.district} · ${price.price_type}` }] as const;
  })).values()].sort((a, b) => a.label.localeCompare(b.label)) : [];
  const selectedTrendMarket = activeMarkets.some((market) => market.key === trendMarket) ? trendMarket : activeMarkets[0]?.key ?? "";
  const trend = prices.filter((price) =>
    !!commodity
    && price.commodity.toLowerCase() === commodity.toLowerCase()
    && (!district || price.district.toLowerCase() === district.toLowerCase())
    && JSON.stringify([price.market, price.district, price.price_type]) === selectedTrendMarket
  ).sort((a, b) => a.observed_at.localeCompare(b.observed_at))
    .map((price) => ({ date: price.observed_at, price: Number(price.price), unit: price.unit, currency: price.currency }));
  return <>
    <PageHeading eyebrow="WFP + ADMIN SOURCES · LAST 12 MONTHS" title="Agricultural market intelligence" description="Review attributed Uganda market observations, price types, and recent differences across markets." />
    <div className="market-controls">
      <label>Commodity<select value={commodity} onChange={(event) => { setCommodity(event.target.value); setTrendMarket(""); }}><option value="">All commodities</option>{commodities.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
      <label>District<select value={district} onChange={(event) => setDistrict(event.target.value)}><option value="">All districts</option>{districts.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
    </div>
    {error && <InlineNotice message={error} />}
    {opportunities.length > 0 && <section className="market-opportunities"><div className="market-section-heading"><div><div className="eyebrow">PRICE SPREADS · MATCHING UNIT, CURRENCY AND TYPE</div><h2>Potential selling opportunities</h2></div><span>Observed in the last 30 days · excludes transport, quality and fees</span></div><div className="opportunity-grid">{opportunities.map((item) => <article className="panel opportunity-card" key={`${item.low.currency}-${item.low.unit}-${item.low.price_type}`}><span className="opportunity-delta">+{item.spreadPct.toFixed(1)}% spread</span><strong>{item.high.market}, {item.high.district}</strong><p>{item.high.price_type}: {formatMarketPrice(item.high.price, item.high.currency, item.high.unit)} versus {formatMarketPrice(item.low.price, item.low.currency, item.low.unit)} at {item.low.market}</p><small>Market observations are not guaranteed farm-gate offers. Compare transport cost, quality, fees and freshness before choosing a buyer.</small></article>)}</div></section>}
    <section className="market-section">
      <div className="market-section-heading"><div><h2>Latest local prices</h2><p>Most recent published observation per market; dates and price types are shown for each record.</p></div><Store size={17} className="panel-heading-icon" /></div>
      {loading ? <div className="panel large-empty"><EmptyState loading title="Loading market prices" text="Retrieving sourced market observations." /></div>
        : currentPrices.length ? <div className="market-price-grid">{currentPrices.map((price) => <article className="panel market-price-card" key={price.id}><div className="market-price-top"><span className="market-price-commodity">{price.commodity}</span><small>{price.observed_at}</small></div><h3>{price.market}</h3><p>{price.district} · {price.price_type}</p><strong>{formatMarketPrice(price.price, price.currency, price.unit)}</strong><a href={price.source_url} target="_blank" rel="noreferrer">Source: {price.source_title}</a></article>)}</div>
          : <div className="panel large-empty"><EmptyState title="No recent sourced prices" text={data?.data_note || "Administrators can add attributed market observations in Django Admin. No prices are fabricated."} /></div>}
    </section>
    <section className="panel market-trend-panel">
      <div className="panel-heading"><div><h3>Market price trend</h3><p>{selectedTrendMarket ? `${commodity || "All commodities"} · ${activeMarkets.find((market) => market.key === selectedTrendMarket)?.label} · up to 12 months` : "Historical source observations"}</p></div>{activeMarkets.length > 1 && <select className="market-trend-select" aria-label="Select market for price trend" value={selectedTrendMarket} onChange={(event) => setTrendMarket(event.target.value)}>{activeMarkets.map((market) => <option key={market.key} value={market.key}>{market.label}</option>)}</select>}</div>
      {trend.length > 1 ? <div className="chart-wrap market-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend} margin={{ top: 10, right: 4, bottom: 0, left: -15 }}><defs><linearGradient id="marketPriceFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#16a34a" stopOpacity={0.25} /><stop offset="100%" stopColor="#16a34a" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#f3f4f6" vertical={false} /><XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 9 }} tickLine={false} axisLine={false} minTickGap={30} /><YAxis tick={{ fill: "#9ca3af", fontSize: 9 }} tickLine={false} axisLine={false} /><Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: 9, color: "#111827", fontSize: 10 }} formatter={(value: number, _name, item) => [formatMarketPrice(value, item.payload.currency, item.payload.unit), "Price"]} /><Area dataKey="price" type="monotone" stroke="#16a34a" strokeWidth={2} fill="url(#marketPriceFill)" /></AreaChart></ResponsiveContainer></div>       : <div className="market-trend-empty">{loading ? "Loading price history…" : !commodity ? "Select a commodity to view market price trends." : "At least two attributed observations for a market are needed to show a trend."}</div>}
    </section>
    {data && <div className="market-data-note"><ShieldAlert size={14} />{data.data_note} WFP survey prices are not guaranteed farm-gate buying offers; contact your extension team if your market or commodity is missing.</div>}
  </>;
}

function formatMarketPrice(price: string | number, currency: string, unit: string) {
  return `${currency} ${Number(price).toLocaleString("en-UG", { maximumFractionDigits: 2 })} / ${unit}`;
}

function AnalyticsPage({ farms }: { farms: Farm[] }) {
  const [analytics, setAnalytics] = useState<{ farm_count: number; total_hectares: number; crop_distribution: { crop: string; count: number }[] } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<typeof analytics>("/analytics/").then(setAnalytics).catch((err: Error) => setError(err.message)); }, []);
  const data = analytics?.crop_distribution.map((row) => ({ name: row.crop, farms: row.count })) ?? [];
  return <><PageHeading eyebrow="WORKSPACE INDICATORS" title="Farm analytics" description="A snapshot of registered farm records and reported crop distribution." /><div className="metric-grid analytics-metrics"><MetricCard icon={<Tractor size={17} />} label="Registered farms" value={analytics?.farm_count ?? "—"} note="Visible in your workspace" tone="green" /><MetricCard icon={<Sprout size={17} />} label="Area recorded" value={analytics ? `${analytics.total_hectares.toLocaleString()} ha` : "—"} note="Reported farm area" tone="lime" /><MetricCard icon={<MapPin size={17} />} label="Districts represented" value={new Set(farms.map((farm) => farm.district)).size} note="Based on saved farm records" tone="blue" /><MetricCard icon={<Activity size={17} />} label="Crop types" value={data.length} note="Crop records entered" tone="orange" /></div>{error && <InlineNotice message={error} />}<div className="panel climate-panel analytics-chart"><div className="panel-heading"><div><h3>Crop distribution</h3><p>Number of registered farms per recorded crop</p></div></div>{data.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><defs><linearGradient id="cropFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#16a34a" stopOpacity={0.25} /><stop offset="100%" stopColor="#16a34a" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#f3f4f6" vertical={false} /><XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 11 }} tickLine={false} axisLine={false} /><YAxis allowDecimals={false} tick={{ fill: "#9ca3af", fontSize: 11 }} tickLine={false} axisLine={false} /><Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: 10, color: "#111827" }} /><Area dataKey="farms" type="monotone" stroke="#16a34a" strokeWidth={2} fill="url(#cropFill)" /></AreaChart></ResponsiveContainer></div> : <EmptyState title="Not enough crop records yet" text="Add crop details to farms to build a crop distribution view." />}</div></>;
}

function ProfilePage({ user, onUpdated }: { user: User; onUpdated: (user: User) => void }) {
  const [form, setForm] = useState({ first_name: user.first_name, last_name: user.last_name, email: user.email, district: user.district, phone: user.phone });
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [photoBusy, setPhotoBusy] = useState(false);
  const photoInput = useRef<HTMLInputElement>(null);
  async function submit(e: FormEvent) {
    e.preventDefault(); setNotice(""); setError("");
    try { const updated = await api<User>("/auth/me/", { method: "PATCH", body: JSON.stringify(form) }); onUpdated(updated); setNotice("Profile saved."); }
    catch (err) { setError(err instanceof Error ? err.message : "Profile could not be saved."); }
  }
  async function uploadPhoto(file: File) {
    setNotice(""); setError("");
    if (file.size > 5 * 1024 * 1024) { setError("Choose an image that is 5 MB or smaller."); return; }
    if (file.type && !["image/jpeg", "image/png", "image/webp"].includes(file.type)) { setError("Choose a JPEG, PNG, or WebP image."); return; }
    const data = new FormData();
    data.append("profile_image", file);
    setPhotoBusy(true);
    try {
      const updated = await api<User>("/auth/me/profile-image/", { method: "POST", body: data });
      onUpdated(updated);
      setNotice("Profile picture updated.");
    } catch (err) { setError(err instanceof Error ? err.message : "Profile picture could not be uploaded."); }
    finally { setPhotoBusy(false); }
  }
  async function removePhoto() {
    setNotice(""); setError(""); setPhotoBusy(true);
    try {
      const updated = await api<User>("/auth/me/profile-image/", { method: "DELETE" });
      onUpdated(updated);
      setNotice("Profile picture removed.");
    } catch (err) { setError(err instanceof Error ? err.message : "Profile picture could not be removed."); }
    finally { setPhotoBusy(false); }
  }
  return <><PageHeading eyebrow="ACCOUNT" title="Profile settings" description="Manage the account information used in your AgriCloud workspace." /><form className="panel profile-form" onSubmit={submit}><div className="profile-intro"><UserAvatar user={user} className="profile-large-avatar" /><div className="profile-identity"><h3>{user.first_name || user.username} {user.last_name}</h3><span>{roleLabel(user.role)} · {user.username}</span><div className="profile-photo-actions"><input ref={photoInput} className="profile-file-input" type="file" accept="image/jpeg,image/png,image/webp" aria-label="Choose a profile picture" disabled={photoBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadPhoto(file); event.target.value = ""; }} /><button type="button" className="button button-secondary button-small" disabled={photoBusy} onClick={() => photoInput.current?.click()}>{photoBusy ? "Updating photo…" : user.profile_image ? "Change photo" : "Upload photo"}</button>{user.profile_image && <button type="button" className="text-button profile-remove-photo" disabled={photoBusy} onClick={() => void removePhoto()}>Remove</button>}<small>JPG, PNG or WebP · Up to 5 MB</small></div></div></div><div className="form-grid"><label>First name<input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></label><label>Last name<input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></label><label>Email address<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label><label>District<input value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></label><label>Phone<input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label></div>{notice && <div className="success-message"><Check size={15} />{notice}</div>}{error && <InlineNotice message={error} />}<div className="form-actions"><span>Role: {roleLabel(user.role)} · Roles are assigned by an administrator.</span><button className="button button-primary">Save changes</button></div></form></>;
}

function UserAvatar({ user, className }: { user: User; className: string }) {
  return user.profile_image
    ? <img className={`${className} user-photo`} src={user.profile_image} alt="" aria-hidden="true" />
    : <span className={className} aria-hidden="true">{initials(user)}</span>;
}

function AuthPage({ onSignIn, onRegister, error }: { onSignIn: (username: string, password: string) => Promise<void>; onRegister: (data: Record<string, string>) => Promise<void>; error: string }) {
  // Detect if we arrived via a password-reset link (?uid=...&token=...)
  const params = new URLSearchParams(window.location.search);
  const resetUid = params.get("uid") ?? "";
  const resetToken = params.get("token") ?? "";
  const arrivedViaResetLink = Boolean(resetUid && resetToken);

  const [mode, setMode] = useState<"signin" | "register" | "forgot" | "reset">(
    arrivedViaResetLink ? "reset" : "signin"
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(error);
  const [successMessage, setSuccessMessage] = useState("");
  const [form, setForm] = useState({ username: "", password: "", newPassword: "", confirmPassword: "", first_name: "", last_name: "", email: "", district: "" });
  useEffect(() => { setMessage(error); }, [error]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setSuccessMessage("");
    try {
      if (mode === "register") {
        await onRegister(form);
      } else if (mode === "signin") {
        await onSignIn(form.username, form.password);
      } else if (mode === "forgot") {
        await api<{ detail: string }>("/auth/password-reset/", {
          method: "POST",
          body: JSON.stringify({ email: form.email }),
        });
        setSuccessMessage("If that email is registered, a reset link has been sent. Check your inbox (and spam folder).");
      } else if (mode === "reset") {
        if (form.newPassword !== form.confirmPassword) {
          setMessage("Passwords do not match.");
          return;
        }
        await api<{ detail: string }>("/auth/password-reset/confirm/", {
          method: "POST",
          body: JSON.stringify({ uid: resetUid, token: resetToken, password: form.newPassword }),
        });
        // Clear reset params from URL and go to sign-in
        window.history.replaceState({}, "", "/");
        setSuccessMessage("Password updated successfully. You can now sign in with your new password.");
        setMode("signin");
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "We couldn't complete your request.");
    } finally {
      setBusy(false);
    }
  }

  const eyebrow = mode === "register" ? "CREATE YOUR ACCOUNT" : mode === "forgot" ? "ACCOUNT RECOVERY" : mode === "reset" ? "SET NEW PASSWORD" : "WELCOME BACK";
  const heading = mode === "register" ? "Start your workspace" : mode === "forgot" ? "Reset your password" : mode === "reset" ? "Choose a new password" : "Sign in to AgriCloud";
  const subtext = mode === "register" ? "Create an account to register your farms and explore local climate context."
    : mode === "forgot" ? "Enter your registered email address and we'll send you a reset link."
    : mode === "reset" ? "Enter a new password for your account. It must be at least 10 characters."
    : "Enter your credentials to continue to your farm dashboard.";

  return (
    <div className="auth-page">
      <div className="auth-left">
        <div className="auth-brand"><div className="brand-mark"><Leaf size={18} fill="currentColor" /></div><span>agricloud<span className="brand-ai">.ai</span></span></div>
        <div className="auth-content">
          <div className="hero-kicker"><span className="live-dot" /> FARM INTELLIGENCE FOR UGANDA</div>
          <h1>A better season<br />starts with <em>insight.</em></h1>
          <p>Bring climate context, your farm records, and trusted local knowledge together in one place.</p>
          <div className="auth-points">
            <span><Check size={15} /> NASA POWER climate observations</span>
            <span><Check size={15} /> Transparent planting guidance</span>
            <span><Check size={15} /> Your farm information, securely scoped</span>
          </div>
        </div>
        <div className="auth-footer">Built for farmers and agricultural extension teams in Uganda.</div>
      </div>

      <div className="auth-right">
        <div className="auth-form-wrap">
          <div className="auth-form-eyebrow">{eyebrow}</div>
          <h2>{heading}</h2>
          <p>{subtext}</p>

          {message && <InlineNotice message={message} />}
          {successMessage && <div className="inline-notice inline-notice-success"><Check size={15} />{successMessage}</div>}

          {!successMessage && (
            <form onSubmit={submit}>
              {mode === "register" && (
                <>
                  <label>First name<input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} placeholder="First name" /></label>
                  <label>Last name<input required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} placeholder="Last name" /></label>
                  <label>Email address<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" /></label>
                  <label>District <span className="optional">(optional)</span><input value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} placeholder="e.g. Wakiso" /></label>
                </>
              )}

              {mode === "forgot" && (
                <label>Email address<input required type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" /></label>
              )}

              {mode === "reset" && (
                <>
                  <label>New password<input required type="password" autoComplete="new-password" minLength={10} value={form.newPassword} onChange={(e) => setForm({ ...form, newPassword: e.target.value })} placeholder="At least 10 characters" /></label>
                  <label>Confirm password<input required type="password" autoComplete="new-password" minLength={10} value={form.confirmPassword} onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })} placeholder="Repeat your new password" /></label>
                </>
              )}

              {(mode === "signin" || mode === "register") && (
                <>
                  <label>Username<input autoComplete="username" required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="Your username" /></label>
                  <label>
                    Password
                    <input autoComplete={mode === "register" ? "new-password" : "current-password"} minLength={mode === "register" ? 10 : undefined} type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={mode === "register" ? "At least 10 characters" : "Enter your password"} />
                  </label>
                  {mode === "signin" && (
                    <div className="auth-forgot-row">
                      <button type="button" className="auth-link" onClick={() => { setMode("forgot"); setMessage(""); setSuccessMessage(""); }}>Forgot password?</button>
                    </div>
                  )}
                </>
              )}

              <button className="button button-primary auth-submit" disabled={busy}>
                {busy ? "Please wait…" : mode === "register" ? "Create account" : mode === "forgot" ? "Send reset link" : mode === "reset" ? "Set new password" : "Sign in"} <ChevronRight size={16} />
              </button>
            </form>
          )}

          {mode !== "reset" && (
            <div className="auth-switch">
              {mode === "forgot" ? (
                <>Remember your password? <button className="auth-link" onClick={() => { setMode("signin"); setMessage(""); setSuccessMessage(""); }}>Sign in</button></>
              ) : mode === "register" ? (
                <>Already have an account? <button className="auth-link" onClick={() => { setMode("signin"); setMessage(""); setSuccessMessage(""); }}>Sign in</button></>
              ) : (
                <>New to AgriCloud? <button className="auth-link" onClick={() => { setMode("register"); setMessage(""); setSuccessMessage(""); }}>Create account</button></>
              )}
            </div>
          )}

          <div className="auth-secure"><ShieldAlert size={13} /> New registrations receive the farmer role. Staff roles are assigned by administrators.</div>
        </div>
      </div>
    </div>
  );
}

function initials(user: User) { return `${user.first_name?.[0] ?? user.username[0] ?? "A"}${user.last_name?.[0] ?? ""}`.toUpperCase(); }
function roleLabel(role: User["role"]) { return role === "extension" ? "Extension worker" : role === "admin" ? "Administrator" : "Farmer"; }
function forecastDayLabel(value: string) {
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-UG", { weekday: "short", day: "numeric", month: "short" }).format(date);
}

export default App;
