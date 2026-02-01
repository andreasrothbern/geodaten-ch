/**
 * 3D Panel - Tab 3
 * 3D visualization using IFC.js (@thatopen/components)
 */

import { useState, Suspense } from 'react';
import { RotateCw, ZoomIn, Home, X, Package, AlertTriangle, Eye, ChevronDown } from 'lucide-react';
import { useScaffoldConfig, useTotals, useSettings } from '../hooks/useScaffoldConfig';
import { formatNumber } from '../utils/calculations';
import type { View3D, BuildingZone, ScaffoldFacade } from '../types/scaffold.types';
import type { NeighborBuilding, ObjectData } from '../../../api/geruestbau';
import type { BuildingWall } from '../../../types/project';
import { ScaffoldScene } from './threeDView';

// NEU 15.01.2026: Types für Materialliste
interface MaterialEstimate {
  article_number: string;
  name: string;
  category: string;
  quantity_min: number;
  quantity_max: number;
  quantity_typical: number;
  weight_per_piece_kg: number | null;
  total_weight_kg: number | null;
  notes: string | null;
}

interface MaterialListResponse {
  system_id: string;
  scaffold_area_m2: number;
  terrain_diff_m: number;
  field_count: number;
  materials: MaterialEstimate[];
  summary: {
    total_pieces: number;
    total_weight_kg: number;
    total_weight_tons: number;
    weight_per_m2_kg: number;
    has_leveling: boolean;
    leveling_pieces: number;
    leveling_weight_kg: number;
  };
}

interface ThreeDPanelProps {
  neighbors?: NeighborBuilding[];
  blockedSides?: string[];
  // NEU 19.01.2026: Objekt-Architektur - Ein Projekt = Ein Objekt
  objectData?: ObjectData;
  zones?: BuildingZone[];
  complexity?: 'simple' | 'moderate' | 'complex';
  // NEU 18.01.2026: Echte 3D-Wandgeometrie aus swissBUILDINGS3D
  buildingWalls?: BuildingWall[];
}

