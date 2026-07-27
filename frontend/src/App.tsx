import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  History,
  BarChart3,
  Database,
  Settings2,
  ShieldCheck,
  ChevronLeft,
} from 'lucide-react'
import { useAppStore } from '@/stores'
import { cn } from '@/lib/utils'

import Dashboard from '@/pages/Dashboard'
import ReviewDetail from '@/pages/ReviewDetail'
import ReviewHistory from '@/pages/ReviewHistory'
import Benchmark from '@/pages/Benchmark'
import ObsidianSync from '@/pages/ObsidianSync'
import SettingsPage from '@/pages/Settings'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', exact: true },
  { to: '/history', icon: History, label: 'History' },
  { to: '/benchmark', icon: BarChart3, label: 'Benchmark' },
  { to: '/obsidian', icon: Database, label: 'Obsidian' },
  { to: '/settings', icon: Settings2, label: 'Settings' },
]

function Sidebar() {
  const { sidebarOpen, setSidebarOpen } = useAppStore()

  return (
    <>
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border bg-card/80 backdrop-blur-xl transition-all duration-300',
          sidebarOpen ? 'w-60 translate-x-0' : 'w-60 -translate-x-full lg:translate-x-0 lg:w-[72px]'
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-3 px-4 border-b border-border">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <ShieldCheck className="h-4.5 w-4.5 text-primary-foreground" />
          </div>
          <span
            className={cn(
              'font-bold text-sm tracking-tight transition-opacity',
              sidebarOpen ? 'opacity-100' : 'lg:hidden'
            )}
          >
            VerifyFlow
          </span>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="hidden lg:flex absolute -right-2.5 top-4 h-5 w-5 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft
              className={cn(
                'h-3 w-3 transition-transform',
                !sidebarOpen && 'rotate-180'
              )}
            />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                onClick={() => {
                  if (window.innerWidth < 1024) setSidebarOpen(false)
                }}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                  )
                }
              >
                <Icon className="h-4.5 w-4.5 flex-shrink-0" />
                <span className={cn('transition-opacity', !sidebarOpen && 'lg:hidden')}>
                  {item.label}
                </span>
              </NavLink>
            )
          })}
        </nav>

        {/* Footer */}
        <div className={cn('border-t border-border p-4', !sidebarOpen && 'lg:hidden')}>
          <p className="text-[10px] text-muted-foreground">
            VerifyFlow v0.1.0
          </p>
        </div>
      </aside>
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 transition-all duration-300 lg:ml-[72px] ml-0">
          <div className="mx-auto max-w-5xl px-6 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/review/:id" element={<ReviewDetail />} />
              <Route path="/history" element={<ReviewHistory />} />
              <Route path="/benchmark" element={<Benchmark />} />
              <Route path="/obsidian" element={<ObsidianSync />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  )
}
