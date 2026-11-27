import React from "react";
import ReactDOM from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./styles.css";
import App from "./App";

class AppErrorBoundary extends React.Component<React.PropsWithChildren, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return <main className="fatal-error"><div className="brand-mark">!</div><h1>Something went wrong</h1><p>The page could not be displayed. Reload to try again.</p><button onClick={() => window.location.reload()}>Reload AgriCloud</button></main>;
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </React.StrictMode>,
);

// Remove the app-shell worker and cache installed by the retired offline module.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.getRegistrations().then((registrations) =>
      Promise.all(registrations.filter((registration) =>
        [registration.active, registration.waiting, registration.installing]
          .some((worker) => worker?.scriptURL === `${window.location.origin}/sw.js`),
      ).map((registration) => registration.unregister())),
    );
  });
}
if ("caches" in window) {
  void caches.keys().then((keys) => Promise.all(
    keys.filter((key) => key.startsWith("agricloud-shell-")).map((key) => caches.delete(key)),
  ));
}
