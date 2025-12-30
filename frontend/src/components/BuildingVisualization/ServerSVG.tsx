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

// Preload all 4 visualization types for an address (parallel)
// WICHTIG: Parameter müssen mit ServerSVG Komponente übereinstimmen!
export async function preloadAllSvgs(
  address: string,
  apiUrl: string,
  width = 650,
  heights = { 'floor-plan': 450, 'elevation': 400, 'cross-section': 400, 'longitudinal-section': 400 },
  traufhoehe?: number,
  firsthoehe?: number
) {
  const types: Array<'floor-plan' | 'elevation' | 'cross-section' | 'longitudinal-section'> = [
    'floor-plan', 'elevation', 'cross-section', 'longitudinal-section'
  ]

  console.log(`[Preload] Starting preload for ${address} - 4 SVG types in parallel`)

  await Promise.all(types.map(async (type) => {
    const height = heights[type]
    // Cache key must match ServerSVG component's cache key format EXACTLY
    const useClaude = type !== 'floor-plan'
    const cacheKey = `${type}|${address}|${width}|${height}|${traufhoehe || ''}|${firsthoehe || ''}|${useClaude}`

    // Skip if already cached
    if (svgCache.has(cacheKey)) {
      console.log(`[Preload] ${type}: cache HIT`)
      return
    }

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
      // Claude API for elevation, cross-section, longitudinal-section
      if (useClaude) {
        params.set('use_claude', 'true')
      }

      console.log(`[Preload] ${type}: fetching...`)
      const response = await fetch(`${apiUrl}/api/v1/visualize/${type}?${params}`)
      if (response.ok) {
        const svgText = await response.text()
        svgCache.set(cacheKey, svgText)
        console.log(`[Preload] ${type}: cached (${svgText.length} chars)`)
      } else {
        console.error(`[Preload] ${type}: HTTP ${response.status}`)
      }
    } catch (err) {
      console.error(`[Preload] ${type}: failed`, err)
    }
  }))

  console.log(`[Preload] Completed for ${address}`)
}

interface ServerSVGProps {
  /** API endpoint type */
  type: 'cross-section' | 'longitudinal-section' | 'elevation' | 'floor-plan'
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
  firsthoehe
}: ServerSVGProps) {
  const [svg, setSvg] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const fetchedRef = useRef<string | null>(null)

  // Cache key includes manual heights
  // Claude API is always used for cross-section/longitudinal-section/elevation (unified prompt system)
  const useClaude = type === 'cross-section' || type === 'longitudinal-section' || type === 'elevation'
  const cacheKey = `${type}|${address}|${width}|${height}|${traufhoehe || ''}|${firsthoehe || ''}|${useClaude}`

  useEffect(() => {
    if (!address) {
      setLoading(false)
      return
    }

    // Debug: Log cache key and available keys
    console.log(`[ServerSVG] ${type}: Looking for cache key:`, cacheKey)
    console.log(`[ServerSVG] Available cache keys:`, Array.from(svgCache.keys()).filter(k => k.includes(type)))

    // Check cache first
    const cached = svgCache.get(cacheKey)
    if (cached) {
      console.log(`[ServerSVG] ${type}: CACHE HIT!`)
      setSvg(cached)
      setLoading(false)
      return
    }
    console.log(`[ServerSVG] ${type}: CACHE MISS - will fetch`)

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
        // Always use Claude API for cross-section/longitudinal-section/elevation (unified prompt system)
        if (type === 'cross-section' || type === 'longitudinal-section' || type === 'elevation') {
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
        console.log(`[SVG] Received ${svgText.length} chars, starts with: ${svgText.substring(0, 50)}`)

        // Validate SVG
        if (!svgText || !svgText.includes('<svg')) {
          console.error(`[SVG] Invalid SVG content received`)
          throw new Error('Ungültiger SVG-Inhalt')
        }

        // Store in cache
        svgCache.set(cacheKey, svgText)
        console.log(`[SVG] Setting SVG state...`)
        setSvg(svgText)
        console.log(`[SVG] SVG state set successfully`)
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

  // Debug render state
  console.log(`[SVG] Render: loading=${loading}, error=${error}, svg=${svg ? svg.length + ' chars' : 'null'}`)

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
  console.log(`[SVG] Rendering SVG with ${svg.length} chars`)
  return (
    <div
      className={`rounded-lg overflow-hidden border ${className}`}
      style={{ width, height, minHeight: height }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}

/**
 * Tabs für alle vier Visualisierungstypen
 * Claude API wird automatisch für Schnitte/Ansicht verwendet (unified prompt system)
 */
interface VisualizationTabsProps {
  address: string
  apiUrl: string
}

export function VisualizationTabs({ address, apiUrl }: VisualizationTabsProps) {
  const [activeTab, setActiveTab] = useState<'cross-section' | 'longitudinal-section' | 'elevation' | 'floor-plan'>('cross-section')

  const tabs = [
    { id: 'floor-plan' as const, label: 'Grundriss', icon: '📋' },
    { id: 'elevation' as const, label: 'Ansicht', icon: '🏛️' },
    { id: 'cross-section' as const, label: 'Querschnitt', icon: '📐' },
    { id: 'longitudinal-section' as const, label: 'Längsschnitt', icon: '↔️' },
  ]

  return (
    <div className="space-y-4">
      {/* Tab Navigation */}
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
          href={`${apiUrl}/api/v1/visualize/${activeTab}?address=${encodeURIComponent(address)}&width=1000&height=700${(activeTab === 'cross-section' || activeTab === 'longitudinal-section' || activeTab === 'elevation') ? '&use_claude=true' : ''}`}
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
