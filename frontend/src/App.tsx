import { Routes, Route, Navigate, Link } from 'react-router-dom'
import AdvisorWorkspace from '@/routes/AdvisorWorkspace'
import ClientPortal from '@/routes/ClientPortal'
import ContactCentre from '@/routes/ContactCentre'
import AgentTrace from '@/routes/AgentTrace'
import AdminConfig from '@/routes/AdminConfig'

function NavBar() {
  return (
    <nav className="flex gap-4 bg-gray-900 px-6 py-3 text-sm text-gray-300">
      <span className="mr-4 font-semibold text-white">GlideGate</span>
      <Link to="/" className="hover:text-white">Advisor Workspace</Link>
      <Link to="/client" className="hover:text-white">Client Portal</Link>
      <Link to="/contact-centre" className="hover:text-white">Contact Centre</Link>
      <Link to="/agent-trace" className="hover:text-white">Agent Trace</Link>
      <Link to="/admin" className="hover:text-white">Admin Config</Link>
    </nav>
  )
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <NavBar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<AdvisorWorkspace />} />
          <Route path="/client" element={<ClientPortal />} />
          <Route path="/contact-centre" element={<ContactCentre />} />
          <Route path="/agent-trace" element={<AgentTrace />} />
          <Route path="/admin" element={<AdminConfig />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
