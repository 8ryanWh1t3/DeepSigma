// ─────────────────────────────────────────────────────────────
// router.tsx – Lightweight hash-based router for the dashboard
// ─────────────────────────────────────────────────────────────
// NOTE: The existing dashboard uses a tab-based App component
// without a router. This module provides an opt-in route for
// /inbox that renders the Exhaust Inbox page. It can be
// integrated into main.tsx or used standalone.
// ─────────────────────────────────────────────────────────────
import React, { useEffect, useState } from "react";
import ExhaustInbox from "./pages/ExhaustInbox";

/**
 * Routes:
 *   #/inbox  → ExhaustInbox
 *   (default) → null (caller renders normal App)
 */
export function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return hash;
}

interface Props {
  fallback: React.ReactNode;
}

/**
 * Wrap your App in <HashRouter fallback={<App />} /> to enable
 * hash-based routing while keeping the existing layout as default.
 *
 * Usage in main.tsx:
 *   import { HashRouter } from "./router";
 *   ReactDOM.createRoot(root).render(
 *     <HashRouter fallback={<App />} />
 *   );
 */
export function HashRouter({ fallback }: Props) {
  const hash = useHashRoute();

  if (hash === "#/inbox" || hash === "#/inbox/") {
    return <ExhaustInbox />;
  }

  // Default: render existing app
  return <>{fallback}</>;
}

export default HashRouter;
