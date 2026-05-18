'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Building2, Target, Briefcase,
  FileText, Kanban, Activity, Settings, Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { href: '/dashboard',  label: 'Dashboard',   icon: LayoutDashboard },
  { href: '/jobs',       label: 'Job Matches',  icon: Briefcase },
  { href: '/companies',  label: 'Companies',    icon: Building2 },
  { href: '/profiles',   label: 'Profiles',     icon: Target },
  { href: '/resumes',    label: 'Resume AI',    icon: FileText },
  { href: '/tracker',    label: 'Tracker',      icon: Kanban },
  { href: '/logs',       label: 'Logs',         icon: Activity },
  { href: '/settings',   label: 'Settings',     icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-[220px] shrink-0 flex flex-col bg-surface-0 border-r border-surface-4 h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-surface-4">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded bg-accent-blue flex items-center justify-center shrink-0">
            <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <p className="text-sm font-semibold text-text-1 leading-tight">Job Hunter</p>
            <p className="text-2xs text-text-3 font-mono">personal</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors',
                active
                  ? 'bg-accent-blue/10 text-accent-blue font-medium'
                  : 'text-text-2 hover:bg-surface-3 hover:text-text-1'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" strokeWidth={active ? 2.5 : 2} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-surface-4">
        <p className="text-2xs text-text-3 font-mono">v0.1.0</p>
      </div>
    </aside>
  )
}
