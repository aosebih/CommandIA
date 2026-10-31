import { useState, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/Layout'
import { AuthPage, Onboarding } from './pages/Auth'
import { Catalog, RulesPage } from './pages/Catalog'
import { AiSettings, Integrations, Overview } from './pages/Dashboard'
import InboxPage from './pages/Inbox'
import Orders from './pages/Orders'
import { Faq, Features, Home, How, PubFrame, Pricing } from './pages/Public'
import { Provider, useApp } from './store'

function Guard({ children, needDone = true }: { children: ReactNode; needDone?: boolean }) {
  const { auth, ready } = useApp()
  if (!auth.user) return <Navigate to="/signin" replace />
  if (needDone && !auth.done) return <Navigate to="/onboarding" replace />
  if (needDone && !ready) return <p style={{ padding: 24 }}>Loading…</p>
  return <>{children}</>
}
/** Returning authenticated users land on their dashboard when they open the site root for the first time in a session. */
function Root() {
  const { auth } = useApp()
  const [redirect] = useState(() => { const r = !!auth.user && auth.done && !sessionStorage.getItem('cmdia-booted'); sessionStorage.setItem('cmdia-booted', '1'); return r })
  return redirect ? <Navigate to="/app" replace /> : <Home />
}

export default function App() {
  return (
    <Provider><BrowserRouter><Routes>
      <Route element={<PubFrame />}>
        <Route path="/" element={<Root />} /><Route path="/features" element={<Features />} /><Route path="/how-it-works" element={<How />} /><Route path="/pricing" element={<Pricing />} /><Route path="/faq" element={<Faq />} />
        <Route path="/signin" element={<AuthPage mode="in" />} /><Route path="/signup" element={<AuthPage mode="up" />} />
      </Route>
      <Route path="/onboarding" element={<Guard needDone={false}><Onboarding /></Guard>} />
      <Route path="/app" element={<Guard><AppShell /></Guard>}>
        <Route index element={<Overview />} /><Route path="inbox" element={<InboxPage />} /><Route path="inbox/:id" element={<InboxPage />} />
        <Route path="orders" element={<Orders />} /><Route path="orders/:id" element={<Orders />} />
        <Route path="catalog" element={<Catalog />} /><Route path="rules" element={<RulesPage />} /><Route path="ai-settings" element={<AiSettings />} /><Route path="integrations" element={<Integrations />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes></BrowserRouter></Provider>
  )
}
