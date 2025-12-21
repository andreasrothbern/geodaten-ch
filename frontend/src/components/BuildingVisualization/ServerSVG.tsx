import { useState, useEffect } from 'react'

interface ServerSVGProps {
  /** API endpoint type */
  type: 'cross-section' | 'elevation' | 'floor-plan'
  /** Address to visualize */
  address: string
  /** API base URL */
  apiUrl: string
  /** SVG width */
  width?: number
  /** SVG height */
  height?: number
  /** Additional CSS classes */
  className?: string
}

/**
 * Lädt SVG-Visualisierungen vom Backend-Server
 * Professionelle Darstellung im Showcase-Stil
 */
export function ServerSVG({
  type,
  address,
  apiUrl,
  width = 700,
  height = 480,
  className = ''
}: ServerSVGProps) {
  const [svg, setSvg] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!address) {
      setLoading(false)
      return
    }

    const fetchSVG = async () => {
      setLoading(true)
      setError(null)

      try {
        const params = new URLSearchParams({
          address,
          width: width.toString(),
          height: height.toString()
        })

        const response = await fetch(`${apiUrl}/api/v1/visualize/${type}?${params}`)

        if (!response.ok) {
          throw new Error(`Fehler beim Laden: ${response.status}`)
        }

        const svgText = await response.text()
        setSvg(svgText)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unbekannter Fehler')
      } finally {
        setLoading(false)
      }
    }

    fetchSVG()
  }, [type, address, apiUrl, width, height])

  if (loading) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 rounded-lg ${className}`}
        style={{ width, height }}
      >
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-red-600 border-t-transparent rounded-full mx-auto mb-2"></div>
          <p className="text-gray-500 text-sm">Lade Visualisierung...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div
        className={`flex items-center justify-center bg-red-50 rounded-lg border border-red-200 ${className}`}
        style={{ width, height }}
      >
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    )
  }

  if (!svg) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 rounded-lg ${className}`}
        style={{ width, height }}
      >
        <p className="text-gray-500 text-sm">Keine Visualisierung verfügbar</p>
      </div>
    )
  }

  // SVG als HTML rendern
  return (
    <div
      className={`rounded-lg overflow-hidden border ${className}`}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}

/**
 * Tabs für alle drei Visualisierungstypen
 */
interface VisualizationTabsProps {
  address: string
  apiUrl: string
}

export function VisualizationTabs({ address, apiUrl }: VisualizationTabsProps) {
  const [activeTab, setActiveTab] = useState<'cross-section' | 'elevation' | 'floor-plan'>('cross-section')

  const tabs = [
    { id: 'cross-section' as const, label: 'Schnitt', icon: '📐' },
    { id: 'elevation' as const, label: 'Ansicht', icon: '🏛️' },
    { id: 'floor-plan' as const, label: 'Grundriss', icon: '📋' },
  ]

  return (
    <div className="space-y-4">
      {/* Tab Navigation */}
      <div className="flex gap-2 border-b pb-2">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-t-lg font-medium transition-colors flex items-center gap-2 ${
              activeTab === tab.id
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* SVG Content */}
      <ServerSVG
        type={activeTab}
        address={address}
        apiUrl={apiUrl}
        width={700}
        height={activeTab === 'floor-plan' ? 500 : 480}
      />

      {/* Download Button */}
      <div className="flex justify-end">
        <a
          href={`${apiUrl}/api/v1/visualize/${activeTab}?address=${encodeURIComponent(address)}&width=1000&height=700`}
          download={`${activeTab}_${address.replace(/[^a-zA-Z0-9]/g, '_')}.svg`}
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
        >
          <span>💾</span> SVG herunterladen
        </a>
      </div>
    </div>
  )
}
