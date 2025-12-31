import { useLocation } from 'react-router-dom'

const titles: Record<string, string> = {
  '/': 'Gerüstbau',
  '/projects': 'Projekte',
  '/projects/new': 'Neues Projekt',
  '/settings': 'Einstellungen',
}

export function Header() {
  const location = useLocation()

  // Handle dynamic routes
  let title = titles[location.pathname]
  if (!title && location.pathname.startsWith('/projects/')) {
    title = 'Projekt Details'
  }
  title = title || 'Gerüstbau'

  return (
    <header className="bg-primary-600 text-white px-4 py-4 sticky top-0 z-50">
      <h1 className="text-xl font-semibold text-center">{title}</h1>
    </header>
  )
}