export default function ThreeDPanel({ neighbors = [], blockedSides = [], objectData, zones = [], complexity = 'simple', buildingWalls = [] }: ThreeDPanelProps) {
  const { setCurrentTab, configuration } = useScaffoldConfig();
  const totals = useTotals();
  const settings = useSettings();
  const [activeView, setActiveView] = useState<View3D>('isometric');
  const [showViewSelector, setShowViewSelector] = useState(false);

  // NEU 15.01.2026: State für Materialliste
  const [materialList, setMaterialList] = useState<MaterialListResponse | null>(null);
  const [isLoadingMaterials, setIsLoadingMaterials] = useState(false);
  const [showMaterialModal, setShowMaterialModal] = useState(false);
  const [materialError, setMaterialError] = useState<string | null>(null);

  // Building polygon is now always the ORIGINAL from swissBUILDINGS3D
  const polygonPointCount = configuration?.buildingPolygon?.length || 0;

  // NEU 15.01.2026: Materialliste vom Backend laden
  const fetchMaterialList = async () => {
    if (!configuration || !totals) return;

    setIsLoadingMaterials(true);
    setMaterialError(null);

    try {
      // Terrain-Differenz und Feldanzahl aus Konfiguration extrahieren
      const facadeElements = configuration.elements.filter(
        (el): el is ScaffoldFacade => el.type === 'facade' && el.enabled
      );
      const terrainDiff = facadeElements.length > 0
        ? facadeElements[0].terrain_diff_m || 0
        : 0;
      const totalFields = facadeElements.reduce((sum, el) => sum + el.fields, 0);

      // System-ID mapping
      const systemId = settings?.system === 'layher_blitz' ? 'blitz70' : 'allround';

      // API-Aufruf mit Hanglage-Parametern
      const params = new URLSearchParams({
        system_id: systemId,
        area_m2: totals.scaffold_area_m2.toString(),
        short_field_ratio: '0.33',
        terrain_diff_m: terrainDiff.toString(),
        field_count: totalFields.toString(),
      });

      const response = await fetch(`/api/v1/catalog/estimate?${params}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: MaterialListResponse = await response.json();
      setMaterialList(data);
      setShowMaterialModal(true);
    } catch (error) {
      console.error('Fehler beim Laden der Materialliste:', error);
      setMaterialError(error instanceof Error ? error.message : 'Unbekannter Fehler');
    } finally {
      setIsLoadingMaterials(false);
    }
  };

  const views: { id: View3D; label: string }[] = [
    { id: 'isometric', label: 'Isometrisch' },
    { id: 'north', label: 'Nord' },
    { id: 'east', label: 'Ost' },
    { id: 'south', label: 'Süd' },
    { id: 'west', label: 'West' },
    { id: 'top', label: 'Draufsicht' },
  ];

  const handleResetView = () => {
    setActiveView('isometric');
  };

  if (!configuration) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Keine Konfiguration geladen</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 3D Viewer */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="relative" style={{ minHeight: '400px' }}>
          {/* 3D Scene */}
          <Suspense
            fallback={
              <div className="absolute inset-0 flex items-center justify-center bg-sky-50">
                <div className="text-center">
                  <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <p className="text-gray-600">3D-Szene wird geladen...</p>
                </div>
              </div>
            }
          >
            <ScaffoldScene
              configuration={configuration}
              activeView={activeView}
              onViewChange={setActiveView}
              neighbors={neighbors}
              blockedSides={blockedSides}
              objectData={objectData}
              zones={zones}
              complexity={complexity}
              buildingWalls={buildingWalls}
            />
          </Suspense>

          {/* 3D Controls */}
          <div className="absolute bottom-4 left-4 flex gap-2">
            <button
              className="p-2.5 bg-white rounded-lg shadow hover:bg-gray-50 transition-colors"
              title="Drehen (Maus ziehen)"
            >
              <RotateCw className="w-5 h-5 text-gray-600" />
            </button>
            <button
              className="p-2.5 bg-white rounded-lg shadow hover:bg-gray-50 transition-colors"
              title="Zoom (Mausrad)"
            >
              <ZoomIn className="w-5 h-5 text-gray-600" />
            </button>
            <button
              onClick={handleResetView}
              className="p-2.5 bg-white rounded-lg shadow hover:bg-gray-50 transition-colors"
              title="Ansicht zurücksetzen"
            >
              <Home className="w-5 h-5 text-gray-600" />
            </button>

            {/* Polygon info badge */}
            {polygonPointCount > 0 && (
              <span className="px-3 py-2 bg-white rounded-lg shadow text-sm text-gray-500">
                {polygonPointCount} Punkte
              </span>
            )}
          </div>

          {/* View Selector - Collapsible */}
          <div className="absolute top-4 right-4">
            {showViewSelector ? (
              <div className="bg-white rounded-lg shadow-lg overflow-hidden">
                {views.map((view) => (
                  <button
                    key={view.id}
                    onClick={() => {
                      setActiveView(view.id);
                      setShowViewSelector(false);
                    }}
                    className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors ${
                      activeView === view.id ? 'font-medium bg-gray-50' : 'text-gray-600'
                    }`}
                  >
                    {activeView === view.id && <span className="text-red-500 mr-2">●</span>}
                    {view.label}
                  </button>
                ))}
              </div>
            ) : (
              <button
                onClick={() => setShowViewSelector(true)}
                className="bg-white rounded-lg shadow-lg px-3 py-2 flex items-center gap-2 hover:bg-gray-50 transition-colors"
                title="Ansicht wechseln"
              >
                <Eye className="w-4 h-4 text-gray-600" />
                <span className="text-sm font-medium text-gray-700">
                  {views.find(v => v.id === activeView)?.label || 'Ansicht'}
                </span>
                <ChevronDown className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>

          {/* Compass */}
          <div className="absolute top-4 left-4 w-14 h-14 bg-white rounded-full shadow-lg flex items-center justify-center">
            <div className="relative w-10 h-10">
              <span className="absolute top-0 left-1/2 -translate-x-1/2 text-xs text-red-600 font-bold">N</span>
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 text-xs text-gray-400">S</span>
              <span className="absolute left-0 top-1/2 -translate-y-1/2 text-xs text-gray-400">W</span>
              <span className="absolute right-0 top-1/2 -translate-y-1/2 text-xs text-gray-400">O</span>
            </div>
          </div>

          {/* Info Badge */}
          <div className="absolute bottom-4 right-4 bg-white/95 rounded-lg shadow-lg px-3 py-2 text-sm">
            <p className="font-medium text-gray-800">
              {settings?.work_type === 'facade' ? 'Fassadengerüst' : settings?.work_type === 'roof' ? 'Dachschutz' : 'Volleinrüstung'}
            </p>
            <p className="text-gray-500 text-xs">{formatNumber(totals.scaffold_area_m2)} m² • {totals.facade_count} Fassaden</p>
          </div>
        </div>

        {/* Legend */}
        <div className="p-4 border-t bg-white">
          <div className="flex flex-wrap gap-4 text-sm">
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-red-500 rounded"></span>Nord
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-rose-500 rounded"></span>Ost
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-pink-500 rounded"></span>Süd
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-orange-500 rounded"></span>West
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-amber-500 rounded"></span>Lift
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-green-500 rounded"></span>Treppe
            </span>
          </div>
        </div>
      </div>

      {/* Summary Card */}
      <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-4 text-white shadow-lg">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          📋 Zusammenfassung
        </h3>
        <div className="grid grid-cols-2 gap-3 text-sm mb-4">
          <div>
            <p className="text-green-100">Gerüstfläche</p>
            <p className="text-xl font-bold">{formatNumber(totals.scaffold_area_m2)} m²</p>
          </div>
          <div>
            <p className="text-green-100">Elemente</p>
            <p className="text-xl font-bold">{totals.facade_count} + {totals.corner_count}</p>
          </div>
          <div>
            <p className="text-green-100">Max. Höhe</p>
            <p className="font-bold">
              {totals.max_height_m.toFixed(2)}m ({Math.ceil(totals.max_height_m / (settings?.level_height_m || 2))} Lagen)
            </p>
          </div>
          <div>
            <p className="text-green-100">System</p>
            <p className="font-bold">{settings?.system === 'layher_blitz' ? 'Layher Blitz' : 'Layher Allround'}</p>
          </div>
        </div>
        <div className="border-t border-white/20 pt-3 space-y-1 text-sm">
          <p className="flex items-center gap-2">✅ Alle Fassaden konfiguriert</p>
          <p className="flex items-center gap-2">✅ Höhenausgleich für Gefälle eingeplant</p>
          {totals.max_height_m > 15 && (
            <p className="flex items-center gap-2 text-yellow-200">⚠️ Statik-Prüfung empfohlen ({'>'}15m)</p>
          )}
        </div>
      </div>

      {/* IFC.js Info */}
      <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
        <div className="flex gap-3">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-blue-600 font-bold text-sm">IFC</span>
          </div>
          <div>
            <h4 className="font-semibold text-blue-800">IFC.js Integration</h4>
            <p className="text-sm text-blue-700 mt-1">
              3D-Ansicht basiert auf @thatopen/components (IFC.js).
              Export nach IFC/DXF für LayPLAN in Entwicklung.
            </p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => setCurrentTab('editor')}
          className="flex-1 py-3 border border-gray-300 bg-white rounded-xl font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          ← Bearbeiten
        </button>
        <button
          onClick={fetchMaterialList}
          disabled={isLoadingMaterials}
          className="flex-1 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 shadow-sm transition-colors disabled:opacity-50 disabled:cursor-wait flex items-center justify-center gap-2"
        >
          {isLoadingMaterials ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Lade...
            </>
          ) : (
            <>
              <Package className="w-4 h-4" />
              Materialliste
            </>
          )}
        </button>
      </div>

      {/* Materialliste Modal */}
      {showMaterialModal && materialList && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b bg-green-50">
              <div>
                <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                  <Package className="w-5 h-5 text-green-600" />
                  Materialliste (Schätzung)
                </h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  {formatNumber(materialList.scaffold_area_m2)} m² Gerüstfläche
                  {materialList.summary.has_leveling && (
                    <span className="ml-2 text-orange-600">
                      • Hanglage {materialList.terrain_diff_m.toFixed(1)}m
                    </span>
                  )}
                </p>
              </div>
              <button
                onClick={() => setShowMaterialModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
              {/* Zusammenfassung */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="bg-gray-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-800">{materialList.summary.total_pieces}</p>
                  <p className="text-xs text-gray-500">Teile</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-800">{formatNumber(materialList.summary.total_weight_kg)}</p>
                  <p className="text-xs text-gray-500">kg Gewicht</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-800">{materialList.summary.weight_per_m2_kg}</p>
                  <p className="text-xs text-gray-500">kg/m²</p>
                </div>
              </div>

              {/* Hanglage-Hinweis */}
              {materialList.summary.has_leveling && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-4 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-orange-800">Hanglage erkannt</p>
                    <p className="text-sm text-orange-700">
                      {materialList.summary.leveling_pieces} Ausnivellierungs-Teile
                      ({materialList.summary.leveling_weight_kg} kg) für {materialList.terrain_diff_m.toFixed(1)}m Terrain-Differenz
                    </p>
                  </div>
                </div>
              )}

              {/* Material-Tabelle nach Kategorie gruppiert */}
              {(() => {
                const byCategory = materialList.materials.reduce((acc, mat) => {
                  const cat = mat.category || 'Sonstiges';
                  if (!acc[cat]) acc[cat] = [];
                  acc[cat].push(mat);
                  return acc;
                }, {} as Record<string, MaterialEstimate[]>);

                return Object.entries(byCategory).map(([category, materials]) => (
                  <div key={category} className="mb-4">
                    <h3 className={`text-sm font-semibold mb-2 ${
                      category === 'Ausnivellierung (Hanglage)' ? 'text-orange-700' : 'text-gray-700'
                    }`}>
                      {category}
                    </h3>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-500 border-b">
                          <th className="pb-1 font-normal">Material</th>
                          <th className="pb-1 font-normal text-right">Menge</th>
                          <th className="pb-1 font-normal text-right">Gewicht</th>
                        </tr>
                      </thead>
                      <tbody>
                        {materials.map((mat, idx) => (
                          <tr key={idx} className="border-b border-gray-100">
                            <td className="py-1.5">
                              <span className="font-medium">{mat.name}</span>
                              {mat.article_number && (
                                <span className="text-xs text-gray-400 ml-1">({mat.article_number})</span>
                              )}
                            </td>
                            <td className="py-1.5 text-right">{mat.quantity_typical}</td>
                            <td className="py-1.5 text-right text-gray-500">
                              {mat.total_weight_kg ? `${formatNumber(mat.total_weight_kg)} kg` : '–'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ));
              })()}
            </div>

            {/* Footer */}
            <div className="p-4 border-t bg-gray-50 flex justify-between items-center">
              <p className="text-xs text-gray-500">
                System: {materialList.system_id === 'blitz70' ? 'Layher Blitz 70' : 'Layher Allround'}
              </p>
              <button
                onClick={() => setShowMaterialModal(false)}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg text-sm font-medium transition-colors"
              >
                Schliessen
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fehler-Toast */}
      {materialError && (
        <div className="fixed bottom-4 right-4 bg-red-100 border border-red-300 text-red-800 px-4 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          <span>Fehler: {materialError}</span>
          <button
            onClick={() => setMaterialError(null)}
            className="ml-2 hover:bg-red-200 rounded p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
