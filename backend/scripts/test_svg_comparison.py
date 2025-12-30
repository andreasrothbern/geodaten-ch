#!/usr/bin/env python3
"""
Test-Script: SVG-Vergleich & Prompt-Export

Dieses Script implementiert die Teststrategie fuer SVG-Qualitaet:

1. Cache leeren
2. Fuer jedes Testgebaeude:
   - Recherche-Prompt exportieren
   - SVG-Prompt exportieren (identisch fuer API & Claude.ai)
   - SVG ueber Claude API generieren
3. Report-Ordner mit allen Artefakten erstellen

Verwendung:
    python scripts/test_svg_comparison.py

    # Optionale Parameter:
    python scripts/test_svg_comparison.py --buildings "Bundeshaus,Muenster"
    python scripts/test_svg_comparison.py --svg-types "schnitt,ansicht"
    python scripts/test_svg_comparison.py --api-url "http://localhost:8000"

Stand: 30.12.2025
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# Backend-Pfad hinzufuegen
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx


# =============================================================================
# KONFIGURATION
# =============================================================================

API_BASE_URL = "https://acceptable-trust-production.up.railway.app"
# API_BASE_URL = "http://localhost:8000"

API_TIMEOUT = 120.0  # SVG-Generierung kann laenger dauern

# Testgebaeude (Standard-Set: 10 Gebaeude Stadt Bern)
# 5 bekannte (in known_buildings.py) + 5 unbekannte
TEST_BUILDINGS = [
    # Bekannte Gebaeude (in known_buildings.py)
    {"address": "Bundesplatz 3, 3011 Bern", "name": "Bundeshaus", "complexity": "complex", "known": True},
    {"address": "Muensterplatz 1, 3011 Bern", "name": "Berner Muenster", "complexity": "complex", "known": True},
    {"address": "Rathausgasse 2, 3011 Bern", "name": "St. Peter und Paul", "complexity": "complex", "known": True},
    {"address": "Kramgasse 49, 3011 Bern", "name": "Einsteinhaus", "complexity": "simple", "known": True},
    {"address": "Hodlerstrasse 8, 3011 Bern", "name": "Kunstmuseum", "complexity": "complex", "known": True},
    # Unbekannte Gebaeude (dynamische Claude-Recherche)
    {"address": "Kornhausplatz 18, 3011 Bern", "name": "Kornhaus", "complexity": "complex", "known": False},
    {"address": "Bahnhofplatz 10, 3011 Bern", "name": "Hauptbahnhof", "complexity": "complex", "known": False},
    {"address": "Theaterplatz 7, 3011 Bern", "name": "Stadttheater", "complexity": "complex", "known": False},
    {"address": "Helvetiaplatz 5, 3005 Bern", "name": "Historisches Museum", "complexity": "complex", "known": False},
    {"address": "Bahnhofplatz 11, 3011 Bern", "name": "Hotel Schweizerhof", "complexity": "moderate", "known": False},
]

# SVG-Typen
SVG_TYPES = ["grundriss", "ansicht", "schnitt"]


@dataclass
class BuildingTestResult:
    """Ergebnis eines Gebaeude-Tests"""
    address: str
    name: str
    egid: Optional[str] = None

    # Prompts
    recherche_prompt: Optional[str] = None
    svg_prompts: Dict[str, str] = field(default_factory=dict)

    # SVGs
    svgs: Dict[str, str] = field(default_factory=dict)

    # Metriken
    response_times: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    # Rohdaten
    building_data: Optional[Dict] = None


async def clear_cache_for_building(
    client: httpx.AsyncClient,
    api_url: str,
    address: str
) -> Dict:
    """Leert den Cache fuer ein einzelnes Gebaeude."""
    url = f"{api_url}/api/v1/smart-building/cache"
    params = {"address": address}
    try:
        response = await client.delete(url, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "address": address}


async def clear_caches_for_buildings(
    client: httpx.AsyncClient,
    api_url: str,
    buildings: List[Dict]
) -> Dict:
    """Leert die Caches nur fuer die Testgebaeude (nicht global)."""
    results = []
    total_deleted = 0

    for building in buildings:
        address = building["address"]
        result = await clear_cache_for_building(client, api_url, address)
        results.append(result)
        if "total" in result:
            total_deleted += result.get("total", 0)

    return {
        "status": "ok",
        "buildings_cleared": len(buildings),
        "total_deleted": total_deleted,
        "details": results
    }


async def fetch_building_data(
    client: httpx.AsyncClient,
    api_url: str,
    address: str
) -> Dict[str, Any]:
    """Ruft Gebaeudedaten ab."""
    url = f"{api_url}/api/v1/smart-building/data"
    params = {
        "address": address,
        "include_research": "true",
        "include_zones": "true",
        "include_terrain": "true",
    }

    start = datetime.now()
    try:
        response = await client.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        elapsed = int((datetime.now() - start).total_seconds() * 1000)
        return {"success": True, "data": data, "time_ms": elapsed}
    except Exception as e:
        return {"success": False, "error": str(e), "time_ms": 0}


async def fetch_prompt(
    client: httpx.AsyncClient,
    api_url: str,
    address: str,
    svg_type: str
) -> Dict[str, Any]:
    """Ruft den SVG-Prompt ab."""
    url = f"{api_url}/api/v1/smart-building/prompt"
    params = {
        "address": address,
        "svg_type": svg_type,
    }

    try:
        response = await client.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return {"success": True, "prompt": data.get("prompt", "")}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def fetch_svg(
    client: httpx.AsyncClient,
    api_url: str,
    address: str,
    svg_type: str
) -> Dict[str, Any]:
    """Generiert SVG ueber die API."""
    url = f"{api_url}/api/v1/smart-building/svg"
    params = {
        "address": address,
        "svg_type": svg_type,
    }

    start = datetime.now()
    try:
        response = await client.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        elapsed = int((datetime.now() - start).total_seconds() * 1000)

        # SVG wird direkt als Text zurueckgegeben, nicht als JSON
        content_type = response.headers.get("content-type", "")
        if "svg" in content_type or response.text.strip().startswith("<svg"):
            return {
                "success": True,
                "svg": response.text,
                "time_ms": elapsed
            }
        else:
            # Fallback: versuche JSON zu parsen
            try:
                data = response.json()
                return {
                    "success": True,
                    "svg": data.get("svg", ""),
                    "time_ms": elapsed
                }
            except:
                return {
                    "success": True,
                    "svg": response.text,
                    "time_ms": elapsed
                }
    except Exception as e:
        return {"success": False, "error": str(e), "time_ms": 0}


def create_recherche_prompt_doc(building_data: Dict, address: str) -> str:
    """Erstellt ein Dokument mit dem Recherche-Prompt."""
    name = building_data.get("building_name", "Unbekannt")

    doc = f"""# Recherche-Prompt: {name}

