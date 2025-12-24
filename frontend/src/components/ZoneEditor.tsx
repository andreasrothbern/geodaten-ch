import { useState, useEffect } from 'react'
import type { BuildingContext, BuildingZone, ZoneType } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface ZoneEditorProps {
  egid: number | string
  onContextChange?: (context: BuildingContext | null) => void
}

const ZONE_TYPE_LABELS: Record<ZoneType, string> = {
  hauptgebaeude: 'Hauptgebäude',
  anbau: 'Anbau',
  turm: 'Turm',
  kuppel: 'Kuppel',
  arkade: 'Arkade',
  vordach: 'Vordach',
  treppenhaus: 'Treppenhaus',
  garage: 'Garage',
  unknown: 'Unbekannt',
}

const ZONE_TYPE_COLORS: Record<ZoneType, string> = {
  hauptgebaeude: 'bg-blue-100 border-blue-300',
  anbau: 'bg-green-100 border-green-300',
  turm: 'bg-purple-100 border-purple-300',
  kuppel: 'bg-yellow-100 border-yellow-300',
  arkade: 'bg-orange-100 border-orange-300',
  vordach: 'bg-gray-100 border-gray-300',
  treppenhaus: 'bg-pink-100 border-pink-300',
  garage: 'bg-slate-100 border-slate-300',
  unknown: 'bg-gray-100 border-gray-300',
}

