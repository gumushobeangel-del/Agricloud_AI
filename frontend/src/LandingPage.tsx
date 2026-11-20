import { Leaf, ChevronRight, CloudSun, Sprout, BarChart3, Droplets, Store, Bug, MapPin, ShieldAlert, Check, Activity, TrendingUp } from "lucide-react";

interface LandingPageProps {
  onGetStarted: () => void;
}

const features = [
  {
    icon: <CloudSun size={20} />,
    title: "Weather Intelligence",
    description: "Live model-based conditions and NASA POWER historical climate observations for your exact farm location.",
    tone: "blue",
  },
  {
    icon: <Sprout size={20} />,
    title: "Planting Advisor",
    description: "AI-powered crop recommendations matched to your soil type, climate data, and local growing conditions.",
    tone: "green",
  },
  {
    icon: <Bug size={20} />,
    title: "Crop Disease Detection",
    description: "Upload a photo of a sick crop and get an instant AI diagnosis with actionable treatment advice.",
    tone: "lime",
  },
  {
    icon: <Droplets size={20} />,
    title: "Smart Irrigation",
    description: "Personalised irrigation plans based on crop water needs, local rainfall, and your farm's soil profile.",
    tone: "blue",
  },
  {
    icon: <BarChart3 size={20} />,
    title: "Yield Forecast",
    description: "Estimate your harvest from recorded production history and district benchmarks with climate risk signals.",
    tone: "lime",
  },
  {
    icon: <Store size={20} />,
    title: "Market Intelligence",
    description: "Live and historical commodity prices from WFP and official sources — find the best market for your crop.",
    tone: "orange",
  },
  {
    icon: <MapPin size={20} />,
    title: "Field Monitoring",
    description: "Interactive map of all your registered farm locations with real-time satellite tile overlays.",
    tone: "green",
  },
  {
    icon: <TrendingUp size={20} />,
    title: "Farm Analytics",
    description: "Reports and trend charts across all your farms — crop distribution, area totals, and production history.",
    tone: "orange",
  },
];

