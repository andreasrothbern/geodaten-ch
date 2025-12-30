#!/usr/bin/env python3
"""
Test-Script: Vergleich von 10+ Berner Gebaeuden

Dieses Script:
1. Ruft API-Daten fuer bekannte und unbekannte Gebaeude ab
2. Vergleicht die Daten mit den erwarteten Werten
3. Generiert einen Analyse-Prompt fuer Claude.ai

Verwendung:
    python scripts/test_building_comparison.py

Ausgabe:
    - docs/tests/building_comparison_results.json (Rohdaten)
    - docs/tests/building_comparison_prompt.md (Prompt fuer Claude.ai)

Stand: 30.12.2025
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Pfad zum Backend hinzufuegen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# HTTP Client
import httpx


# =============================================================================
# KONFIGURATION
# =============================================================================

API_BASE_URL = "https://acceptable-trust-production.up.railway.app"
# API_BASE_URL = "http://localhost:8000"  # Fuer lokale Tests

# Timeout fuer API-Calls (Sekunden)
API_TIMEOUT = 60.0

# Bekannte Gebaeude aus known_buildings.py (mit erwarteten Werten)
KNOWN_BUILDINGS = {
    "Bundesplatz 3, 3011 Bern": {
        "name": "Bundeshaus",
        "egid": "2242547",
        "expected_zones": 3,
        "zone_names": ["Arkaden", "Hauptgebaeude", "Kuppel"],
        "max_height": 64.0,
        "is_known": True,
    },
    "Rathausgasse 2, 3011 Bern": {
        "name": "Kirche St. Peter und Paul",
        "egid": "191821074",
        "expected_zones": 4,
        "zone_names": ["Kirchenschiff", "Seitenschiffe", "Chor", "Westturm"],
        "max_height": 54.6,
        "is_known": True,
    },
    "Muensterplatz 1, 3011 Bern": {
        "name": "Berner Muenster",
        "egid": "1230337",
        "expected_zones": 3,
        "zone_names": ["Kirchenschiff", "Seitenkapellen", "Turm"],
        "max_height": 100.3,
        "is_known": True,
    },
    "Kramgasse 49, 3011 Bern": {
        "name": "Einsteinhaus",
        "egid": "1234567",
        "expected_zones": 1,
        "zone_names": ["Hauptgebaeude"],
        "max_height": 16.0,
        "is_known": True,
    },
}

# Unbekannte Gebaeude (NICHT in known_buildings.py)
UNKNOWN_BUILDINGS = {
    "Bahnhofplatz 11, 3011 Bern": {
        "name": "Hotel Schweizerhof (erwartet)",
        "expected_type": "Hotel",
        "is_known": False,
    },
    "Bahnhofplatz 10, 3011 Bern": {
        "name": "Hauptbahnhof Bern (erwartet)",
        "expected_type": "Bahnhof",
        "is_known": False,
    },
    "Kornhausplatz 18, 3011 Bern": {
        "name": "Kornhaus (erwartet)",
        "expected_type": "Kulturgebaeude",
        "is_known": False,
    },
    "Theaterplatz 7, 3011 Bern": {
        "name": "Stadttheater (erwartet)",
        "expected_type": "Theater",
        "is_known": False,
    },
    "Hodlerstrasse 8, 3011 Bern": {
        "name": "Kunstmuseum (erwartet)",
        "expected_type": "Museum",
        "is_known": False,
    },
    "Helvetiaplatz 5, 3005 Bern": {
        "name": "Historisches Museum (erwartet)",
        "expected_type": "Museum",
        "is_known": False,
    },
}


@dataclass
class BuildingTestResult:
    """Ergebnis eines Gebaeude-Tests"""
    address: str
    expected_name: str
    actual_name: Optional[str]
    egid: Optional[str]

    # Zonen
    expected_zones: Optional[int]
    actual_zones: int
    zone_details: List[Dict]

    # Hoehen
    traufhoehe_m: Optional[float]
    firsthoehe_m: Optional[float]
    max_zone_height: Optional[float]

    # Qualitaet
    complexity: Optional[str]
    data_quality: Optional[str]
    warnings: List[str]

    # API-Metriken
    api_calls_used: List[str]
    response_time_ms: int
    is_known_building: bool

    # Match-Bewertung
    name_match: bool
    zones_match: bool

    # Rohdaten
    raw_data: Dict


@dataclass
class APIMetrics:
    """API-Call Metriken"""
    total_calls: int
    calls_by_type: Dict[str, int]
    total_time_ms: int
    avg_time_ms: float
    errors: List[str]


async def fetch_building_data(
    client: httpx.AsyncClient,
    address: str
) -> Dict[str, Any]:
    """
    Ruft Gebaeudedaten von der Smart-Building API ab.

    Returns:
        Dict mit Gebaeudedaten und Metadaten
    """
    url = f"{API_BASE_URL}/api/v1/smart-building/data"
    params = {
        "address": address,
        "include_research": "true",
        "include_zones": "true",
        "include_terrain": "true",
    }

    start_time = datetime.now()

    try:
        response = await client.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        end_time = datetime.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return {
            "success": True,
            "data": data,
            "response_time_ms": response_time_ms,
            "error": None,
        }

    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "data": None,
            "response_time_ms": 0,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "response_time_ms": 0,
            "error": str(e),
        }


async def fetch_prompt_data(
    client: httpx.AsyncClient,
    address: str
) -> Dict[str, Any]:
    """
    Ruft den generierten Prompt von der API ab.
    """
    url = f"{API_BASE_URL}/api/v1/smart-building/prompt"
    params = {
        "address": address,
        "svg_type": "all",
    }

    try:
        response = await client.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        return {
            "success": True,
            "prompt": data.get("prompt", ""),
            "data_sources": data.get("data_sources", {}),
        }

    except Exception as e:
        return {
            "success": False,
            "prompt": "",
            "error": str(e),
        }


async def test_building(
    client: httpx.AsyncClient,
    address: str,
    expected: Dict[str, Any]
) -> BuildingTestResult:
    """
    Testet ein einzelnes Gebaeude und vergleicht mit Erwartungen.
    """
    print(f"  Testing: {address}")

    # API-Call
    result = await fetch_building_data(client, address)

    if not result["success"]:
        return BuildingTestResult(
            address=address,
            expected_name=expected.get("name", "Unbekannt"),
            actual_name=None,
            egid=None,
            expected_zones=expected.get("expected_zones"),
            actual_zones=0,
            zone_details=[],
            traufhoehe_m=None,
            firsthoehe_m=None,
            max_zone_height=None,
            complexity=None,
            data_quality=None,
            warnings=[result["error"]],
            api_calls_used=["smart-building/data (FAILED)"],
            response_time_ms=0,
            is_known_building=expected.get("is_known", False),
            name_match=False,
            zones_match=False,
            raw_data={"error": result["error"]},
        )

    data = result["data"]

    # Zonen extrahieren
    zones = data.get("zones", [])
    zone_details = [
        {
            "name": z.get("name"),
            "type": z.get("zone_type"),
            "traufhoehe_m": z.get("traufhoehe_m"),
            "firsthoehe_m": z.get("firsthoehe_m"),
            "sonderkonstruktion": z.get("sonderkonstruktion", False),
        }
        for z in zones
    ]

    # Max Zonenhoehe
    max_zone_height = max(
        (z.get("firsthoehe_m", 0) or 0 for z in zones),
        default=0
    )

    # Name-Match pruefen
    actual_name = data.get("building_name")
    expected_name = expected.get("name", "")
    name_match = (
        actual_name and
        expected_name and
        (expected_name.lower() in actual_name.lower() or
         actual_name.lower() in expected_name.lower())
    )

    # Zonen-Match pruefen
    expected_zones = expected.get("expected_zones")
    zones_match = (
        expected_zones is None or
        len(zones) >= expected_zones
    )

    # API-Calls aus data_sources rekonstruieren
    data_sources = data.get("data_sources", [])
    api_calls = []
    if isinstance(data_sources, list):
        for ds in data_sources:
            if isinstance(ds, dict):
                api_calls.append(ds.get("name", "unknown"))
            else:
                api_calls.append(str(ds))

    return BuildingTestResult(
        address=address,
        expected_name=expected.get("name", "Unbekannt"),
        actual_name=actual_name,
        egid=data.get("egid"),
        expected_zones=expected_zones,
        actual_zones=len(zones),
        zone_details=zone_details,
        traufhoehe_m=data.get("traufhoehe_m"),
        firsthoehe_m=data.get("firsthoehe_m"),
        max_zone_height=max_zone_height,
        complexity=data.get("complexity"),
        data_quality=data.get("overall_quality"),
        warnings=data.get("warnings", []),
        api_calls_used=api_calls or ["smart-building/data"],
        response_time_ms=result["response_time_ms"],
        is_known_building=expected.get("is_known", False),
        name_match=name_match,
        zones_match=zones_match,
        raw_data=data,
    )


def generate_analysis_prompt(
    results: List[BuildingTestResult],
    metrics: APIMetrics
) -> str:
    """
    Generiert einen Analyse-Prompt fuer Claude.ai.
    """
    prompt = """# Analyse: Berner Gebaeude - API-Daten vs. Prompt-Generierung