## Adresse
{address}

## Kontext

Dieser Prompt wird verwendet, um Gebaeudeinformationen via Claude Sonnet zu recherchieren.
Er wird in `research_integration.py` und `known_buildings.py` verarbeitet.

## Erhaltene Daten

### Identifikation
- **EGID:** {building_data.get("egid", "N/A")}
- **Gebaeudename:** {building_data.get("building_name", "N/A")}
- **Gebaeudetyp:** {building_data.get("building_type", "N/A")}
- **Architekturstil:** {building_data.get("architectural_style", "N/A")}
- **Baujahr:** {building_data.get("construction_year", "N/A")}

### Hoehen
- **Traufhoehe:** {building_data.get("traufhoehe_m", "N/A")} m
- **Firsthoehe:** {building_data.get("firsthoehe_m", "N/A")} m
- **Komplexitaet:** {building_data.get("complexity", "N/A")}

### Zonen
"""

    zones = building_data.get("zones", [])
    if zones:
        for i, zone in enumerate(zones, 1):
            doc += f"""
#### Zone {i}: {zone.get("name", "Unbenannt")}
- **Typ:** {zone.get("zone_type", "N/A")}
- **Traufhoehe:** {zone.get("traufhoehe_m", "N/A")} m
- **Firsthoehe:** {zone.get("firsthoehe_m", "N/A")} m
- **Sonderkonstruktion:** {"Ja" if zone.get("sonderkonstruktion") else "Nein"}
"""
    else:
        doc += "\n*Keine Zonen definiert*\n"

    doc += """
## Analyse-Fragen fuer Claude.ai

1. Sind die Zonen korrekt erkannt?
2. Fehlen wichtige Hoehenzonen?
3. Stimmen die Hoehenwerte mit der Realitaet ueberein?
4. Welche zusaetzlichen Informationen waeren hilfreich?

## Optimierungsvorschlaege

