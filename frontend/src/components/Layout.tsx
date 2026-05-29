import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Icon } from '@/components/ui/Icon'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/',             label: 'Overview',     icon: 'dashboard' },
  { to: '/sources',      label: 'Sources',      icon: 'language' },
  { to: '/destinations', label: 'Destinations', icon: 'place' },
  { to: '/routes',       label: 'Routes',       icon: 'alt_route' },
  { to: '/deliveries',   label: 'Deliveries',   icon: 'local_shipping' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="flex h-screen bg-[#091a0d] text-slate-100 overflow-hidden">
      <aside className="w-56 flex-shrink-0 flex flex-col bg-[#0f2314] border-r border-[#1e3d24]">
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-[#1e3d24]">
          <div className="w-7 h-7 rounded-lg bg-green-600 flex items-center justify-center">
            <Icon name="bolt" size={16} className="text-white" />
          </div>
          <span className="font-semibold text-sm text-slate-100 tracking-tight">Webhook Relay</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-3 space-y-0.5">
          {navItems.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-green-600/15 text-green-400 font-medium'
                    : 'text-slate-400 hover:bg-[#183d21] hover:text-slate-100',
                )
              }
            >
              <Icon name={icon} size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User / logout */}
        <div className="border-t border-[#1e3d24] p-3">
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex items-center gap-2">
              <Icon name="person" size={15} className="text-slate-500" />
              <span className="text-xs text-slate-400 truncate">{user?.username}</span>
            </div>
            <button
              onClick={() => { logout(); navigate('/login') }}
              title="Logout"
              className="text-slate-500 hover:text-red-400 transition-colors"
            >
              <Icon name="logout" size={16} />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