const stats = [
  { value: "10+", label: "AI-powered tools" },
  { value: "NASA", label: "POWER climate data" },
  { value: "Live", label: "weather & market feeds" },
  { value: "Free", label: "for farmers" },
];

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  return (
    <div className="landing-page">
      {/* ── NAV ─────────────────────────────────────────── */}
      <nav className="landing-nav">
        <div className="landing-nav-brand">
          <div className="brand-mark"><Leaf size={18} fill="currentColor" /></div>
          <span>agricloud<span className="brand-ai">.ai</span></span>
        </div>
        <div className="landing-nav-actions">
          <button className="button button-secondary button-small" onClick={onGetStarted}>Sign in</button>
          <button className="button button-primary button-small" onClick={onGetStarted}>Get started free</button>
        </div>
      </nav>

      {/* ── HERO ────────────────────────────────────────── */}
      <section className="landing-hero">
        <div className="landing-hero-bg" aria-hidden />
        <div className="landing-hero-inner">
          <div className="landing-hero-eyebrow">
            <span className="live-dot" />
            FARM INTELLIGENCE · BUILT FOR UGANDA
          </div>
          <h1 className="landing-hero-title">
            Grow smarter with<br />
            <em className="landing-hero-em">AI-powered farming</em>
          </h1>
          <p className="landing-hero-sub">
            AgriCloud brings climate data, crop intelligence, disease detection,
            market prices, and irrigation planning together in one platform built
            for Ugandan smallholder farmers and agricultural extension teams.
          </p>
          <div className="landing-hero-cta">
            <button className="button button-primary landing-cta-primary" onClick={onGetStarted}>
              Start for free <ChevronRight size={17} />
            </button>
            <button className="button button-secondary" onClick={onGetStarted}>
              Sign in to your workspace
            </button>
          </div>
          <div className="landing-hero-checks">
            <span><Check size={14} /> No credit card required</span>
            <span><Check size={14} /> Free farmer accounts</span>
            <span><Check size={14} /> Data stays secure</span>
          </div>
        </div>

        {/* Hero visual card */}
        <div className="landing-hero-card" aria-hidden>
          <div className="landing-hero-card-header">
            <div className="landing-card-dot green" /><div className="landing-card-dot yellow" /><div className="landing-card-dot red" />
            <span>agricloud.ai · dashboard</span>
          </div>
          <div className="landing-card-metric-row">
            <div className="landing-card-metric">
              <span className="landing-card-label"><Activity size={11} /> Total fields</span>
              <strong>8</strong>
              <small>Registered farm locations</small>
            </div>
            <div className="landing-card-metric">
              <span className="landing-card-label"><Sprout size={11} /> Total area</span>
              <strong>24.5 ha</strong>
              <small>Across saved records</small>
            </div>
            <div className="landing-card-metric">
              <span className="landing-card-label"><CloudSun size={11} /> Observed days</span>
              <strong>90</strong>
              <small>NASA POWER · historical</small>
            </div>
          </div>
          <div className="landing-card-chart-wrap">
            <div className="landing-card-chart-label">Rainfall · Temperature</div>
            <div className="landing-card-chart">
              {[18, 30, 22, 45, 12, 55, 38, 20, 48, 35, 25, 60].map((h, i) => (
                <div key={i} className="landing-chart-bar" style={{ height: `${h}%` }} />
              ))}
            </div>
          </div>
          <div className="landing-card-status">
            <span className="live-dot" /> Live — refreshed every 15 minutes · Open-Meteo
          </div>
        </div>
      </section>

      {/* ── STATS ───────────────────────────────────────── */}
      <div className="landing-stats">
        {stats.map((s) => (
          <div key={s.label} className="landing-stat">
            <strong>{s.value}</strong>
            <span>{s.label}</span>
          </div>
        ))}
      </div>

      {/* ── FEATURES ────────────────────────────────────── */}
      <section className="landing-features">
        <div className="landing-section-label">
          <span className="live-dot" /> PLATFORM FEATURES
        </div>
        <h2 className="landing-section-title">
          Everything a Ugandan farmer needs in one place
        </h2>
        <p className="landing-section-sub">
          From planting advice to market prices — powered by real data sources and AI.
        </p>
        <div className="landing-feature-grid">
          {features.map((f) => (
            <div key={f.title} className="landing-feature-card">
              <div className={`landing-feature-icon metric-icon ${f.tone}`}>{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── HOW IT WORKS ────────────────────────────────── */}
      <section className="landing-how">
        <div className="landing-section-label">
          <span className="live-dot" /> HOW IT WORKS
        </div>
        <h2 className="landing-section-title">Up and running in minutes</h2>
        <div className="landing-steps">
          <div className="landing-step">
            <div className="landing-step-num">01</div>
            <h3>Create your free account</h3>
            <p>Register as a farmer or agricultural extension worker. No credit card or subscription needed.</p>
          </div>
          <div className="landing-step-arrow"><ChevronRight size={20} /></div>
          <div className="landing-step">
            <div className="landing-step-num">02</div>
            <h3>Add your farm locations</h3>
            <p>Enter your farm's GPS coordinates from Google Maps to unlock climate data and local intelligence.</p>
          </div>
          <div className="landing-step-arrow"><ChevronRight size={20} /></div>
          <div className="landing-step">
            <div className="landing-step-num">03</div>
            <h3>Get AI-powered insights</h3>
            <p>Access weather, planting advice, disease detection, yield forecasts, and market prices immediately.</p>
          </div>
        </div>
      </section>

      {/* ── TRUST BADGES ────────────────────────────────── */}
      <section className="landing-trust">
        <div className="landing-trust-inner">
          <div className="landing-trust-badge">
            <ShieldAlert size={18} />
            <div>
              <strong>NASA POWER Data</strong>
              <span>Satellite-informed daily climate observations for every registered farm location.</span>
            </div>
          </div>
          <div className="landing-trust-badge">
            <CloudSun size={18} />
            <div>
              <strong>Open-Meteo Forecasts</strong>
              <span>Open-source weather API providing real-time model-based conditions and 7-day outlooks.</span>
            </div>
          </div>
          <div className="landing-trust-badge">
            <Store size={18} />
            <div>
              <strong>WFP Market Prices</strong>
              <span>Official commodity price data from the World Food Programme and district sources.</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA BANNER ──────────────────────────────────── */}
      <section className="landing-cta-section">
        <div className="landing-cta-inner">
          <div className="brand-mark landing-cta-logo"><Leaf size={22} fill="currentColor" /></div>
          <h2>Ready to farm smarter?</h2>
          <p>Join farmers and extension workers across Uganda using AgriCloud.ai to make better decisions every season.</p>
          <button className="button button-primary landing-cta-primary" onClick={onGetStarted}>
            Create your free account <ChevronRight size={16} />
          </button>
        </div>
      </section>

      {/* ── FOOTER ──────────────────────────────────────── */}
      <footer className="landing-footer">
        <div className="landing-nav-brand">
          <div className="brand-mark"><Leaf size={16} fill="currentColor" /></div>
          <span>agricloud<span className="brand-ai">.ai</span></span>
        </div>
        <span>Built for farmers and agricultural extension teams in Uganda.</span>
        <button className="auth-link" onClick={onGetStarted}>Sign in →</button>
      </footer>
    </div>
  );
}
