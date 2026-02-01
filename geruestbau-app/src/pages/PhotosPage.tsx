import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Camera, MapPin, Building2, Compass, Info, X } from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import type { OcrExtractionResult } from '../types/project'

interface ProjectUpload {
  id: string
  project_id: string
  filename: string
  file_type: string
  direction?: string
  created_at: string
  extraction_result?: OcrExtractionResult
}

export default function PhotosPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [uploads, setUploads] = useState<ProjectUpload[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedUpload, setSelectedUpload] = useState<ProjectUpload | null>(null)

  useEffect(() => {
    if (id) {
      loadUploads(id)
    }
  }, [id])

  const loadUploads = async (projectId: string) => {
    try {
      setLoading(true)
      setError(null)
      const data = await geruestbauApi.getProjectUploads(projectId)
      setUploads(data)
    } catch (err) {
      console.error('Fehler beim Laden:', err)
      setError('Fotos konnten nicht geladen werden')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('de-CH', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <button
          type="button"
          onClick={() => navigate(`/projects/${id}`)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-lg font-semibold">Projekt-Fotos</h1>
          <p className="text-sm text-gray-500">{uploads.length} Fotos</p>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card bg-red-50 text-red-700 text-center">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && uploads.length === 0 && (
        <div className="card text-center py-12">
          <Camera className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">Noch keine Fotos vorhanden</p>
          <p className="text-sm text-gray-400 mt-1">
            Fotos werden beim Projekt-Import automatisch gespeichert
          </p>
        </div>
      )}

      {/* Photo Grid */}
      {!loading && uploads.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {uploads.map((upload) => (
            <button
              key={upload.id}
              type="button"
              onClick={() => setSelectedUpload(upload)}
              className="relative aspect-square bg-gray-100 rounded-lg overflow-hidden hover:opacity-90 transition-opacity"
            >
              <img
                src={geruestbauApi.getUploadFile(upload.id)}
                alt={upload.filename}
                className="w-full h-full object-cover"
              />
              {/* Direction Badge */}
              {upload.direction && (
                <div className="absolute top-2 left-2 bg-black/60 text-white text-xs px-2 py-0.5 rounded">
                  {upload.direction}
                </div>
              )}
              {/* Analysis Badge */}
              {upload.extraction_result?.building_analysis && (
                <div className="absolute top-2 right-2 bg-blue-600 text-white p-1 rounded">
                  <Info className="w-3 h-3" />
                </div>
              )}
              {/* Date */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
                <p className="text-white text-xs">
                  {formatDate(upload.created_at)}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {selectedUpload && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedUpload(null)}
        >
          <div
            className="bg-white rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Image */}
            <div className="relative">
              <img
                src={geruestbauApi.getUploadFile(selectedUpload.id)}
                alt={selectedUpload.filename}
                className="w-full"
              />
              <button
                type="button"
                onClick={() => setSelectedUpload(null)}
                className="absolute top-2 right-2 bg-black/60 text-white p-2 rounded-full"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Details */}
            <div className="p-4 space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-medium">{selectedUpload.filename}</p>
                  <p className="text-sm text-gray-500">
                    {formatDate(selectedUpload.created_at)}
                  </p>
                </div>
                {selectedUpload.direction && (
                  <span className="bg-gray-100 text-gray-700 text-sm px-2 py-1 rounded">
                    {selectedUpload.direction}
                  </span>
                )}
              </div>

              {/* Extraction Result Details */}
              {selectedUpload.extraction_result && (
                <div className="space-y-3 pt-3 border-t">
                  {/* GPS Data */}
                  {selectedUpload.extraction_result.gps_data && (
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                      <div className="text-sm">
                        <p className="font-medium">GPS-Position</p>
                        <p className="text-gray-500">
                          {selectedUpload.extraction_result.gps_data.lat?.toFixed(5)},{' '}
                          {selectedUpload.extraction_result.gps_data.lon?.toFixed(5)}
                        </p>
                        {selectedUpload.extraction_result.gps_data.compass_direction_text && (
                          <p className="text-gray-400 text-xs flex items-center gap-1">
                            <Compass className="w-3 h-3" />
                            Blick: {selectedUpload.extraction_result.gps_data.compass_direction_text}
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Suggested Address */}
                  {selectedUpload.extraction_result.suggested_address && (
                    <div className="flex items-start gap-2">
                      <Building2 className="w-4 h-4 text-gray-400 mt-0.5" />
                      <div className="text-sm">
                        <p className="font-medium">Erkannte Adresse</p>
                        <p className="text-gray-500">
                          {selectedUpload.extraction_result.suggested_address}
                        </p>
                        {selectedUpload.extraction_result.suggested_egid && (
                          <p className="text-gray-400 text-xs">
                            EGID: {selectedUpload.extraction_result.suggested_egid}
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Building Analysis */}
                  {selectedUpload.extraction_result.building_analysis && (
                    <div className="bg-blue-50 rounded-lg p-3">
                      <p className="font-medium text-blue-900 text-sm mb-2">Gebäude-Analyse</p>
                      <ul className="text-sm text-blue-800 space-y-1">
                        {selectedUpload.extraction_result.building_analysis.floors_count && (
                          <li>Geschosse: {selectedUpload.extraction_result.building_analysis.floors_count}</li>
                        )}
                        {selectedUpload.extraction_result.building_analysis.roof_type && (
                          <li>Dachform: {selectedUpload.extraction_result.building_analysis.roof_type}</li>
                        )}
                        {selectedUpload.extraction_result.building_analysis.facade_material && (
                          <li>Fassade: {selectedUpload.extraction_result.building_analysis.facade_material}</li>
                        )}
                        {selectedUpload.extraction_result.building_analysis.obstacles &&
                          selectedUpload.extraction_result.building_analysis.obstacles.length > 0 && (
                          <li className="text-orange-700">
                            Hindernisse: {selectedUpload.extraction_result.building_analysis.obstacles.join(', ')}
                          </li>
                        )}
                      </ul>
                    </div>
                  )}

                  {/* Terrain Analysis */}
                  {selectedUpload.extraction_result.terrain_analysis && (
                    <div className="bg-green-50 rounded-lg p-3">
                      <p className="font-medium text-green-900 text-sm mb-2">Terrain & Umgebung</p>
                      <ul className="text-sm text-green-800 space-y-1">
                        {selectedUpload.extraction_result.terrain_analysis.slope_estimate && (
                          <li>Hanglage: {selectedUpload.extraction_result.terrain_analysis.slope_estimate}</li>
                        )}
                        {selectedUpload.extraction_result.terrain_analysis.ground_type && (
                          <li>Untergrund: {selectedUpload.extraction_result.terrain_analysis.ground_type}</li>
                        )}
                        {selectedUpload.extraction_result.terrain_analysis.access_type && (
                          <li>Zufahrt: {selectedUpload.extraction_result.terrain_analysis.access_type}</li>
                        )}
                        {selectedUpload.extraction_result.terrain_analysis.trees_nearby && (
                          <li className="text-orange-700">Bäume in der Nähe</li>
                        )}
                        {selectedUpload.extraction_result.terrain_analysis.power_lines && (
                          <li className="text-red-700">Stromleitungen!</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