## Aufgabe

Analysiere die folgenden API-Ergebnisse fuer 10+ Berner Gebaeude und identifiziere:

1. **Datenqualitaet**: Wie vollstaendig und korrekt sind die gesammelten Daten?
2. **Zonen-Erkennung**: Werden die Hoehenzonen korrekt erkannt?
3. **Bekannte vs. Unbekannte Gebaeude**: Funktioniert der Fallback fuer unbekannte Gebaeude?
4. **Optimierungspotential**: Was kann verbessert werden?

---

## Test-Ergebnisse

"""

    # Bekannte Gebaeude
    prompt += "### Bekannte Gebaeude (in known_buildings.py)\n\n"
    known_results = [r for r in results if r.is_known_building]

    for r in known_results:
        status = "OK" if r.name_match and r.zones_match else "WARNUNG"
        prompt += f"""#### {r.address}
- **Status:** {status}
- **Erwartet:** {r.expected_name} ({r.expected_zones} Zonen)
- **Erhalten:** {r.actual_name or 'N/A'} ({r.actual_zones} Zonen)
- **Hoehen:** Traufe {r.traufhoehe_m or 'N/A'}m, First {r.firsthoehe_m or 'N/A'}m
- **Max. Zonenhoehe:** {r.max_zone_height or 'N/A'}m
- **Komplexitaet:** {r.complexity or 'N/A'}
- **Response-Zeit:** {r.response_time_ms}ms