(Wird von Claude.ai ausgefuellt)
"""

    return doc


def create_claude_ai_bundle(
    results: List[BuildingTestResult],
    timestamp: str
) -> str:
    """
    Erstellt ein einzelnes Dokument fuer Claude.ai mit allen Artefakten.
    Enthaelt: Anweisungen, alle Prompts, alle SVGs, Recherche-Daten.
    """

    bundle = f"""# Claude.ai Analyse-Bundle: {timestamp}

## ANWEISUNGEN FÜR CLAUDE.AI

Dieses Dokument enthält Test-Ergebnisse unserer SVG-Generierungs-Pipeline für Gerüstplanung.

### Deine Aufgaben:

**1. SVG-Generierung & Vergleich**
- Generiere für JEDES Gebäude die SVGs (Grundriss, Ansicht, Schnitt) basierend auf den mitgelieferten Prompts
- Vergleiche deine generierten SVGs mit den SVGs der Claude-API (unten aufgeführt)
- Dokumentiere Unterschiede: Was macht die API anders? Was ist besser/schlechter?

**2. Prompt-Analyse**
- Analysiere die SVG-Prompts: Was ist fehlerhaft, verbesserungswürdig, perfekt?
- Analysiere die Recherche-Prompts: Werden die richtigen Gebäudedaten erkannt?
- Identifiziere Inkonsistenzen zwischen Prompt und generiertem SVG

**3. Verbesserungsvorschläge**
- Erstelle konkrete, priorisierte Verbesserungsvorschläge für die Prompts
- Unterscheide: Quick Wins vs. größere Änderungen
- Berücksichtige die gesamte Pipeline (Recherche → Daten → SVG-Prompt → SVG)

### Ausgabe-Format:

Bitte strukturiere deine Analyse wie folgt:

```
## Gebäude: [Name]

### SVG-Vergleich
| Typ | API-Qualität | Deine Version | Unterschiede |
|-----|--------------|---------------|--------------|

### Prompt-Bewertung
- Stärken: ...
- Schwächen: ...
- Fehler: ...

### Verbesserungsvorschläge
1. ...
2. ...
```

---

## ÜBERSICHT TESTGEBÄUDE

| Nr | Gebäude | Komplexität | Status |
|----|---------|-------------|--------|
"""

    for i, r in enumerate(results, 1):
        known = "bekannt" if r.building_data and r.building_data.get("building_name") else "unbekannt"
        bundle += f"| {i} | {r.name} | {r.building_data.get('complexity', 'N/A') if r.building_data else 'N/A'} | {known} |\n"

    bundle += "\n---\n\n"

    # Pro Gebäude: Recherche-Daten, Prompts, SVGs
    for i, result in enumerate(results, 1):
        bundle += f"""
================================================================================
# GEBÄUDE {i}: {result.name}
================================================================================

## Adresse
{result.address}

## EGID
{result.egid or 'N/A'}

## Recherche-Ergebnis (aus Pipeline)

"""
        if result.building_data:
            bd = result.building_data
            bundle += f"""- **Gebäudename:** {bd.get('building_name', 'N/A')}
- **Gebäudetyp:** {bd.get('building_type', 'N/A')}
- **Architekturstil:** {bd.get('architectural_style', 'N/A')}
- **Baujahr:** {bd.get('construction_year', 'N/A')}
- **Komplexität:** {bd.get('complexity', 'N/A')}
- **Traufhöhe:** {bd.get('traufhoehe_m', 'N/A')} m
- **Firsthöhe:** {bd.get('firsthoehe_m', 'N/A')} m

### Erkannte Zonen

"""
            zones = bd.get('zones', [])
            if zones:
                for j, zone in enumerate(zones, 1):
                    bundle += f"""**Zone {j}: {zone.get('name', 'Unbenannt')}**
- Typ: {zone.get('zone_type', 'N/A')}
- Traufhöhe: {zone.get('traufhoehe_m', 'N/A')} m
- Firsthöhe: {zone.get('firsthoehe_m', 'N/A')} m
- Sonderkonstruktion: {"Ja" if zone.get('sonderkonstruktion') else "Nein"}

"""
            else:
                bundle += "*Keine Zonen definiert*\n\n"

        # SVG-Prompts und generierte SVGs
        for svg_type in SVG_TYPES:
            prompt = result.svg_prompts.get(svg_type, "")
            svg = result.svgs.get(svg_type, "")

            bundle += f"""
--------------------------------------------------------------------------------
## {svg_type.upper()}-PROMPT
--------------------------------------------------------------------------------

