import { NavLink } from 'react-router-dom'
import { Home, FolderOpen, PlusCircle, Settings } from 'lucide-react'

export function BottomNav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex flex-col items-center py-2 px-4 ${
      isActive ? 'text-primary-600' : 'text-gray-500'
    }`

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
      <div className="flex justify-around max-w-lg mx-auto">
        <NavLink to="/" className={linkClass}>
          <Home size={24} />
          <span className="text-xs mt-1">Home</span>
        </NavLink>
        <NavLink to="/projects" className={linkClass}>
          <FolderOpen size={24} />
          <span className="text-xs mt-1">Projekte</span>
        </NavLink>
        <NavLink to="/projects/new" className={linkClass}>
          <PlusCircle size={24} />
          <span className="text-xs mt-1">Neu</span>
        </NavLink>
        <NavLink to="/settings" className={linkClass}>
          <Settings size={24} />
          <span className="text-xs mt-1">Einstellungen</span>
        </NavLink>
      </div>
    </nav>
  )
}
