import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import {
  Activity, Bell, Check, ChevronDown, ChevronRight, LogOut, Pencil,
  CloudSun, Droplets, Ellipsis, Leaf, MapPin, Menu, Plus, Search, ShieldAlert,
  MessageCircleQuestion, Sprout, Sun, Thermometer, Tractor, TrendingUp, X,
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { api, ApiError, Farm, FarmQuestion, NotificationItem, Recommendation, User, Weather } from "./api";

type Page = "overview" | "farms" | "weather" | "advisor" | "map" | "assistant" | "questions" | "alerts" | "analytics" | "profile";
const mainLinks: { id: Page; label: string; icon: typeof Activity }[] = [
  { id: "overview", label: "Dashboard", icon: Activity },
  { id: "farms", label: "Crop management", icon: Tractor },
  { id: "weather", label: "Weather", icon: CloudSun },
  { id: "advisor", label: "Planting advisor", icon: Sprout },
  { id: "map", label: "Field monitoring", icon: MapPin },
  { id: "assistant", label: "AI assistant", icon: Ellipsis },
  { id: "questions", label: "Farmer questions", icon: MessageCircleQuestion },
  { id: "alerts", label: "Alerts", icon: ShieldAlert },
  { id: "analytics", label: "Reports", icon: TrendingUp },
];
const pageTitles: Record<Page, string> = {
  overview: "Overview", farms: "My farms", weather: "Weather intelligence", advisor: "Planting advisor",
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

  const loadWorkspace = async () => {
    try {
      const current = await api<User>("/auth/me/");
      setUser(current);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        localStorage.removeItem("agri_access");
        localStorage.removeItem("agri_refresh");
      }
      setUser(null);
      setAuthError(error instanceof Error ? error.message : "Unable to load your account.");
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
  if (!user) return <AuthPage onSignIn={signIn} onRegister={register} error={authError} />;

  return (
    <div className="app-shell">
      {mobileNav && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
      <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
        <div className="brand"><div className="brand-mark"><Leaf size={18} fill="currentColor" /></div><span>agricloud<span className="brand-ai">.ai</span></span></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {mainLinks.slice(0, 3).map((item) => <NavItem key={item.id} item={item} active={page === item.id} onClick={() => { setPage(item.id); setMobileNav(false); }} />)}
          <div className="nav-section">FIELD TOOLS</div>
          {mainLinks.slice(3).filter((item) => item.id !== "questions" || user.role !== "farmer").map((item) => <NavItem key={item.id} item={item} active={page === item.id} onClick={() => { setPage(item.id); setMobileNav(false); }} />)}
        </nav>
        <div className="sidebar-bottom">
          <div className="season-card"><div className="season-icon"><Sun size={16} /></div><div><strong>Season watch</strong><span>Local climate context</span></div><ChevronRight size={15} /></div>
          <button className={`nav-item ${page === "profile" ? "active" : ""}`} onClick={() => setPage("profile")}><div className="avatar">{initials(user)}</div><span className="profile-label"><strong>{user.first_name || user.username}</strong><small>Settings · {roleLabel(user.role)}</small></span><ChevronDown size={14} /></button>
        </div>
      </aside>
      <main className="main-shell">
        <header className="topbar">
          <button className="icon-btn mobile-menu" aria-label="Open menu" onClick={() => setMobileNav(true)}><Menu size={19} /></button>
          <div className="breadcrumbs"><span>Workspace</span><ChevronRight size={13} /><strong>{pageTitles[page]}</strong></div>
          <div className="topbar-actions"><div className="searchbox"><Search size={16} /><input placeholder="Search farms, crops..." aria-label="Search" /><kbd>⌘ K</kbd></div><button className="icon-btn notification-btn" aria-label="Notifications" onClick={() => setPage("alerts")}><Bell size={18} /></button><button className="top-add-farm" onClick={() => setPage("farms")} aria-label="Open farm management"><Plus size={16} /><span>Add farm</span></button><button className="user-chip" onClick={() => setPage("profile")} aria-label="Open profile settings"><span className="top-avatar">{initials(user)}</span><span className="user-chip-copy"><strong>{user.first_name || user.username}</strong><small>{roleLabel(user.role)}</small></span><ChevronDown size={13} /></button><button className="icon-btn logout-btn" aria-label="Sign out" title="Sign out" onClick={() => void signOut()}><LogOut size={16} /></button></div>
        </header>
        <div className="content">
          {page === "overview" && <Dashboard user={user} farms={farms} go={setPage} />}
          {page === "farms" && <FarmsPage farms={farms} refresh={refreshFarms} readOnly={user.role === "extension"} />}
          {page === "weather" && <WeatherPage farms={farms} />}
          {page === "advisor" && <AdvisorPage farms={farms} />}
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
    ]).then(([statsResult, weatherResult, recommendationsResult]) => {
      if (!active) return;
      if (statsResult.status === "fulfilled") setAnalytics(statsResult.value);
      if (weatherResult.status === "fulfilled") {
        setWeather(weatherResult.value);
        if (weatherResult.value) setWeatherError("");
      } else setWeatherError(weatherResult.reason instanceof Error ? weatherResult.reason.message : "Could not load climate observations.");
      if (recommendationsResult.status === "fulfilled") setRecentRecommendation(recommendationsResult.value[0] ?? null);
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [farms]);
  const latestObservation = weather?.observations.at(-1);
  const latest = latestObservation?.values;
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
          <div className="panel-heading"><div><h3>Latest climate</h3><p>{latestObservation ? `Observed ${latestObservation.date}` : "Historical data for your farm"}</p></div><CloudSun size={17} className="panel-heading-icon" /></div>
          {weatherError && <InlineNotice message={weatherError} />}
          <div className="weather-reading-grid">
            <div className="weather-reading weather-temperature"><Thermometer size={15} /><span>Temperature</span><strong>{latest?.T2M ? `${latest.T2M.value.toFixed(1)}°C` : "—"}</strong></div>
            <div className="weather-reading"><Droplets size={15} /><span>Rainfall</span><strong>{latest?.PRECTOTCORR ? `${latest.PRECTOTCORR.value.toFixed(1)} mm` : "—"}</strong></div>
            <div className="weather-reading"><Activity size={15} /><span>Humidity</span><strong>{latest?.RH2M ? `${latest.RH2M.value.toFixed(0)}%` : "—"}</strong></div>
          </div>
          <div className="dashboard-data-note"><span className="source-dot" /> {weather?.source || "NASA POWER"} · historical observations</div>
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

const cropChartColors = ["#43d392", "#d3eb74", "#79c6c8", "#e0b877", "#7aa5df", "#c38fd0"];

function CropDistributionChart({ data }: { data: { crop: string; count: number }[] }) {
  const total = data.reduce((sum, item) => sum + item.count, 0);
  return <div className="crop-chart-layout">
    <div className="crop-chart-visual">
      <ResponsiveContainer width="100%" height="100%"><PieChart>
        <Pie data={data} dataKey="count" nameKey="crop" innerRadius="61%" outerRadius="83%" paddingAngle={2} stroke="none">
          {data.map((item, index) => <Cell key={item.crop} fill={cropChartColors[index % cropChartColors.length]} />)}
        </Pie>
        <Tooltip contentStyle={{ background: "#0c2621", border: "1px solid #24463b", borderRadius: 9, color: "#eff7f0", fontSize: 10 }} formatter={(value: number) => [`${value} farm${value === 1 ? "" : "s"}`, "Recorded"]} />
      </PieChart></ResponsiveContainer>
      <div className="crop-chart-total"><strong>{total}</strong><span>farms</span></div>
    </div>
    <div className="crop-chart-legend">{data.slice(0, 5).map((item, index) => <div key={item.crop}><span><i style={{ backgroundColor: cropChartColors[index % cropChartColors.length] }} />{item.crop}</span><strong>{item.count}</strong></div>)}</div>
  </div>;
}

function MetricCard({ icon, label, value, note, tone }: { icon: ReactNode; label: string; value: ReactNode; note: string; tone: string }) {
  return <div className="metric-card"><div className="metric-top"><span className={`metric-icon ${tone}`}>{icon}</span><button className="more-btn" aria-label={`${label} options`}><Ellipsis size={17} /></button></div><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></div>;
}

function Condition({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="condition-row"><span className="condition-label">{icon}{label}</span><strong>{value}</strong></div>;
}

function ClimateChart({ data }: { data: { date: string; rain: number | null; temp: number | null }[] }) {
  return <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 10, right: 4, bottom: 0, left: -20 }}>
    <defs><linearGradient id="rainFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#23cf83" stopOpacity={0.27} /><stop offset="100%" stopColor="#23cf83" stopOpacity={0} /></linearGradient><linearGradient id="tempFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#d0ed72" stopOpacity={0.12} /><stop offset="100%" stopColor="#d0ed72" stopOpacity={0} /></linearGradient></defs>
    <CartesianGrid stroke="#ffffff0b" vertical={false} /><XAxis dataKey="date" tick={{ fill: "#82958d", fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={30} /><YAxis yAxisId="rain" tick={{ fill: "#82958d", fontSize: 10 }} tickLine={false} axisLine={false} /><YAxis yAxisId="temp" orientation="right" tick={{ fill: "#82958d", fontSize: 10 }} tickLine={false} axisLine={false} /><Tooltip contentStyle={{ background: "#0c2621", border: "1px solid #24463b", borderRadius: 10, color: "#eff7f0", fontSize: 12 }} labelStyle={{ color: "#a9b9b0" }} />
    <Area yAxisId="rain" type="monotone" dataKey="rain" name="Rainfall (mm/day)" stroke="#25d38a" strokeWidth={2} fill="url(#rainFill)" connectNulls /><Area yAxisId="temp" type="monotone" dataKey="temp" name="Temperature (°C)" stroke="#d3ed71" strokeWidth={2} fill="url(#tempFill)" connectNulls />
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
      <label>Latitude<input required type="number" min="-90" max="90" step="any" value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} placeholder="0.3476" /></label>
      <label>Longitude<input required type="number" min="-180" max="180" step="any" value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} placeholder="32.5825" /></label>
      <label>Soil type<select value={form.soil_type} onChange={(e) => setForm({ ...form, soil_type: e.target.value })}><option value="unknown">Not specified</option><option value="clay">Clay</option><option value="loam">Loam</option><option value="sandy">Sandy</option><option value="volcanic">Volcanic</option></select></label>
    </div><div className="form-actions"><span>Coordinates are stored with your private farm record.</span><button className="button button-primary" disabled={busy}>{busy ? "Saving…" : editingId ? "Save changes" : "Save farm"}</button></div></form>}
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
  useEffect(() => { if (!selectedId && farms.length) setSelectedId(farms[0].id); }, [farms, selectedId]);
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
  return <>
    <PageHeading eyebrow="NASA POWER · HISTORICAL DATA" title="Weather intelligence" description="Explore daily climate observations at your registered farm coordinates." action={<div className="weather-controls"><select aria-label="Select farm" value={selectedId} onChange={(e) => setSelectedId(Number(e.target.value))}>{farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name} · {farm.district}</option>)}</select><select aria-label="Observation period" value={period} onChange={(e) => setPeriod(Number(e.target.value))}><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={365}>Last year</option></select></div>} />
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

function MapPage({ farms }: { farms: Farm[] }) {
  return <>
    <PageHeading eyebrow="OPENSTREETMAP" title="Farm map" description="See registered farm locations across Uganda. Map tiles are provided by OpenStreetMap." />
    {farms.length ? <div className="panel map-panel"><FarmMap farms={farms} /><div className="map-legend"><span className="map-pip" /> Your registered farms <span className="map-count">{farms.length} location{farms.length === 1 ? "" : "s"}</span></div></div> : <div className="panel large-empty"><EmptyState title="No mapped farms yet" text="Register farm coordinates to see your growing locations on the map." /></div>}
  </>;
}

function FarmMap({ farms, compact = false }: { farms: Farm[]; compact?: boolean }) {
  const center: [number, number] = farms.length ? [Number(farms[0].latitude), Number(farms[0].longitude)] : [1.3733, 32.2903];
  return <MapContainer center={center} zoom={farms.length === 1 ? 10 : 7} scrollWheelZoom={!compact} className={`leaflet-map${compact ? " dashboard-leaflet-map" : ""}`}>
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

function AnalyticsPage({ farms }: { farms: Farm[] }) {
  const [analytics, setAnalytics] = useState<{ farm_count: number; total_hectares: number; crop_distribution: { crop: string; count: number }[] } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<typeof analytics>("/analytics/").then(setAnalytics).catch((err: Error) => setError(err.message)); }, []);
  const data = analytics?.crop_distribution.map((row) => ({ name: row.crop, farms: row.count })) ?? [];
  return <><PageHeading eyebrow="WORKSPACE INDICATORS" title="Farm analytics" description="A snapshot of registered farm records and reported crop distribution." /><div className="metric-grid analytics-metrics"><MetricCard icon={<Tractor size={17} />} label="Registered farms" value={analytics?.farm_count ?? "—"} note="Visible in your workspace" tone="green" /><MetricCard icon={<Sprout size={17} />} label="Area recorded" value={analytics ? `${analytics.total_hectares.toLocaleString()} ha` : "—"} note="Reported farm area" tone="lime" /><MetricCard icon={<MapPin size={17} />} label="Districts represented" value={new Set(farms.map((farm) => farm.district)).size} note="Based on saved farm records" tone="blue" /><MetricCard icon={<Activity size={17} />} label="Crop types" value={data.length} note="Crop records entered" tone="orange" /></div>{error && <InlineNotice message={error} />}<div className="panel climate-panel analytics-chart"><div className="panel-heading"><div><h3>Crop distribution</h3><p>Number of registered farms per recorded crop</p></div></div>{data.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><defs><linearGradient id="cropFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#24d184" stopOpacity={0.3} /><stop offset="100%" stopColor="#24d184" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#ffffff0b" vertical={false} /><XAxis dataKey="name" tick={{ fill: "#82958d", fontSize: 11 }} tickLine={false} axisLine={false} /><YAxis allowDecimals={false} tick={{ fill: "#82958d", fontSize: 11 }} tickLine={false} axisLine={false} /><Tooltip contentStyle={{ background: "#0c2621", border: "1px solid #24463b", borderRadius: 10 }} /><Area dataKey="farms" type="monotone" stroke="#24d184" strokeWidth={2} fill="url(#cropFill)" /></AreaChart></ResponsiveContainer></div> : <EmptyState title="Not enough crop records yet" text="Add crop details to farms to build a crop distribution view." />}</div></>;
}

function ProfilePage({ user, onUpdated }: { user: User; onUpdated: (user: User) => void }) {
  const [form, setForm] = useState({ first_name: user.first_name, last_name: user.last_name, email: user.email, district: user.district, phone: user.phone });
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault(); setNotice(""); setError("");
    try { const updated = await api<User>("/auth/me/", { method: "PATCH", body: JSON.stringify(form) }); onUpdated(updated); setNotice("Profile saved."); }
    catch (err) { setError(err instanceof Error ? err.message : "Profile could not be saved."); }
  }
  return <><PageHeading eyebrow="ACCOUNT" title="Profile settings" description="Manage the account information used in your AgriCloud workspace." /><form className="panel profile-form" onSubmit={submit}><div className="profile-intro"><div className="profile-large-avatar">{initials(user)}</div><div><h3>{user.first_name || user.username} {user.last_name}</h3><span>{roleLabel(user.role)} · {user.username}</span></div></div><div className="form-grid"><label>First name<input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></label><label>Last name<input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></label><label>Email address<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label><label>District<input value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></label><label>Phone<input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label></div>{notice && <div className="success-message"><Check size={15} />{notice}</div>}{error && <InlineNotice message={error} />}<div className="form-actions"><span>Role: {roleLabel(user.role)} · Roles are assigned by an administrator.</span><button className="button button-primary">Save changes</button></div></form></>;
}