**Zonen:**
"""
        for z in r.zone_details:
            prompt += f"  - {z['name']} ({z['type']}): {z['traufhoehe_m']}m - {z['firsthoehe_m']}m\n"

        if r.warnings:
            prompt += f"\n**Warnungen:** {', '.join(r.warnings)}\n"
        prompt += "\n"

    # Unbekannte Gebaeude
    prompt += "### Unbekannte Gebaeude (NICHT in known_buildings.py)\n\n"
    unknown_results = [r for r in results if not r.is_known_building]

    for r in unknown_results:
        prompt += f"""#### {r.address}
- **Erwartet:** {r.expected_name}
- **Erhalten:** {r.actual_name or 'N/A'} ({r.actual_zones} Zonen)
- **Hoehen:** Traufe {r.traufhoehe_m or 'N/A'}m, First {r.firsthoehe_m or 'N/A'}m
- **Komplexitaet:** {r.complexity or 'N/A'}
- **Response-Zeit:** {r.response_time_ms}ms

**Zonen:**
"""
        for z in r.zone_details:
            prompt += f"  - {z['name']} ({z['type']}): {z['traufhoehe_m']}m - {z['firsthoehe_m']}m\n"

        if r.warnings:
            prompt += f"\n**Warnungen:** {', '.join(r.warnings)}\n"
        prompt += "\n"

    # API-Metriken
    prompt += f"""---

## API-Metriken

| Metrik | Wert |
|--------|------|
| Anzahl Gebaeude | {len(results)} |
| Erfolgreiche Abfragen | {sum(1 for r in results if r.actual_name)} |
| Fehlgeschlagene Abfragen | {sum(1 for r in results if not r.actual_name)} |
| Gesamtzeit | {metrics.total_time_ms}ms |
| Durchschnittszeit | {metrics.avg_time_ms:.0f}ms |

### API-Calls pro Gebaeude

Die SmartBuildingService-Pipeline fuehrt folgende Schritte aus:

1. **Geocoding** (swisstopo API)
2. **GWR-Daten** (swisstopo API)
3. **Hoehendaten** (swissBUILDINGS3D DB oder On-Demand)
4. **Terrain** (swissALTI3D API)
5. **Polygon** (geodienste.ch WFS)
6. **Dach-Analyse** (berechnet)
7. **Recherche** (known_buildings.py ODER Claude Haiku API)
8. **Zonen-Analyse** (bei komplexen Gebaeuden: Claude Sonnet)
9. **SUVA Zugaenge** (berechnet)
10. **Qualitaetsbewertung** (berechnet)

