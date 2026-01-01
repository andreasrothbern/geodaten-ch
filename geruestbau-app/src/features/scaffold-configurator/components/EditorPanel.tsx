/**
 * Editor Panel - Tab 2
 * Carousel navigation and interactive scaffold grid
 */

import { ChevronLeft, ChevronRight, MousePointer, Eraser, ArrowLeftRight, ArrowUpDown, ArrowUpFromLine, Footprints } from 'lucide-react';
import { useScaffoldConfig, useVisibleElements, useSettings } from '../hooks/useScaffoldConfig';
import type { EditorTool, ScaffoldFacade } from '../types/scaffold.types';
import { ScaffoldGrid } from './editor';

export default function EditorPanel() {
  const {
    currentElementIndex,
    currentTool,
    navigateCarousel,
    jumpToElement,
    setTool,
    setCurrentTab,
    configuration,
    toggleCell,
    toggleRow,
    toggleLevel,
    setLift,
    setStairs,
    toggleCornerEnabled,
  } = useScaffoldConfig();

  const visibleElements = useVisibleElements();
  const settings = useSettings();
  const currentElement = visibleElements?.current;
  const elements = configuration?.elements ?? [];

  const tools: { id: EditorTool; label: string; icon: React.ReactNode }[] = [
    { id: 'select', label: 'Auswählen', icon: <MousePointer className="w-4 h-4" /> },
    { id: 'remove', label: 'Feld ±', icon: <Eraser className="w-4 h-4" /> },
    { id: 'removeRow', label: 'Reihe ±', icon: <ArrowLeftRight className="w-4 h-4" /> },
    { id: 'removeLevel', label: 'Schicht ±', icon: <ArrowUpDown className="w-4 h-4" /> },
    { id: 'lift', label: 'Lift', icon: <ArrowUpFromLine className="w-4 h-4" /> },
    { id: 'stairs', label: 'Treppe', icon: <Footprints className="w-4 h-4" /> },
  ];

  const toolHints: Record<EditorTool, string> = {
    select: 'Klicke auf ein Feld für Details',
    remove: 'Klicke auf Felder zum Entfernen/Wiederherstellen',
    removeRow: 'Klicke um ganze Reihe (vertikal) zu toggeln',
    removeLevel: 'Klicke um ganze Schicht (horizontal) zu toggeln',
    lift: 'Klicke wo der Lift platziert werden soll',
    stairs: 'Klicke wo die Treppe platziert werden soll',
  };

  // Grid click handlers
  const handleCellClick = (field: number, level: number) => {
    if (currentElement?.type === 'facade') {
      toggleCell(currentElement.id, field, level);
    }
  };

  const handleRowClick = (field: number) => {
    if (currentElement?.type === 'facade') {
      toggleRow(currentElement.id, field);
    }
  };

  const handleLevelClick = (level: number) => {
    if (currentElement?.type === 'facade') {
      toggleLevel(currentElement.id, level);
    }
  };

  const handleLiftClick = (field: number) => {
    if (currentElement?.type === 'facade') {
      const currentLift = currentElement.modifications.lift_position;
      setLift(currentElement.id, currentLift === field ? null : field);
    }
  };

  const handleStairsClick = (field: number) => {
    if (currentElement?.type === 'facade') {
      const currentStairs = currentElement.modifications.stairs_position;
      setStairs(currentElement.id, currentStairs === field ? null : field);
    }
  };

  if (!visibleElements || !settings) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Keine Elemente verfügbar</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Carousel Navigation */}
      <div className="bg-white rounded-xl shadow-sm">
        <div className="flex items-center justify-center gap-2 py-3 px-4">
          <button
            onClick={() => navigateCarousel(-1)}
            className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-gray-500" />
          </button>

          {/* Previous */}
          <button
            onClick={() => navigateCarousel(-1)}
            className="px-3 py-1.5 rounded-xl text-xs opacity-50 hover:opacity-75 transition-opacity"
            style={{
              backgroundColor: visibleElements.prev.type === 'corner' ? '#fef3c7' : '#f3f4f6',
              color: visibleElements.prev.type === 'corner' ? '#92400e' : '#374151',
            }}
          >
            {visibleElements.prev.name}
          </button>

          {/* Current */}
          <div
            className="px-4 py-2.5 rounded-xl text-sm font-semibold transform scale-110 shadow-sm"
            style={{
              backgroundColor: currentElement?.type === 'corner' ? '#f59e0b' : currentElement?.type === 'facade' ? currentElement.color : '#ef4444',
              color: 'white',
            }}
          >
            {currentElement?.name}
            {currentElement?.type === 'facade' && (
              <span className="opacity-70 ml-1">({currentElement.length_m}m)</span>
            )}
          </div>

          {/* Next */}
          <button
            onClick={() => navigateCarousel(1)}
            className="px-3 py-1.5 rounded-xl text-xs opacity-50 hover:opacity-75 transition-opacity"
            style={{
              backgroundColor: visibleElements.next.type === 'corner' ? '#fef3c7' : '#f3f4f6',
              color: visibleElements.next.type === 'corner' ? '#92400e' : '#374151',
            }}
          >
            {visibleElements.next.name}
          </button>

          <button
            onClick={() => navigateCarousel(1)}
            className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors"
          >
            <ChevronRight className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Dots - only enabled elements */}
        <div className="flex justify-center gap-1.5 pb-3">
          {elements
            .filter(el => el.enabled)
            .map((el) => {
              const actualIdx = elements.findIndex(e => e.id === el.id);
              return (
                <button
                  key={el.id}
                  onClick={() => {
                    jumpToElement(actualIdx);
                    setCurrentTab('editor'); // Stay on editor
                  }}
                  className={`w-2 h-2 rounded-full transition-all hover:scale-125 ${
                    actualIdx === currentElementIndex
                      ? el.type === 'corner' ? 'bg-amber-500 w-4' : 'bg-red-500 w-4'
                      : el.type === 'corner' ? 'bg-amber-200' : 'bg-gray-300'
                  }`}
                  title={el.name}
                />
              );
            })}
        </div>
      </div>

      {/* Toolbar */}
      <div className="bg-white rounded-xl p-3 shadow-sm">
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
          {tools.map((tool) => (
            <button
              key={tool.id}
              onClick={() => setTool(tool.id)}
              disabled={currentElement?.type === 'corner'}
              className={`flex items-center gap-1.5 px-3 py-2 border-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                currentTool === tool.id
                  ? 'bg-red-50 border-red-500 text-red-600'
                  : 'border-gray-200 text-gray-600 hover:border-gray-300'
              } ${currentElement?.type === 'corner' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {tool.icon}
              {tool.label}
            </button>
          ))}
        </div>
        <div className="mt-2 text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
          ℹ️ {currentElement?.type === 'corner' ? 'Ecken werden automatisch berechnet' : toolHints[currentTool]}
        </div>
      </div>

      {/* Editor Area */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-semibold text-gray-700">
              {currentElement?.type === 'corner' ? currentElement.name : `${currentElement?.name}-Fassade`}
            </h3>
            <p className="text-xs text-gray-400">
              {currentElement?.type === 'facade'
                ? `${currentElement.fields} Felder × ${currentElement.levels} Lagen`
                : 'Automatisch berechnet'}
            </p>
          </div>
          {currentElement?.type === 'facade' && (
            <div className="text-right">
              <span className="text-sm font-medium text-gray-700">
                {currentElement.length_m}m × {currentElement.target_height_m.toFixed(1)}m
              </span>
              <p className="text-xs text-gray-400">Gefälle: {currentElement.slope_percent}%</p>
            </div>
          )}
        </div>

        {/* Grid or Corner Info */}
        {currentElement?.type === 'corner' ? (
          <div className={`text-center py-8 rounded-xl border-2 border-dashed transition-all ${
            currentElement.enabled
              ? 'bg-amber-50 border-amber-200'
              : 'bg-gray-100 border-gray-300 opacity-60'
          }`}>
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 ${
              currentElement.enabled ? 'bg-amber-100' : 'bg-gray-200'
            }`}>
              <span className={`text-2xl ${currentElement.enabled ? 'text-amber-500' : 'text-gray-400'}`}>⌐</span>
            </div>
            <h4 className={`font-semibold ${currentElement.enabled ? 'text-amber-800' : 'text-gray-500'}`}>
              {currentElement.name}
            </h4>
            <p className={`text-sm mt-1 ${currentElement.enabled ? 'text-amber-600' : 'text-gray-400'}`}>
              {currentElement.enabled ? 'Wird automatisch berechnet' : 'Ecke entfernt'}
            </p>
            {currentElement.enabled && (
              <div className="flex justify-center gap-3 mt-4">
                <span className="bg-amber-100 text-amber-700 text-sm px-3 py-1.5 rounded-full">
                  {currentElement.corner_posts} Eckpfosten
                </span>
                <span className="bg-amber-100 text-amber-700 text-sm px-3 py-1.5 rounded-full">
                  {currentElement.diagonals} Diagonalen
                </span>
              </div>
            )}
            <button
              onClick={() => toggleCornerEnabled(currentElement.id)}
              className={`mt-4 px-4 py-2 rounded-lg font-medium transition-colors ${
                currentElement.enabled
                  ? 'bg-red-100 text-red-700 hover:bg-red-200'
                  : 'bg-green-100 text-green-700 hover:bg-green-200'
              }`}
            >
              {currentElement.enabled ? 'Ecke entfernen' : 'Ecke wiederherstellen'}
            </button>
          </div>
        ) : currentElement?.type === 'facade' ? (
          <div className="overflow-hidden border rounded-xl bg-gradient-to-b from-sky-50 to-gray-50">
            <ScaffoldGrid
              facade={currentElement as ScaffoldFacade}
              settings={settings}
              currentTool={currentTool}
              onCellClick={handleCellClick}
              onRowClick={handleRowClick}
              onLevelClick={handleLevelClick}
              onLiftClick={handleLiftClick}
              onStairsClick={handleStairsClick}
            />
          </div>
        ) : null}

        {/* Legend */}
        <div className="flex flex-wrap gap-3 mt-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="inline-block w-4 h-3 bg-red-500 rounded"></span>
            Gerüstfeld
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-4 h-3 bg-red-200 rounded opacity-50"></span>
            Entfernt
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-4 h-3 bg-amber-500 rounded"></span>
            Lift
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-4 h-3 bg-green-500 rounded"></span>
            Treppe
          </span>
        </div>
      </div>

      {/* Stats */}
      {currentElement?.type === 'facade' && (
        <div className="grid grid-cols-4 gap-2">
          <div className="bg-white rounded-xl p-3 text-center shadow-sm">
            <p className="text-xl font-bold text-gray-800">
              {currentElement.fields * currentElement.levels - currentElement.modifications.removed_cells.size}
            </p>
            <p className="text-xs text-gray-500">Felder</p>
          </div>
          <div className="bg-white rounded-xl p-3 text-center shadow-sm">
            <p className="text-xl font-bold text-orange-500">
              {currentElement.modifications.removed_cells.size}
            </p>
            <p className="text-xs text-gray-500">Entfernt</p>
          </div>
          <div className="bg-white rounded-xl p-3 text-center shadow-sm">
            <p className="text-xl font-bold text-red-600">
              {Math.round(
                (currentElement.fields * currentElement.levels - currentElement.modifications.removed_cells.size) *
                settings.field_width_m *
                settings.level_height_m
              )}
            </p>
            <p className="text-xs text-gray-500">m²</p>
          </div>
          <div className="bg-white rounded-xl p-3 text-center shadow-sm">
            <p className="text-xl font-bold text-blue-600">
              {(currentElement.modifications.lift_position !== null ? 1 : 0) +
                (currentElement.modifications.stairs_position !== null ? 1 : 0)}
            </p>
            <p className="text-xs text-gray-500">Extras</p>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex gap-3">
        <button
          onClick={() => setCurrentTab('overview')}
          className="flex-1 py-3 border border-gray-300 bg-white rounded-xl font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          ← Übersicht
        </button>
        <button
          onClick={() => setCurrentTab('3d')}
          className="flex-1 py-3 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-colors"
        >
          3D-Vorschau →
        </button>
      </div>
    </div>
  );
}
