import { useState, useEffect, useRef } from 'react'

// Global cache for SVGs to persist across component remounts
const svgCache = new Map<string, string>()

// Clear cache for a specific address (when address changes)
export function clearSvgCache(address?: string) {
  if (address) {
    // Clear only entries for this address
    for (const key of svgCache.keys()) {
      if (key.includes(address)) {
        svgCache.delete(key)
      }
    }
  } else {
    svgCache.clear()
  }
}

// Preload all visualization types for an address
export async function preloadAllSvgs(
  address: string,
  apiUrl: string,
  width = 650,
  heights = { 'cross-section': 400, 'elevation': 400, 'floor-plan': 450 }
) {
  const types: Array<'cross-section' | 'elevation' | 'floor-plan'> = ['cross-section', 'elevation', 'floor-plan']

  await Promise.all(types.map(async (type) => {
    const height = heights[type]
    const cacheKey = `${type}|${address}|${width}|${height}`

    // Skip if already cached
    if (svgCache.has(cacheKey)) return

    try {
      const params = new URLSearchParams({
        address,
        width: width.toString(),
        height: height.toString()
      })
      // Use Claude API for cross-section and elevation
      if (type === 'cross-section' || type === 'elevation') {
        params.set('use_claude', 'true')
      }
      const response = await fetch(`${apiUrl}/api/v1/visualize/${type}?${params}`)
      if (response.ok) {
        const svgText = await response.text()
        svgCache.set(cacheKey, svgText)
      }
    } catch (err) {
      console.error(`Failed to preload ${type}:`, err)
    }
  }))
}

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
  /** Manual eave height (Traufhöhe) to override database value */
  traufhoehe?: number
  /** Manual ridge height (Firsthöhe) to override database value */
  firsthoehe?: number
  /** Professional mode with hatch patterns */
  professional?: boolean
}

/**
 * Lädt SVG-Visualisierungen vom Backend-Server
 * Mit Cache um wiederholtes Laden zu vermeiden
 */
export function ServerSVG({
  type,
  address,
  apiUrl,
  width = 700,
  height = 480,
  className = '',
  traufhoehe,
  firsthoehe,
  professional = false
}: ServerSVGProps) {
  const [svg, setSvg] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const fetchedRef = useRef<string | null>(null)

  // Cache key includes manual heights, professional mode, and claude
  const useClaude = type === 'cross-section' || type === 'elevation'
  const cacheKey = `${type}|${address}|${width}|${height}|${traufhoehe || ''}|${firsthoehe || ''}|${professional}|${useClaude}`

  useEffect(() => {
    if (!address) {
      setLoading(false)
      return
    }

    // Check cache first
    const cached = svgCache.get(cacheKey)
    if (cached) {
      setSvg(cached)
      setLoading(false)
      return
    }

    // Prevent duplicate fetches
    if (fetchedRef.current === cacheKey) {
      return
    }
    fetchedRef.current = cacheKey

    const fetchSVG = async () => {
      setLoading(true)
      setError(null)

      try {
        const params = new URLSearchParams({
          address,
          width: width.toString(),
          height: height.toString()
        })
        // Add manual heights if provided
        if (traufhoehe && traufhoehe > 0) {
          params.set('traufhoehe', traufhoehe.toString())
        }
        if (firsthoehe && firsthoehe > 0) {
          params.set('firsthoehe', firsthoehe.toString())
        }
        // Add professional mode
        if (professional) {
          params.set('professional', 'true')
        }
        // Use Claude API for cross-section and elevation
        if (type === 'cross-section' || type === 'elevation') {
          params.set('use_claude', 'true')
        }

        const url = `${apiUrl}/api/v1/visualize/${type}?${params}`
        console.log(`[SVG] Fetching: ${url}`)

        // 120 second timeout for Claude API calls
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 120000)

        const response = await fetch(url, { signal: controller.signal })
        clearTimeout(timeoutId)

        console.log(`[SVG] Response status: ${response.status}`)

        if (!response.ok) {
          throw new Error(`Fehler beim Laden: ${response.status}`)
        }

        const svgText = await response.text()
        console.log(`[SVG] Received ${svgText.length} chars`)

        // Store in cache
        svgCache.set(cacheKey, svgText)
        setSvg(svgText)
      } catch (err) {
        console.error(`[SVG] Error:`, err)
        if (err instanceof Error && err.name === 'AbortError') {
          setError('Timeout: SVG-Generierung dauerte zu lange')
        } else {
          setError(err instanceof Error ? err.message : 'Unbekannter Fehler')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchSVG()
  }, [cacheKey, address, apiUrl, type, width, height])

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
  const [professional, setProfessional] = useState(false)

  const tabs = [
    { id: 'cross-section' as const, label: 'Schnitt', icon: '📐' },
    { id: 'elevation' as const, label: 'Ansicht', icon: '🏛️' },
    { id: 'floor-plan' as const, label: 'Grundriss', icon: '📋' },
  ]

  return (
    <div className="space-y-4">
      {/* Tab Navigation + Professional Toggle */}
      <div className="flex items-center justify-between border-b pb-2">
        <div className="flex gap-2">
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
        {/* Professional Toggle */}
        <label className="flex items-center gap-2 cursor-pointer">
          <span className="text-xs text-gray-500">Professional</span>
          <div className="relative">
            <input
              type="checkbox"
              checked={professional}
              onChange={(e) => setProfessional(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-red-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-red-600"></div>
          </div>
        </label>
      </div>

      {/* SVG Content */}
      <ServerSVG
        type={activeTab}
        address={address}
        apiUrl={apiUrl}
        width={700}
        height={activeTab === 'floor-plan' ? 500 : 480}
        professional={professional}
      />

      {/* Download Button */}
      <div className="flex justify-end">
        <a
          href={`${apiUrl}/api/v1/visualize/${activeTab}?address=${encodeURIComponent(address)}&width=1000&height=700${professional ? '&professional=true' : ''}${(activeTab === 'cross-section' || activeTab === 'elevation') ? '&use_claude=true' : ''}`}
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