---

## Analyse-Fragen

Bitte beantworte folgende Fragen:

### 1. Datenqualitaet

- Sind die Hoehendaten konsistent?
- Fehlen wichtige Informationen?
- Gibt es offensichtliche Fehler?

### 2. Zonen-Erkennung

- Werden bei bekannten Gebaeuden alle Zonen korrekt erkannt?
- Sind die Zonen-Namen sinnvoll?
- Stimmen die Hoehenwerte mit der Realitaet ueberein?

### 3. Bekannte vs. Unbekannte Gebaeude

- Funktioniert der Fallback fuer unbekannte Gebaeude?
- Welche Gebaeude sollten zu known_buildings.py hinzugefuegt werden?
- Ist die automatische Komplexitaets-Erkennung zuverlaessig?

### 4. Optimierungspotential

- Welche Verbesserungen sind empfehlenswert?
- Wo sind die groessten Datenluecken?
- Wie koennte die Prompt-Generierung verbessert werden?

### 5. Kosten-Nutzen

- Sind die Claude-API-Calls (Haiku + Sonnet) gerechtfertigt?
- Wo koennte man API-Calls einsparen?
- Welche Gebaeude benoetigen zwingend Claude-Analyse?

---

## Zusammenfassung

Erstelle eine Zusammenfassung mit:
1. **Staerken** des aktuellen Systems
2. **Schwaechen** und Verbesserungsvorschlaege
3. **Priorisierte Massnahmen** (nach Impact sortiert)

"""

    return prompt


async def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("BUILDING COMPARISON TEST")
    print(f"API: {API_BASE_URL}")
    print(f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print()

    # Alle Gebaeude zusammenfassen
    all_buildings = {**KNOWN_BUILDINGS, **UNKNOWN_BUILDINGS}

    print(f"Teste {len(all_buildings)} Gebaeude...")
    print()

    results: List[BuildingTestResult] = []
    total_time_ms = 0

    async with httpx.AsyncClient() as client:
        for address, expected in all_buildings.items():
            result = await test_building(client, address, expected)
            results.append(result)
            total_time_ms += result.response_time_ms

            # Kurze Pause zwischen Requests
            await asyncio.sleep(0.5)

    # Metriken berechnen
    metrics = APIMetrics(
        total_calls=len(results),
        calls_by_type={
            "known": sum(1 for r in results if r.is_known_building),
            "unknown": sum(1 for r in results if not r.is_known_building),
        },
        total_time_ms=total_time_ms,
        avg_time_ms=total_time_ms / len(results) if results else 0,
        errors=[r.warnings[0] for r in results if r.warnings and not r.actual_name],
    )

    # Ausgabe-Verzeichnis erstellen
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs", "tests"
    )
    os.makedirs(output_dir, exist_ok=True)

    # JSON-Ergebnisse speichern
    json_path = os.path.join(output_dir, "building_comparison_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "api_base_url": API_BASE_URL,
                "metrics": asdict(metrics),
                "results": [asdict(r) for r in results],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\nJSON gespeichert: {json_path}")

    # Analyse-Prompt generieren
    prompt = generate_analysis_prompt(results, metrics)
    prompt_path = os.path.join(output_dir, "building_comparison_prompt.md")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"Prompt gespeichert: {prompt_path}")

    # Zusammenfassung ausgeben
    print()
    print("=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"Getestete Gebaeude: {len(results)}")
    print(f"  - Bekannt: {metrics.calls_by_type['known']}")
    print(f"  - Unbekannt: {metrics.calls_by_type['unknown']}")
    print(f"Erfolgreiche Abfragen: {sum(1 for r in results if r.actual_name)}")
    print(f"Fehlgeschlagene Abfragen: {sum(1 for r in results if not r.actual_name)}")
    print(f"Gesamtzeit: {metrics.total_time_ms}ms")
    print(f"Durchschnittszeit: {metrics.avg_time_ms:.0f}ms")
    print()
    print(f"Kopiere den Prompt aus: {prompt_path}")
    print("Fuege ihn in Claude.ai ein fuer die Analyse.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
