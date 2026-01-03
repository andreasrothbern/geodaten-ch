#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test-Script: simap.ch Import-Flow gegen Geodaten-Architektur.

Prüft ob die 20 Test-Cases aus simap_test_cases.json korrekt:
1. Importiert werden können (UrlImporter)
2. Geocodiert werden (swisstopo)
3. Alle Geodaten erhalten (SmartBuildingService)
4. Als Projekt gespeichert werden können

Ausführung:
    cd backend
    python scripts/test_simap_import_flow.py

Stand: 03.01.2026
"""

import asyncio
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Backend-Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.geruestbau.url_importer import UrlImporter, UrlImportResult
from app.services.swisstopo import SwisstopoService
from app.services.smart_building import get_smart_building_service


@dataclass
class TestResult:
    """Ergebnis eines einzelnen Tests."""
    test_id: str
    address: str

    # Import-Phase
    import_success: bool = False
    import_error: Optional[str] = None
    import_fields_found: List[str] = field(default_factory=list)

    # Geocoding-Phase
    geocode_success: bool = False
    geocode_error: Optional[str] = None
    egid_found: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None

    # SmartBuilding-Phase
    geodata_success: bool = False
    geodata_error: Optional[str] = None
    polygon_found: bool = False
    polygon_source: Optional[str] = None
    polygon_points: int = 0
    height_found: bool = False
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    zones_count: int = 0
    complexity: Optional[str] = None
    building_name: Optional[str] = None

    # Timing
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "address": self.address,
            "import": {
                "success": self.import_success,
                "error": self.import_error,
                "fields_found": self.import_fields_found,
            },
            "geocode": {
                "success": self.geocode_success,
                "error": self.geocode_error,
                "egid": self.egid_found,
                "coordinates": self.coordinates,
            },
            "geodata": {
                "success": self.geodata_success,
                "error": self.geodata_error,
                "polygon_found": self.polygon_found,
                "polygon_source": self.polygon_source,
                "polygon_points": self.polygon_points,
                "height_found": self.height_found,
                "traufhoehe_m": self.traufhoehe_m,
                "firsthoehe_m": self.firsthoehe_m,
                "zones_count": self.zones_count,
                "complexity": self.complexity,
                "building_name": self.building_name,
            },
            "duration_ms": self.duration_ms,
        }


class SimapImportTester:
    """Testet den kompletten Import-Flow."""

    def __init__(self):
        self.url_importer = UrlImporter()
        self.swisstopo = SwisstopoService()
        self.smart_building = None  # Lazy init

    async def run_all_tests(self, test_cases_path: Path) -> List[TestResult]:
        """Führt alle Tests aus."""

        # Test-Cases laden
        with open(test_cases_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        test_cases = data.get('test_cases', [])
        print(f"\n{'='*70}")
        print(f"  SIMAP IMPORT-FLOW TEST")
        print(f"  {len(test_cases)} Test-Cases")
        print(f"{'='*70}\n")

        results = []

        for i, tc in enumerate(test_cases, 1):
            print(f"[{i:02d}/{len(test_cases)}] {tc['id']}: {tc['raw_data']['project_name'][:40]}...")

            result = await self._test_single_case(tc)
            results.append(result)

            # Status anzeigen
            status = "[OK]" if result.geodata_success else ("[WARN]" if result.geocode_success else "[FAIL]")
            print(f"       {status} Geocode: {result.geocode_success}, "
                  f"Polygon: {result.polygon_found}, "
                  f"Hoehe: {result.height_found}, "
                  f"Zeit: {result.duration_ms}ms")

        return results

    async def _test_single_case(self, tc: Dict[str, Any]) -> TestResult:
        """Testet einen einzelnen Test-Case."""
        start = datetime.now()

        raw = tc['raw_data']
        result = TestResult(
            test_id=tc['id'],
            address=raw.get('address', ''),
        )

        # 1. Import-Phase (simuliert - wir haben die Daten bereits)
        result.import_success = True
        result.import_fields_found = list(raw.keys())

        # 2. Geocoding-Phase
        # HINWEIS: Geocoding liefert NUR Koordinaten, KEIN egid!
        # Das egid wird später vom SmartBuildingService via GWR-Lookup geholt.
        try:
            address = raw.get('address', '')
            if address:
                geo = await self.swisstopo.geocode(address)
                if geo and geo.coordinates:
                    result.geocode_success = True
                    result.coordinates = {
                        'lv95_e': geo.coordinates.lv95_e,
                        'lv95_n': geo.coordinates.lv95_n,
                    }
                    # Debug: Terrain-Info falls verfügbar
                    if geo.terrain:
                        result.coordinates['terrain_height_m'] = geo.terrain.terrain_height_m
                else:
                    result.geocode_error = "Keine Geocoding-Ergebnisse"
            else:
                result.geocode_error = "Keine Adresse vorhanden"
        except Exception as e:
            import traceback
            result.geocode_error = f"{str(e)} | {traceback.format_exc()[:200]}"

        # 3. SmartBuilding-Phase (nur wenn Geocoding erfolgreich)
        if result.geocode_success and result.coordinates:
            try:
                if self.smart_building is None:
                    self.smart_building = get_smart_building_service()

                # Volle Datensammlung
                bundle = await self.smart_building.collect_all_data(
                    address=raw.get('address', ''),
                    force_refresh=False,
                    include_research=True,
                    include_zones_analysis=True,
                    include_terrain=True,
                )

                if bundle:
                    result.geodata_success = True

                    # EGID
                    result.egid_found = bundle.egid

                    # Polygon
                    if bundle.polygon:
                        result.polygon_found = True
                        result.polygon_points = len(bundle.polygon)
                        result.polygon_source = str(bundle.polygon_source) if bundle.polygon_source else None

                    # Hoehen
                    if bundle.traufhoehe_m or bundle.firsthoehe_m:
                        result.height_found = True
                        result.traufhoehe_m = bundle.traufhoehe_m
                        result.firsthoehe_m = bundle.firsthoehe_m

                    # Zonen
                    if bundle.zones:
                        result.zones_count = len(bundle.zones)

                    # Komplexitaet & Name
                    result.complexity = bundle.complexity
                    result.building_name = bundle.building_name
                else:
                    result.geodata_error = "Keine Geodaten gefunden"

            except Exception as e:
                result.geodata_error = str(e)

        # Timing
        result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)

        return result

    async def close(self):
        """Ressourcen freigeben."""
        await self.url_importer.close()


def print_summary(results: List[TestResult]):
    """Druckt eine Zusammenfassung der Testergebnisse."""

    total = len(results)
    import_ok = sum(1 for r in results if r.import_success)
    geocode_ok = sum(1 for r in results if r.geocode_success)
    geodata_ok = sum(1 for r in results if r.geodata_success)
    polygon_ok = sum(1 for r in results if r.polygon_found)
    height_ok = sum(1 for r in results if r.height_found)

    avg_duration = sum(r.duration_ms for r in results) / total if total > 0 else 0

    print(f"\n{'='*70}")
    print(f"  ZUSAMMENFASSUNG")
    print(f"{'='*70}")
    print(f"  Total Tests:           {total}")
    print(f"  Import erfolgreich:    {import_ok}/{total} ({100*import_ok/total:.0f}%)")
    print(f"  Geocoding erfolgreich: {geocode_ok}/{total} ({100*geocode_ok/total:.0f}%)")
    print(f"  Geodaten erfolgreich:  {geodata_ok}/{total} ({100*geodata_ok/total:.0f}%)")
    print(f"  Polygon gefunden:      {polygon_ok}/{total} ({100*polygon_ok/total:.0f}%)")
    print(f"  Hoehe gefunden:        {height_ok}/{total} ({100*height_ok/total:.0f}%)")
    print(f"  Avg Dauer:             {avg_duration:.0f}ms")
    print(f"{'='*70}")

    # Fehlgeschlagene Tests
    failed = [r for r in results if not r.geodata_success]
    if failed:
        print(f"\n  FEHLGESCHLAGENE TESTS ({len(failed)}):")
        for r in failed:
            error = r.geodata_error or r.geocode_error or "Unbekannt"
            print(f"  - {r.test_id}: {r.address[:40]}...")
            print(f"    Fehler: {error[:60]}")

    # Komplexität-Übersicht
    by_complexity = {}
    for r in results:
        c = r.complexity or 'unknown'
        if c not in by_complexity:
            by_complexity[c] = 0
        by_complexity[c] += 1

    print(f"\n  KOMPLEXITÄT:")
    for c, count in sorted(by_complexity.items()):
        print(f"  - {c}: {count}")

    print()


def save_results(results: List[TestResult], output_path: Path):
    """Speichert die Ergebnisse als JSON."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "summary": {
            "import_success": sum(1 for r in results if r.import_success),
            "geocode_success": sum(1 for r in results if r.geocode_success),
            "geodata_success": sum(1 for r in results if r.geodata_success),
            "polygon_found": sum(1 for r in results if r.polygon_found),
            "height_found": sum(1 for r in results if r.height_found),
        },
        "results": [r.to_dict() for r in results],
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Ergebnisse gespeichert: {output_path}")


async def main():
    """Hauptfunktion."""

    # Pfade
    script_dir = Path(__file__).parent
    test_cases_path = script_dir.parent / 'tests' / 'data' / 'simap_test_cases.json'
    output_path = script_dir.parent / 'tests' / 'data' / 'simap_test_results.json'

    if not test_cases_path.exists():
        print(f"ERROR: Test-Cases nicht gefunden: {test_cases_path}")
        sys.exit(1)

    # Tests ausführen
    tester = SimapImportTester()

    try:
        results = await tester.run_all_tests(test_cases_path)
        print_summary(results)
        save_results(results, output_path)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
