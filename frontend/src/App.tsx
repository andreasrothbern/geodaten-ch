import { useState } from 'react'
import { SearchForm } from './components/SearchForm'
import { BuildingCard } from './components/BuildingCard'
import { ApiStatus } from './components/ApiStatus'
import { ScaffoldingCard } from './components/ScaffoldingCard'
import { AusmassCard } from './components/AusmassCard'
import { MaterialCard } from './components/MaterialCard'
import { SchulaufgabenCard } from './components/SchulaufgabenCard'
import { exportToCSV, exportToPDF, prepareExportData } from './utils/export'
import type { BuildingInfo, LookupResult, ScaffoldingData } from './types'

const API_URL = import.meta.env.VITE_API_URL || ''

function App() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<LookupResult | null>(null)
  const [scaffoldingData, setScaffoldingData] = useState<ScaffoldingData | null>(null)
  const [scaffoldingLoading, setScaffoldingLoading] = useState(false)
  const [currentAddress, setCurrentAddress] = useState<string>('')
  const [fetchingHeight, setFetchingHeight] = useState(false)
  const [activeTab, setActiveTab] = useState<'scaffolding' | 'ausmass' | 'material' | 'schulaufgaben'>('scaffolding')
  // Cached data for all tabs (loaded in parallel)
  const [ausmassData, setAusmassData] = useState<any>(null)
  const [ausmassLoading, setAusmassLoading] = useState(false)

  const handleExport = (data: any, format: 'csv' | 'pdf') => {
    const exportData = prepareExportData(data)
    if (format === 'csv') {
      exportToCSV(exportData)
    } else {
      exportToPDF(exportData)
    }
  }

  const fetchScaffoldingData = async (address: string, height?: number, refresh?: boolean) => {
    setScaffoldingLoading(true)
    try {
      let url = `${API_URL}/api/v1/scaffolding?address=${encodeURIComponent(address)}`
      if (height) {
        url += `&height=${height}`
      }
      if (refresh) {
        url += `&refresh=true`
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

  const fetchAusmassData = async (address: string, dachform = 'satteldach', breitenklasse = 'W09') => {
    setAusmassLoading(true)
    try {
      const params = new URLSearchParams({
        address,
        system_id: 'blitz70',
        dachform,
        breitenklasse
      })
      const response = await fetch(`${API_URL}/api/v1/ausmass/komplett?${params}`)
      if (response.ok) {
        const data = await response.json()
        setAusmassData(data)
      }
    } catch (err) {
      console.error('Ausmass fetch error:', err)
    } finally {
      setAusmassLoading(false)
    }
  }

  const handleSearch = async (address: string) => {
    setLoading(true)
    setError(null)
    setResult(null)
    setScaffoldingData(null)
    setAusmassData(null)
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

      // Alle Tab-Daten parallel laden
      fetchScaffoldingData(address)
      fetchAusmassData(address)
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

  const handleFetchMeasuredHeight = async () => {
    if (!scaffoldingData?.address?.coordinates || !scaffoldingData?.gwr_data?.egid) {
      console.log('Missing coordinates or EGID')
      return
    }

    const { lv95_e, lv95_n } = scaffoldingData.address.coordinates
    const egid = scaffoldingData.gwr_data.egid

    console.log(`Fetching height for EGID ${egid} at E=${lv95_e}, N=${lv95_n}`)
    setFetchingHeight(true)
    setError(null)

    try {
      // Call the on-demand height fetch API
      const url = `${API_URL}/api/v1/heights/fetch-on-demand?e=${lv95_e}&n=${lv95_n}&egid=${egid}`
      console.log('Calling API:', url)

      const response = await fetch(url, { method: 'POST' })
      const data = await response.json()
      console.log('Height fetch result:', data)

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Fehler beim Abrufen der Höhe')
      }

      // Handle different response statuses
      if (data.status === 'already_exists') {
        console.log(`Height already exists in database: ${data.height_m}m`)
        if (currentAddress) {
          // Refresh to bypass cache and get updated height
          await fetchScaffoldingData(currentAddress, undefined, true)
        }
      } else if (data.status === 'success') {
        console.log(`Imported ${data.imported_count} buildings from tile ${data.tile_id}`)

        // Check if the specific EGID was found
        if (data.height_found === false) {
          // EGID not in swissBUILDINGS3D - show info message
          const sampleEgids = data.sample_egids_in_tile || []
          console.log(`EGID ${egid} not found. Sample EGIDs in tile:`, sampleEgids)
          setError(`Dieses Gebäude (EGID ${egid}) ist nicht in swissBUILDINGS3D enthalten. Möglicherweise ein Neubau oder Daten noch nicht aktualisiert. (${data.imported_count} andere Gebäude im Tile gefunden)`)
        } else if (data.height_m) {
          // Height found - reload scaffolding data with refresh to bypass cache
          console.log(`Found height: ${data.height_m}m`)
          if (currentAddress) {
            await fetchScaffoldingData(currentAddress, undefined, true)
          }
        } else {
          // Imported but EGID lookup didn't find height - reload anyway with refresh
          if (currentAddress) {
            await fetchScaffoldingData(currentAddress, undefined, true)
          }
        }
      } else if (data.status === 'no_tile_found') {
        setError('Keine swissBUILDINGS3D Daten für diesen Standort verfügbar')
      } else if (data.status === 'no_heights_found') {
        const debug = data.debug || {}
        const nullCount = debug.null_egid_count || 0
        const totalRows = debug.total_rows || 0
        setError(`Tile gefunden (${totalRows} Gebäude), aber keine mit EGID-Zuordnung (${nullCount} ohne EGID). Möglicherweise ältere Daten ohne EGID-Attribut.`)
      }
    } catch (err) {
      console.error('Height fetch error:', err)
      setError(err instanceof Error ? err.message : 'Fehler beim Abrufen der gemessenen Höhe')
    } finally {
      setFetchingHeight(false)
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

            {/* Gerüstbau-Daten mit Tabs */}
            {(scaffoldingLoading || scaffoldingData) && (
              <div className="space-y-4">
                {/* Tab Navigation */}
                <div className="flex gap-2 border-b pb-2">
                  <button
                    onClick={() => setActiveTab('scaffolding')}
                    className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                      activeTab === 'scaffolding'
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    🏗️ Gerüstbau
                  </button>
                  <button
                    onClick={() => setActiveTab('ausmass')}
                    className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                      activeTab === 'ausmass'
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    📐 NPK 114 Ausmass
                  </button>
                  <button
                    onClick={() => setActiveTab('material')}
                    className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                      activeTab === 'material'
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Materialliste
                  </button>
                  <button
                    onClick={() => setActiveTab('schulaufgaben')}
                    className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                      activeTab === 'schulaufgaben'
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Schulaufgaben
                  </button>
                </div>

                {/* Tab Content */}
                {scaffoldingLoading && (
                  <div className="card text-center py-8">
                    <p className="text-gray-500">Lade Gerüstbau-Daten...</p>
                  </div>
                )}

                {scaffoldingData && !scaffoldingLoading && (
                  <>
                    {activeTab === 'scaffolding' && (
                      <ScaffoldingCard
                        data={scaffoldingData}
                        apiUrl={API_URL}
                        onHeightChange={handleHeightChange}
                        onFetchMeasuredHeight={handleFetchMeasuredHeight}
                        fetchingHeight={fetchingHeight}
                      />
                    )}

                    {activeTab === 'ausmass' && (
                      <AusmassCard
                        address={currentAddress}
                        coordinates={scaffoldingData.address?.coordinates}
                        apiUrl={API_URL}
                        onExport={(data) => handleExport(data, 'pdf')}
                        cachedData={ausmassData}
                        loading={ausmassLoading}
                        onRefetch={(dachform, breitenklasse) => fetchAusmassData(currentAddress, dachform, breitenklasse)}
                      />
                    )}

                    {activeTab === 'material' && scaffoldingData.scaffolding?.estimated_scaffold_area_m2 && (
                      <MaterialCard
                        scaffoldAreaM2={scaffoldingData.scaffolding.estimated_scaffold_area_m2}
                        apiUrl={API_URL}
                      />
                    )}

                    {activeTab === 'schulaufgaben' && (
                      <SchulaufgabenCard
                        address={currentAddress}
                        apiUrl={API_URL}
                      />
                    )}

                    {/* Export Buttons */}
                    <div className="flex justify-end gap-2 mt-4">
                      <button
                        onClick={() => {
                          // Fetch ausmass data and export as CSV
                          fetch(`${API_URL}/api/v1/ausmass/komplett?address=${encodeURIComponent(currentAddress)}`)
                            .then(r => r.json())
                            .then(data => handleExport(data, 'csv'))
                            .catch(console.error)
                        }}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                      >
                        📊 CSV Export
                      </button>
                      <button
                        onClick={() => {
                          fetch(`${API_URL}/api/v1/ausmass/komplett?address=${encodeURIComponent(currentAddress)}`)
                            .then(r => r.json())
                            .then(data => handleExport(data, 'pdf'))
                            .catch(console.error)
                        }}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                      >
                        📄 PDF Drucken
                      </button>
                    </div>
                  </>
                )}
              </div>
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
            {' | '}
            <a
              href="https://map.geo.admin.ch/?topic=ech&lang=de&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.swisstopo.swissbuildings3d&3d=true"
              target="_blank"
              rel="noopener noreferrer"
              className="text-red-600 hover:underline"
            >
              3D Viewer
            </a>
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
