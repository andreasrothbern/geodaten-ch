import { Routes, Route, useLocation } from 'react-router-dom'
import { BottomNav } from './components/layout/BottomNav'
import { Header } from './components/layout/Header'
import HomePage from './pages/HomePage'
import ProjectsPage from './pages/ProjectsPage'
import NewProjectPage from './pages/NewProjectPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import ConfiguratorPage from './pages/ConfiguratorPage'
import PhotosPage from './pages/PhotosPage'

function App() {
  const location = useLocation();

  // Hide header/nav on configurator page (has its own layout)
  const isConfiguratorPage = location.pathname === '/configurator';

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      {!isConfiguratorPage && <Header />}
      <main className={isConfiguratorPage ? '' : 'container mx-auto px-4 py-4 max-w-lg'}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/configurator" element={<ConfiguratorPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/new" element={<NewProjectPage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage />} />
          <Route path="/projects/:id/photos" element={<PhotosPage />} />
          <Route path="/projects/:id/scaffold" element={<div className="text-center py-8">Gerüst - Coming Soon</div>} />
          <Route path="/settings" element={<div className="text-center py-8">Einstellungen - Coming Soon</div>} />
        </Routes>
      </main>
      {!isConfiguratorPage && <BottomNav />}
    </div>
  )
}

export default App