export function ZoneEditor({ egid, onContextChange }: ZoneEditorProps) {
  const [context, setContext] = useState<BuildingContext | null>(null)
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  // Kontext laden
  useEffect(() => {
    if (egid) {
      loadContext()
    }
  }, [egid])

  const loadContext = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/building/context/${egid}?create_if_missing=true`
      )
      const data = await response.json()
      if (data.status === 'found' || data.status === 'created') {
        setContext(data.context)
        onContextChange?.(data.context)
      } else {
        setContext(null)
        onContextChange?.(null)
      }
    } catch (err) {
      setError('Fehler beim Laden des Kontexts')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const analyzeWithClaude = async () => {
    setAnalyzing(true)
    setError(null)
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/building/context/${egid}/analyze`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ include_orthofoto: false, force_reanalyze: true }),
        }
      )
      const data = await response.json()
      if (data.status === 'success' || data.status === 'already_exists') {
        setContext(data.context)
        onContextChange?.(data.context)
        setHasChanges(false)
      } else {
        setError(data.message || 'Analyse fehlgeschlagen')
      }
    } catch (err) {
      setError('Fehler bei der Claude-Analyse')
      console.error(err)
    } finally {
      setAnalyzing(false)
    }
  }

  const saveContext = async () => {
    if (!context) return
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/building/context/${egid}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            zones: context.zones,
            validated: true,
          }),
        }
      )
      const data = await response.json()
      if (data.status === 'updated') {
        setContext(data.context)
        onContextChange?.(data.context)
        setHasChanges(false)
      } else {
        setError(data.message || 'Speichern fehlgeschlagen')
      }
    } catch (err) {
      setError('Fehler beim Speichern')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const updateZone = (zoneId: string, updates: Partial<BuildingZone>) => {
    if (!context) return
    setContext({
      ...context,
      zones: context.zones.map((z) =>
        z.id === zoneId ? { ...z, ...updates } : z
      ),
    })
    setHasChanges(true)
  }

  const toggleZoneScaffolding = (zoneId: string) => {
    const zone = context?.zones.find((z) => z.id === zoneId)
    if (zone) {
      updateZone(zoneId, { beruesten: !zone.beruesten })
    }
  }

  if (loading && !context) {
    return (
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center gap-2 text-gray-500">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Lade Gebäude-Kontext...
        </div>
      </div>
    )
  }

  return (
    <div className="bg-amber-50 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-amber-900 flex items-center gap-2">
          <span>🏗️</span>
          Gebäude-Zonen
          {context && (
            <span className="text-xs bg-amber-200 px-2 py-0.5 rounded">
              {context.complexity}
            </span>
          )}
        </h4>
        <div className="flex items-center gap-2">
          {context?.source === 'claude' && (
            <span className="text-xs text-amber-600">
              ✨ Claude analysiert
            </span>
          )}
          {context?.source === 'auto' && (
            <span className="text-xs text-gray-500">
              Auto-Context
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-300 rounded p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Zonen-Liste */}
      {context && context.zones.length > 0 ? (
        <div className="space-y-3">
          {context.zones.map((zone) => (
            <div
              key={zone.id}
              className={`border rounded-lg p-3 ${ZONE_TYPE_COLORS[zone.type]} ${
                !zone.beruesten ? 'opacity-50' : ''
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={zone.beruesten}
                    onChange={() => toggleZoneScaffolding(zone.id)}
                    className="w-4 h-4 text-amber-600 rounded"
                  />
                  <span className="font-medium">{zone.name}</span>
                </div>
                <span className="text-xs px-2 py-0.5 bg-white/50 rounded">
                  {ZONE_TYPE_LABELS[zone.type]}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-sm">
                <div>
                  <label className="text-xs text-gray-600">Höhe (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={zone.gebaeudehoehe_m || ''}
                    onChange={(e) =>
                      updateZone(zone.id, {
                        gebaeudehoehe_m: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full px-2 py-1 text-sm border rounded bg-white"
                    disabled={!zone.beruesten}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600">Traufe (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={zone.traufhoehe_m || ''}
                    onChange={(e) =>
                      updateZone(zone.id, {
                        traufhoehe_m: parseFloat(e.target.value) || undefined,
                      })
                    }
                    className="w-full px-2 py-1 text-sm border rounded bg-white"
                    disabled={!zone.beruesten}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600">First (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={zone.firsthoehe_m || ''}
                    onChange={(e) =>
                      updateZone(zone.id, {
                        firsthoehe_m: parseFloat(e.target.value) || undefined,
                      })
                    }
                    className="w-full px-2 py-1 text-sm border rounded bg-white"
                    disabled={!zone.beruesten}
                  />
                </div>
              </div>

              {zone.notes && (
                <p className="text-xs text-gray-500 mt-2 italic">{zone.notes}</p>
              )}

              {zone.sonderkonstruktion && (
                <div className="mt-2 text-xs text-orange-700 bg-orange-100 px-2 py-1 rounded inline-block">
                  ⚠️ Sonderkonstruktion erforderlich
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm text-gray-500 text-center py-4">
          Keine Zonen definiert
        </div>
      )}

      {/* Claude Reasoning */}
      {context?.reasoning && (
        <div className="bg-white/50 rounded p-3 text-xs text-gray-600">
          <span className="font-medium">Claude:</span> {context.reasoning}
        </div>
      )}

      {/* Aktionen */}
      <div className="flex flex-wrap gap-2 pt-2 border-t border-amber-200">
        <button
          onClick={analyzeWithClaude}
          disabled={analyzing}
          className="px-3 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50 flex items-center gap-1"
        >
          {analyzing ? (
            <>
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analysiere...
            </>
          ) : (
            <>✨ Mit Claude analysieren</>
          )}
        </button>

        {hasChanges && (
          <button
            onClick={saveContext}
            disabled={loading}
            className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
          >
            💾 Speichern
          </button>
        )}

        <button
          onClick={loadContext}
          disabled={loading}
          className="px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300 disabled:opacity-50"
        >
          🔄 Neu laden
        </button>
      </div>

      {/* Zusammenfassung */}
      {context && context.zones.length > 0 && (
        <div className="text-xs text-amber-700 pt-2">
          {context.zones.filter((z) => z.beruesten).length} von {context.zones.length} Zonen zum Einrüsten ausgewählt
          {context.validated_by_user && ' • ✓ Validiert'}
        </div>
      )}
    </div>
  )
}