```
{prompt}
```

--------------------------------------------------------------------------------
## {svg_type.upper()}-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
{svg}
```

"""

    # Abschluss
    bundle += f"""
================================================================================
# ZUSAMMENFASSUNG & ANALYSE-AUFFORDERUNG
================================================================================

## Statistik

- **Getestete Gebäude:** {len(results)}
- **Generierte SVGs:** {sum(len(r.svgs) for r in results)}
- **Erfolgsrate:** {sum(len(r.svgs) for r in results) / (len(results) * len(SVG_TYPES)) * 100:.1f}%

## Bitte analysiere nun:

1. **Generiere die SVGs** basierend auf den Prompts oben
2. **Vergleiche** mit den API-generierten SVGs
3. **Bewerte** die Prompt-Qualität
4. **Erstelle** priorisierte Verbesserungsvorschläge

Fokussiere besonders auf:
- Proportionen und Maßstäbe
- Zonen-Darstellung (werden alle Zonen korrekt gezeichnet?)
- Technischer Zeichnungsstil (nicht künstlerisch!)
- Gerüst-Elemente (Ständer, Verankerungen, Zugänge)
- Beschriftungen und Lesbarkeit

---

*Generiert: {timestamp}*
*Pipeline: SmartBuildingService + Claude Sonnet SVG-Generierung*
"""

    return bundle


def create_report(
    results: List[BuildingTestResult],
    timestamp: str,
    cache_result: Dict
) -> str:
    """Erstellt den Report."""

    report = f"""# Test-Report: {timestamp}

## Uebersicht

| Metrik | Wert |
|--------|------|
| **Testzeit** | {timestamp} |
| **API** | {API_BASE_URL} |
| **Getestete Gebaeude** | {len(results)} |
| **SVG-Typen** | {", ".join(SVG_TYPES)} |

### Cache-Status vor Test

```json
{json.dumps(cache_result, indent=2, ensure_ascii=False)}
```

---

## Ergebnisse pro Gebaeude

"""

    for result in results:
        status = "OK" if not result.errors else "FEHLER"
        report += f"""### {result.name}

**Adresse:** {result.address}
**EGID:** {result.egid or "N/A"}
**Status:** {status}

#### SVG-Generierung

| Typ | Status | Zeit |
|-----|--------|------|
"""
        for svg_type in SVG_TYPES:
            svg = result.svgs.get(svg_type)
            time_ms = result.response_times.get(f"svg_{svg_type}", 0)
            svg_status = "OK" if svg else "FEHLER"
            report += f"| {svg_type} | {svg_status} | {time_ms}ms |\n"

        if result.errors:
            report += f"\n**Fehler:** {', '.join(result.errors)}\n"

        report += "\n---\n\n"

    # Zusammenfassung
    total_svgs = sum(len(r.svgs) for r in results)
    expected_svgs = len(results) * len(SVG_TYPES)
    success_rate = (total_svgs / expected_svgs * 100) if expected_svgs > 0 else 0

    avg_time = 0
    time_count = 0
    for r in results:
        for key, val in r.response_times.items():
            if key.startswith("svg_"):
                avg_time += val
                time_count += 1
    avg_time = avg_time / time_count if time_count > 0 else 0

    report += f"""## Zusammenfassung

| Metrik | Wert |
|--------|------|
| **SVGs generiert** | {total_svgs}/{expected_svgs} |
| **Erfolgsrate** | {success_rate:.1f}% |
| **Durchschnittliche SVG-Zeit** | {avg_time:.0f}ms |

---

## Dateien in diesem Report

### Recherche-Prompts
```
recherche_prompts/
"""
    for r in results:
        safe_name = r.name.lower().replace(" ", "_").replace(".", "")
        report += f"  {safe_name}_recherche.md\n"

    report += """```

### SVG-Prompts
```
svg_prompts/
"""
    for r in results:
        safe_name = r.name.lower().replace(" ", "_").replace(".", "")
        for svg_type in SVG_TYPES:
            report += f"  {safe_name}_{svg_type}_prompt.md\n"

    report += """```

### API-generierte SVGs
```
svg_api/
"""
    for r in results:
        safe_name = r.name.lower().replace(" ", "_").replace(".", "")
        for svg_type in SVG_TYPES:
            if svg_type in r.svgs:
                report += f"  {safe_name}_{svg_type}.svg\n"

    report += """```

---

## Naechste Schritte

1. **SVG-Vergleich:** Kopiere einen SVG-Prompt zu Claude.ai und vergleiche das Ergebnis
2. **Recherche-Analyse:** Pruefe ob die Zonen korrekt erkannt wurden
3. **Optimierungen:** Dokumentiere Verbesserungsvorschlaege

---

## Analyse mit Claude.ai

### Prompt fuer Gesamtanalyse

Kopiere diesen Text plus die relevanten Dateien zu Claude.ai:

```
Hier ist ein Test-Report unserer SVG-Generierungs-Pipeline.

