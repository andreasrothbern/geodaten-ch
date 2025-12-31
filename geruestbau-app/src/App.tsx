import { Routes, Route } from 'react-router-dom'
import { BottomNav } from './components/layout/BottomNav'
import { Header } from './components/layout/Header'
import HomePage from './pages/HomePage'
import ProjectsPage from './pages/ProjectsPage'
import NewProjectPage from './pages/NewProjectPage'
import ProjectDetailPage from './pages/ProjectDetailPage'

function App() {
  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <Header />
      <main className="container mx-auto px-4 py-4 max-w-lg">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/new" element={<NewProjectPage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage />} />
          <Route path="/projects/:id/photos" element={<div className="text-center py-8">Fotos - Coming Soon</div>} />
          <Route path="/projects/:id/scaffold" element={<div className="text-center py-8">Gerüst - Coming Soon</div>} />
          <Route path="/settings" element={<div className="text-center py-8">Einstellungen - Coming Soon</div>} />
        </Routes>
      </main>
      <BottomNav />
    </div>
  )
}

export default App
