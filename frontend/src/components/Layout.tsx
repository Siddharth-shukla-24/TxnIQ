import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Upload,
  List,
  Menu,
  Github,
  X,
} from 'lucide-react'
import clsx from 'clsx'
import logo from '../assets/logo.png'

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Upload CSV' },
  { to: '/jobs', icon: List, label: 'Job History' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const pageTitle =
    NAV_ITEMS.find((item) =>
      item.to === '/'
        ? location.pathname === '/'
        : location.pathname.startsWith(item.to)
    )?.label ?? 'Job Detail'

  useEffect(() => {
    document.title = `${pageTitle} • TxnIQ`
  }, [pageTitle])

  return (
    <div className="flex h-screen bg-[#0a0a0a] overflow-hidden">
      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-56 bg-[#0d0d0d] border-r border-[#161616]',
          'flex flex-col transition-transform duration-200 ease-in-out',
          'lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Brand */}
        <div className="flex items-center justify-between px-5 h-20 border-b border-white/5 bg-[#0d0d0d] flex-shrink-0">
          <div className="flex items-center gap-3.5 min-w-0">
            {/* Logo */}
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500/10 via-blue-500/10 to-cyan-500/10 border border-sky-500/20 shadow-lg shadow-sky-500/[0.08] flex items-center justify-center overflow-hidden flex-shrink-0">
              <img
                src={logo}
                alt="TxnIQ logo"
                className="w-7 h-7 object-contain"
              />
            </div>

            {/* Brand text */}
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-[16px] font-bold tracking-tight text-white leading-none">
                  TxnIQ
                </h1>
                <span className="rounded-full border border-sky-500/20 bg-sky-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-sky-400 leading-none">
                  AI
                </span>
              </div>
              <p className="mt-1 text-[11px] tracking-wide text-zinc-500 truncate">
                Transaction Intelligence
              </p>
            </div>
          </div>

          {/* Mobile close */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden rounded-xl p-2 text-zinc-500 transition-all duration-200 hover:bg-white/5 hover:text-white"
            aria-label="Close sidebar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto" aria-label="Main navigation">
          <p className="section-label px-3 mb-3">Menu</p>
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-white/[0.06] text-white'
                    : 'text-[#666] hover:text-[#ccc] hover:bg-white/[0.03]'
                )
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-[#161616]">
          <a
            href="https://github.com/Siddharth-shukla-24/ai-transaction-pipeline"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-xs text-[#555] hover:text-[#999] transition-colors"
          >
            <Github className="w-3.5 h-3.5" />
            View on GitHub
          </a>
        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="flex items-center gap-4 px-6 h-14 border-b border-[#161616] bg-[#0d0d0d] flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-[#555] hover:text-white transition-colors"
            aria-label="Open sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>
          <span className="text-sm font-semibold text-white">{pageTitle}</span>
          <div className="ml-auto flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse-slow" />
            <span className="text-xs text-[#555]">Live</span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  )
}