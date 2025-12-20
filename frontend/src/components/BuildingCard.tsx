import type { BuildingInfo } from '../types'

interface BuildingCardProps {
  building: BuildingInfo
}

export function BuildingCard({ building }: BuildingCardProps) {
  return (
    <div className="card border border-gray-200">
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <h4 className="font-semibold text-lg">{building.address}</h4>
        <span className="text-xs bg-gray-100 px-2 py-1 rounded">
          EGID: {building.egid}
        </span>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        {building.construction_year && (
          <div>
            <span className="text-gray-500">Baujahr:</span>
            <span className="ml-2 font-medium">{building.construction_year}</span>
          </div>
        )}

        {building.building_category && (
          <div>
            <span className="text-gray-500">Kategorie:</span>
            <span className="ml-2 font-medium">{building.building_category}</span>
          </div>
        )}

        {building.floors && (
          <div>
            <span className="text-gray-500">Geschosse:</span>
            <span className="ml-2 font-medium">{building.floors}</span>
          </div>
        )}

        {building.apartments && (
          <div>
            <span className="text-gray-500">Wohnungen:</span>
            <span className="ml-2 font-medium">{building.apartments}</span>
          </div>
        )}

        {building.area_m2 && (
          <div>
            <span className="text-gray-500">Fläche:</span>
            <span className="ml-2 font-medium">{building.area_m2} m²</span>
          </div>
        )}

        {building.heating_type && (
          <div>
            <span className="text-gray-500">Heizung:</span>
            <span className="ml-2 font-medium">{building.heating_type}</span>
          </div>
        )}

        {building.heating_energy && (
          <div className="col-span-2">
            <span className="text-gray-500">Energieträger:</span>
            <span className="ml-2 font-medium">{building.heating_energy}</span>
          </div>
        )}
      </div>

      {/* Canton Badge */}
      {building.canton && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <span className="text-xs bg-red-50 text-red-700 px-2 py-1 rounded">
            Kanton {building.canton}
          </span>
          {building.city && (
            <span className="text-xs text-gray-500 ml-2">{building.city}</span>
          )}
        </div>
      )}
    </div>
  )
}