function AuthPage({ onSignIn, onRegister, error }: { onSignIn: (username: string, password: string) => Promise<void>; onRegister: (data: Record<string, string>) => Promise<void>; error: string }) {
  const [registering, setRegistering] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(error);
  const [form, setForm] = useState({ username: "", password: "", first_name: "", last_name: "", email: "", district: "" });
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      if (registering) await onRegister(form);
      else await onSignIn(form.username, form.password);
    } catch (err) { setMessage(err instanceof Error ? err.message : "We couldn't complete your request."); }
    finally { setBusy(false); }
  }
  return <div className="auth-page"><div className="auth-left"><div className="auth-brand"><div className="brand-mark"><Leaf size={18} fill="currentColor" /></div><span>agricloud<span className="brand-ai">.ai</span></span></div><div className="auth-content"><div className="hero-kicker"><span className="live-dot" /> FARM INTELLIGENCE FOR UGANDA</div><h1>A better season<br />starts with <em>insight.</em></h1><p>Bring climate context, your farm records, and trusted local knowledge together in one place.</p><div className="auth-points"><span><Check size={15} /> NASA POWER climate observations</span><span><Check size={15} /> Transparent planting guidance</span><span><Check size={15} /> Your farm information, securely scoped</span></div></div><div className="auth-footer">Built for farmers and agricultural extension teams in Uganda.</div></div><div className="auth-right"><div className="auth-form-wrap"><div className="auth-form-eyebrow">{registering ? "CREATE YOUR ACCOUNT" : "WELCOME BACK"}</div><h2>{registering ? "Start your workspace" : "Sign in to AgriCloud"}</h2><p>{registering ? "Create an account to register your farms and explore local climate context." : "Enter your credentials to continue to your farm dashboard."}</p>{message && <InlineNotice message={message} />}<form onSubmit={submit}>{registering && <><label>First name<input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} placeholder="First name" /></label><label>Last name<input required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} placeholder="Last name" /></label><label>Email address<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" /></label><label>District <span className="optional">(optional)</span><input value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} placeholder="e.g. Wakiso" /></label></>}<label>Username<input autoComplete="username" required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="Your username" /></label><label>Password<input autoComplete={registering ? "new-password" : "current-password"} minLength={registering ? 10 : undefined} type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={registering ? "At least 10 characters" : "Enter your password"} /></label><button className="button button-primary auth-submit" disabled={busy}>{busy ? "Please wait…" : registering ? "Create account" : "Sign in"} <ChevronRight size={16} /></button></form><div className="auth-switch">{registering ? "Already have an account?" : "New to AgriCloud?"} <button onClick={() => { setRegistering(!registering); setMessage(""); }}>{registering ? "Sign in" : "Create account"}</button></div><div className="auth-secure"><ShieldAlert size={13} /> New registrations receive the farmer role. Staff roles are assigned by administrators.</div></div></div></div>;
}

function initials(user: User) { return `${user.first_name?.[0] ?? user.username[0] ?? "A"}${user.last_name?.[0] ?? ""}`.toUpperCase(); }
function roleLabel(role: User["role"]) { return role === "extension" ? "Extension worker" : role === "admin" ? "Administrator" : "Farmer"; }

export default App;
