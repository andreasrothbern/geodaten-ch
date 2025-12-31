import { Link } from 'react-router-dom'
import { FolderPlus, List, BarChart3 } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div className="text-center py-8">
        <div className="w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-4xl">🏗️</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Gerüstbau App</h2>
      </div>

      <div className="grid gap-4">
        <Link to="/projects/new" className="card flex items-center gap-4">
          <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
            <FolderPlus className="text-primary-600" size={24} />
          </div>
          <div>
            <h3 className="font-semibold">Neues Projekt</h3>
            <p className="text-sm text-gray-500">Ausschreibung erfassen</p>
          </div>
        </Link>

        <Link to="/projects" className="card flex items-center gap-4">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
            <List className="text-blue-600" size={24} />
          </div>
          <div>
            <h3 className="font-semibold">Meine Projekte</h3>
            <p className="text-sm text-gray-500">Übersicht und Status</p>
          </div>
        </Link>

        <Link to="/stats" className="card flex items-center gap-4">
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
            <BarChart3 className="text-green-600" size={24} />
          </div>
          <div>
            <h3 className="font-semibold">Statistiken</h3>
            <p className="text-sm text-gray-500">Auswertungen</p>
          </div>
        </Link>
      </div>

      <div className="text-center text-xs text-gray-400 mt-8">
        Version 0.1.0
      </div>
    </div>
  )
}
