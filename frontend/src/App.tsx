import { useState } from 'react'
import { SearchForm } from './components/SearchForm'
import { BuildingCard } from './components/BuildingCard'
import { ApiStatus } from './components/ApiStatus'
import { ScaffoldingCard } from './components/ScaffoldingCard'
import type { BuildingInfo, LookupResult, ScaffoldingData } from './types'

const API_URL = import.meta.env.VITE_API_URL || ''

function App() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<LookupResult | null>(null)
  const [scaffoldingData, setScaffoldingData] = useState<ScaffoldingData | null>(null)
  const [scaffoldingLoading, setScaffoldingLoading] = useState(false)
  const [currentAddress, setCurrentAddress] = useState<string>('')

  const fetchScaffoldingData = async (address: string, height?: number) => {
    setScaffoldingLoading(true)
    try {
      let url = `${API_URL}/api/v1/scaffolding?address=${encodeURIComponent(address)}`
      if (height) {
        url += `&height=${height}`
      }
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setScaffoldingData(data)
      }
    } catch (err) {
      console.error('Scaffolding fetch error:', err)
    } finally {
      setScaffoldingLoading(false)
    }
  }

  const handleSearch = async (address: string) => {
    setLoading(true)
    setError(null)
    setResult(null)
    setScaffoldingData(null)
    setCurrentAddress(address)

    try {
      const response = await fetch(
        `${API_URL}/api/v1/lookup?address=${encodeURIComponent(address)}`
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Fehler bei der Suche')
      }

      const data = await response.json()
      setResult(data)

      // Automatisch Gerüstbau-Daten laden
      fetchScaffoldingData(address)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler')
    } finally {
      setLoading(false)
    }
  }

  const handleHeightChange = (height: number) => {
    if (currentAddress) {
      fetchScaffoldingData(currentAddress, height)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-red-600 text-white shadow-lg">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🇨🇭</span>
            <div>
              <h1 className="text-2xl font-bold">Geodaten Schweiz</h1>
              <p className="text-red-100 text-sm">
                Gebäude- und Grundstücksinformationen
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* API Status */}
        <ApiStatus apiUrl={API_URL} />

        {/* Search Form */}
        <div className="card mb-8">
          <h2 className="text-xl font-semibold mb-4">Adresse suchen</h2>
          <SearchForm onSearch={handleSearch} loading={loading} />
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            <strong>Fehler:</strong> {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Address Info */}
            <div className="card">
              <h3 className="text-lg font-semibold mb-2">📍 Gefundene Adresse</h3>
              <p className="text-gray-700">{result.address.matched_address}</p>
              <div className="mt-2 text-sm text-gray-500">
                <p>
                  Koordinaten (LV95): E {result.address.coordinates.lv95_e.toFixed(1)}, 
                  N {result.address.coordinates.lv95_n.toFixed(1)}
                </p>
                <p>Konfidenz: {(result.address.confidence * 100).toFixed(0)}%</p>
              </div>
            </div>

            {/* Buildings */}
            <div>
              <h3 className="text-lg font-semibold mb-4">
                🏠 Gebäude ({result.buildings_count})
              </h3>

              {result.buildings_count === 0 ? (
                <p className="text-gray-500">
                  Keine Gebäude an dieser Adresse gefunden.
                </p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {result.buildings.map((building: BuildingInfo) => (
                    <BuildingCard key={building.egid} building={building} />
                  ))}
                </div>
              )}
            </div>

            {/* Gerüstbau-Daten */}
            {scaffoldingLoading && (
              <div className="card text-center py-8">
                <p className="text-gray-500">Lade Gerüstbau-Daten...</p>
              </div>
            )}

            {scaffoldingData && !scaffoldingLoading && (
              <ScaffoldingCard
                data={scaffoldingData}
                onHeightChange={handleHeightChange}
              />
            )}
          </div>
        )}

        {/* Empty State */}
        {!result && !error && !loading && (
          <div className="text-center py-12 text-gray-500">
            <p className="text-5xl mb-4">🏡</p>
            <p>Geben Sie eine Adresse ein, um Gebäudeinformationen abzurufen.</p>
            <p className="text-sm mt-2">
              Beispiel: Bundesplatz 3, 3011 Bern
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 border-t mt-12">
        <div className="max-w-6xl mx-auto px-4 py-6 text-center text-sm text-gray-500">
          <p>
            Daten: © swisstopo, BFS/GWR | 
            <a 
              href="https://api3.geo.admin.ch" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-red-600 hover:underline ml-1"
            >
              geo.admin.ch
            </a>
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