Bitte analysiere:

1. **SVG-Qualitaet**
   - Sind die Proportionen korrekt?
   - Werden alle Zonen dargestellt?
   - Entspricht der Stil einer technischen Zeichnung?

2. **Recherche-Qualitaet**
   - Sind die Gebaeude korrekt erkannt?
   - Fehlen wichtige Hoehenzonen?
   - Welche Gebaeude sollten zu known_buildings.py hinzugefuegt werden?

3. **Prompt-Optimierung**
   - Was kann am SVG-Prompt verbessert werden?
   - Was kann am Recherche-Prompt verbessert werden?

4. **Priorisierte Massnahmen**
   - Quick Wins (sofort umsetzbar)
   - Mittelfristig (1-2 Tage)
   - Langfristig (ML-System)

[REPORT UND DATEIEN HIER EINFUEGEN]
```

---

*Generiert: {timestamp}*
*Script: test_svg_comparison.py*
"""

    return report


async def test_building(
    client: httpx.AsyncClient,
    api_url: str,
    building: Dict,
    svg_types: List[str]
) -> BuildingTestResult:
    """Testet ein einzelnes Gebaeude."""

    address = building["address"]
    name = building["name"]

    print(f"\n  Testing: {name}")

    result = BuildingTestResult(address=address, name=name)

    # 1. Gebaeudedaten abrufen
    print(f"    -> Gebaeudedaten...")
    data_result = await fetch_building_data(client, api_url, address)

    if not data_result["success"]:
        result.errors.append(f"Daten: {data_result.get('error', 'Unbekannt')}")
        return result

    result.building_data = data_result["data"]
    result.egid = data_result["data"].get("egid")
    result.response_times["data"] = data_result["time_ms"]

    # 2. Recherche-Prompt erstellen (aus den Daten)
    result.recherche_prompt = create_recherche_prompt_doc(
        result.building_data, address
    )

    # 3. Fuer jeden SVG-Typ: Prompt + SVG
    for svg_type in svg_types:
        print(f"    -> {svg_type}...")

        # Prompt abrufen
        prompt_result = await fetch_prompt(client, api_url, address, svg_type)
        if prompt_result["success"]:
            result.svg_prompts[svg_type] = prompt_result["prompt"]
        else:
            result.errors.append(f"Prompt {svg_type}: {prompt_result.get('error')}")

        # SVG generieren
        svg_result = await fetch_svg(client, api_url, address, svg_type)
        if svg_result["success"] and svg_result.get("svg"):
            result.svgs[svg_type] = svg_result["svg"]
            result.response_times[f"svg_{svg_type}"] = svg_result["time_ms"]
        else:
            error = svg_result.get("error", "Kein SVG erhalten")
            result.errors.append(f"SVG {svg_type}: {error}")

        # Kurze Pause zwischen Requests
        await asyncio.sleep(0.5)

    return result


def save_results(
    results: List[BuildingTestResult],
    report: str,
    claude_bundle: str,
    output_dir: Path
):
    """Speichert alle Ergebnisse im Report-Ordner."""

    # Ordner erstellen
    (output_dir / "recherche_prompts").mkdir(parents=True, exist_ok=True)
    (output_dir / "svg_prompts").mkdir(parents=True, exist_ok=True)
    (output_dir / "svg_api").mkdir(parents=True, exist_ok=True)

    # Report speichern
    (output_dir / "report.md").write_text(report, encoding="utf-8")

    # Claude.ai Bundle speichern (ALLES IN EINEM FILE)
    (output_dir / "CLAUDE_AI_ANALYSE.md").write_text(claude_bundle, encoding="utf-8")

    # Pro Gebaeude
    for result in results:
        safe_name = result.name.lower().replace(" ", "_").replace(".", "")

        # Recherche-Prompt
        if result.recherche_prompt:
            path = output_dir / "recherche_prompts" / f"{safe_name}_recherche.md"
            path.write_text(result.recherche_prompt, encoding="utf-8")

        # SVG-Prompts
        for svg_type, prompt in result.svg_prompts.items():
            path = output_dir / "svg_prompts" / f"{safe_name}_{svg_type}_prompt.md"
            # Prompt als Markdown-Dokument
            doc = f"""# SVG-Prompt: {result.name} - {svg_type.capitalize()}

## Verwendung

Dieser Prompt ist **identisch** mit dem Prompt der von der Claude API verwendet wird.
Kopiere ihn zu Claude.ai um das SVG zu generieren und vergleiche das Ergebnis.

---

{prompt}
"""
            path.write_text(doc, encoding="utf-8")

        # SVGs
        for svg_type, svg in result.svgs.items():
            path = output_dir / "svg_api" / f"{safe_name}_{svg_type}.svg"
            path.write_text(svg, encoding="utf-8")

    # JSON mit allen Rohdaten
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "api_url": API_BASE_URL,
        "results": [
            {
                "address": r.address,
                "name": r.name,
                "egid": r.egid,
                "svg_types": list(r.svgs.keys()),
                "response_times": r.response_times,
                "errors": r.errors,
                "building_data": r.building_data,
            }
            for r in results
        ]
    }
    (output_dir / "results.json").write_text(
        json.dumps(json_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


async def main():
    """Hauptfunktion"""

    parser = argparse.ArgumentParser(description="SVG-Vergleich Test")
    parser.add_argument("--buildings", help="Komma-separierte Liste von Gebaeuden")
    parser.add_argument("--svg-types", help="Komma-separierte Liste von SVG-Typen")
    parser.add_argument("--api-url", default=API_BASE_URL, help="API URL")
    args = parser.parse_args()

    api_url = args.api_url

    # Gebaeude filtern
    buildings = TEST_BUILDINGS
    if args.buildings:
        filter_names = [n.strip().lower() for n in args.buildings.split(",")]
        buildings = [b for b in buildings if b["name"].lower() in filter_names]

    # SVG-Typen filtern
    svg_types = SVG_TYPES
    if args.svg_types:
        svg_types = [t.strip().lower() for t in args.svg_types.split(",")]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    print("=" * 70)
    print("SVG-VERGLEICH TEST (Teststrategie v2.0)")
    print(f"API: {api_url}")
    print(f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Gebaeude: {len(buildings)}")
    print(f"SVG-Typen: {', '.join(svg_types)}")
    print("=" * 70)

    results: List[BuildingTestResult] = []

    async with httpx.AsyncClient() as client:
        # 1. Cache leeren (nur fuer Testgebaeude)
        print(f"\n1. Cache leeren fuer {len(buildings)} Testgebaeude...")
        cache_result = await clear_caches_for_buildings(client, api_url, buildings)
        print(f"   -> {cache_result['buildings_cleared']} Gebaeude, {cache_result['total_deleted']} Eintraege geloescht")

        # 2. Gebaeude testen
        print(f"\n2. Teste {len(buildings)} Gebaeude...")

        for building in buildings:
            result = await test_building(client, api_url, building, svg_types)
            results.append(result)

    # 3. Report + Claude.ai Bundle erstellen
    print("\n3. Report erstellen...")
    report = create_report(results, timestamp, cache_result)
    claude_bundle = create_claude_ai_bundle(results, timestamp)

    # 4. Speichern
    output_dir = Path(__file__).parent.parent.parent / "docs" / "tests" / f"report-{timestamp}"
    save_results(results, report, claude_bundle, output_dir)

    # Zusammenfassung
    total_svgs = sum(len(r.svgs) for r in results)
    expected_svgs = len(results) * len(svg_types)

    print("\n" + "=" * 70)
    print("ZUSAMMENFASSUNG")
    print("=" * 70)
    print(f"Report-Ordner: {output_dir}")
    print(f"SVGs generiert: {total_svgs}/{expected_svgs}")
    print(f"Fehler: {sum(len(r.errors) for r in results)}")
    print()
    print("CLAUDE.AI ANALYSE:")
    print(f"  -> Lade CLAUDE_AI_ANALYSE.md zu Claude.ai hoch")
    print(f"  -> Datei enthaelt ALLE Prompts + SVGs + Anweisungen")
    print(f"  -> Dateipfad: {output_dir / 'CLAUDE_AI_ANALYSE.md'}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
