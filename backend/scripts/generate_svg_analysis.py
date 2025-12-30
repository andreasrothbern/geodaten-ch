#!/usr/bin/env python3
"""
SVG Analysis Generator
======================

Generiert Prompts und SVGs für einzelne Adressen und erstellt
ein Analyse-Paket für Claude.ai.

Verwendung:
    python scripts/generate_svg_analysis.py "Rathausgasse 2, Bern"
    python scripts/generate_svg_analysis.py "Bundesplatz 3, 3011 Bern" --output docs/svg_analysis/bundeshaus
"""

import sys
import os
import json
import argparse
import urllib.parse
from datetime import datetime
from pathlib import Path

# Pfad für lokale Imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    import urllib.request
    print("[WARNUNG] httpx nicht installiert - verwende urllib")

# API-Konfiguration
RAILWAY_API = "https://acceptable-trust-production.up.railway.app"
LOCAL_API = "http://localhost:8000"


def fetch_data(address: str, api_base: str = RAILWAY_API) -> dict:
    """Ruft Gebäudedaten von der API ab"""
    encoded = urllib.parse.quote(address)
    url = f"{api_base}/api/v1/smart-building/data?address={encoded}&include_research=true&include_zones=true&include_terrain=true"

    if HAS_HTTPX:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    else:
        from urllib.request import urlopen
        with urlopen(url, timeout=60) as resp:
            return json.loads(resp.read().decode())


def fetch_prompt(address: str, svg_type: str = "all", api_base: str = RAILWAY_API) -> str:
    """Ruft den generierten Prompt von der API ab"""
    encoded = urllib.parse.quote(address)
    url = f"{api_base}/api/v1/smart-building/prompt?address={encoded}&svg_type={svg_type}"

    if HAS_HTTPX:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("prompt", "")
    else:
        from urllib.request import urlopen
        with urlopen(url, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data.get("prompt", "")


def fetch_svg(address: str, svg_type: str, api_base: str = RAILWAY_API) -> str:
    """Ruft ein generiertes SVG von der API ab"""
    encoded = urllib.parse.quote(address)

    # Mapping der SVG-Typen zu API-Endpunkten
    endpoints = {
        "grundriss": "floor-plan",
        "ansicht": "elevation",
        "schnitt": "cross-section",
    }

    endpoint = endpoints.get(svg_type, svg_type)
    url = f"{api_base}/api/v1/visualize/{endpoint}?address={encoded}"

    if HAS_HTTPX:
        with httpx.Client(timeout=120.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    else:
        from urllib.request import urlopen
        with urlopen(url, timeout=120) as resp:
            return resp.read().decode()


def create_claude_instructions(building_name: str, address: str) -> str:
    """Erstellt die Anweisungen für Claude.ai"""
    return f'''# SVG-Analyse Auftrag: {building_name}

> **WICHTIG: Lies diese Anleitung KOMPLETT bevor du beginnst!**

---

## PHASE 1: EIGENE SVGs GENERIEREN (ZUERST!)

**STOPP! Schau dir die API-SVGs noch NICHT an!**

Lies NUR den Prompt (prompt.md) und generiere daraus **3 vollständige SVG-Dateien**:

### 1.1 Grundriss erstellen

Erstelle `grundriss_claude.svg`:
- ViewBox: `0 0 700 480`
- Zeige: Gebäudeumriss von oben, Gerüstzone, Nordpfeil, Massstab
- Schraffur für Mauern: url(#hatch)

**Gib mir den VOLLSTÄNDIGEN SVG-Code für den Grundriss.**

### 1.2 Ansicht erstellen

Erstelle `ansicht_claude.svg`:
- ViewBox: `0 0 700 480`
- Zeige: Fassade frontal, alle Zonen, Gerüst davor, Höhenskala links
- Hintergrund: Weiss (#FFFFFF)
- Gerüst: Blau (#0066CC)

**Gib mir den VOLLSTÄNDIGEN SVG-Code für die Ansicht.**

### 1.3 Schnitt erstellen

Erstelle `schnitt_claude.svg`:
- ViewBox: `0 0 700 480`
- Zeige: Gebäude aufgeschnitten, Innenräume LEER, Schnittflächen schraffiert
- Geschossdecken als horizontale Linien

**Gib mir den VOLLSTÄNDIGEN SVG-Code für den Schnitt.**

---

## PHASE 2: VERGLEICH MIT API-SVGs

**Jetzt darfst du die API-SVGs anschauen!**

Vergleiche deine 3 SVGs mit den 3 API-SVGs und fülle diese Tabelle aus:

| Aspekt | API-SVG | Dein SVG | Besser |
|--------|---------|----------|--------|
| **GRUNDRISS** | | | |
| Gebäudeform korrekt? | ja/nein | ja/nein | API/Claude/gleich |
| Proportionen? | | | |
| Beschriftungen? | | | |
| Nordpfeil? | | | |
| **ANSICHT** | | | |
| Zonen erkennbar? | | | |
| Höhen korrekt? | | | |
| Gerüst-Position? | | | |
| Höhenskala? | | | |
| **SCHNITT** | | | |
| Innenräume leer? | | | |
| Schnittflächen schraffiert? | | | |
| Geschossdecken? | | | |

---

## PHASE 3: ANALYSE & VERBESSERUNGEN

Für JEDEN Unterschied, dokumentiere:

```
### Problem: [Name]
- Was ist falsch: [Beschreibung]
- Ursache im Prompt: [Was fehlt oder ist unklar]
- Lösung: [Konkreter Prompt-Text der hinzugefügt werden sollte]
- SVG-Beispiel: [Code-Snippet]
```

---

## PHASE 4: DATEIEN ZUM DOWNLOAD ANBIETEN

**PFLICHT: Biete JEDE Datei einzeln zum Download an!**

Folgende Dateien müssen erstellt und zum Download angeboten werden:

1. `grundriss_claude.svg` - Dein generierter Grundriss
2. `ansicht_claude.svg` - Deine generierte Ansicht
3. `schnitt_claude.svg` - Dein generierter Schnitt
4. `vergleich.md` - Deine ausgefüllte Vergleichstabelle
5. `verbesserungen.md` - Deine Prompt-Verbesserungsvorschläge
6. `zusammenfassung.md` - Kurze Zusammenfassung der Analyse

---

## Gebäude-Daten

- **Adresse:** {address}
- **Gebäude:** {building_name}
- **Datum:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## Checkliste vor Abschluss

- [ ] 3 eigene SVGs generiert (grundriss, ansicht, schnitt)
- [ ] Vergleichstabelle ausgefüllt
- [ ] Mindestens 3 Verbesserungsvorschläge dokumentiert
- [ ] Alle 6 Dateien zum Download angeboten

---

**START JETZT MIT PHASE 1!**
'''


def create_output_folder(address: str, output_path: str = None) -> Path:
    """Erstellt den Ausgabe-Ordner in docs/tests/svg_analysis/"""
    # Basis-Pfad ist immer geodaten-ch/docs/tests/svg_analysis/
    base_path = Path(__file__).parent.parent.parent / "docs" / "tests" / "svg_analysis"

    if output_path:
        folder = Path(output_path)
    else:
        # Automatischer Name aus Adresse
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_name = address.split(",")[0].strip().replace(" ", "_").lower()
        # Umlaute ersetzen
        safe_name = safe_name.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        safe_name = safe_name.replace("ß", "ss")
        folder = base_path / f"{safe_name}_{timestamp}"

    folder.mkdir(parents=True, exist_ok=True)
    return folder


def main():
    parser = argparse.ArgumentParser(
        description="Generiert SVG-Analyse-Paket für eine Adresse"
    )
    parser.add_argument("address", help="Adresse des Gebäudes (z.B. 'Rathausgasse 2, Bern')")
    parser.add_argument("--output", "-o", help="Ausgabe-Ordner (optional)")
    parser.add_argument("--local", action="store_true", help="Lokale API statt Railway verwenden")
    parser.add_argument("--svg-type", default="all", choices=["all", "grundriss", "ansicht", "schnitt"])
    parser.add_argument("--no-svg", action="store_true", help="SVGs nicht generieren (nur Prompt)")

    args = parser.parse_args()

    api_base = LOCAL_API if args.local else RAILWAY_API

    print(f"="*60)
    print(f"SVG-Analyse Generator")
    print(f"="*60)
    print(f"Adresse: {args.address}")
    print(f"API: {api_base}")
    print(f"SVG-Typ: {args.svg_type}")
    print()

    # 1. Gebäudedaten abrufen
    print("[1/4] Rufe Gebäudedaten ab...")
    try:
        data = fetch_data(args.address, api_base)
        building_name = data.get("building_name") or data.get("address_matched", args.address).split(",")[0]
        print(f"      Gebäude: {building_name}")
        print(f"      EGID: {data.get('egid', 'N/A')}")
        print(f"      Komplexität: {data.get('complexity', 'N/A')}")
        zones = data.get("zones", [])
        print(f"      Zonen: {len(zones)}")
    except Exception as e:
        print(f"      FEHLER: {e}")
        return 1

    # 2. Prompt abrufen
    print("[2/4] Rufe Prompt ab...")
    try:
        prompt = fetch_prompt(args.address, args.svg_type, api_base)
        print(f"      Prompt-Länge: {len(prompt)} Zeichen")
    except Exception as e:
        print(f"      FEHLER: {e}")
        return 1

    # 3. Ausgabe-Ordner erstellen
    print("[3/4] Erstelle Ausgabe-Ordner...")
    folder = create_output_folder(args.address, args.output)
    print(f"      Ordner: {folder}")

    # 4. SVGs generieren (optional)
    svgs = {}
    if not args.no_svg:
        print("[4/6] Generiere SVGs...")
        svg_types = ["grundriss", "ansicht", "schnitt"]
        for svg_type in svg_types:
            try:
                print(f"      Generiere {svg_type}...", end=" ", flush=True)
                svg_content = fetch_svg(args.address, svg_type, api_base)
                if svg_content and not svg_content.startswith("{"):  # Kein JSON-Error
                    svgs[svg_type] = svg_content
                    print("[OK]")
                else:
                    print("[FEHLER - JSON Response]")
            except Exception as e:
                print(f"[FEHLER: {e}]")
    else:
        print("[4/6] SVG-Generierung uebersprungen (--no-svg)")

    # 5. Dateien schreiben
    print("[5/6] Schreibe Dateien...")

    # Prompt
    with open(folder / "prompt.md", "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"      [OK] prompt.md")

    # Gebäudedaten als JSON
    with open(folder / "building_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"      [OK] building_data.json")

    # Claude.ai Anweisungen
    instructions = create_claude_instructions(building_name, args.address)
    with open(folder / "ANLEITUNG_CLAUDE_AI.md", "w", encoding="utf-8") as f:
        f.write(instructions)
    print(f"      [OK] ANLEITUNG_CLAUDE_AI.md")

    # SVGs speichern
    for svg_type, svg_content in svgs.items():
        with open(folder / f"{svg_type}_api.svg", "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"      [OK] {svg_type}_api.svg")

    # README für den Ordner
    svg_list = "\n".join([f"| `{svg_type}_api.svg` | Von Claude API generiertes SVG ({svg_type}) |" for svg_type in svgs.keys()])
    readme = f'''# SVG-Analyse: {building_name}

## Inhalt

| Datei | Beschreibung |
|-------|--------------|
| `prompt.md` | Generierter SVG-Prompt |
| `building_data.json` | Rohdaten vom SmartBuildingService |
| `ANLEITUNG_CLAUDE_AI.md` | Anleitung für Claude.ai Analyse |
{svg_list}

## Verwendung mit Claude.ai

1. Öffne Claude.ai (https://claude.ai)
2. Starte einen neuen Chat
3. Kopiere den Inhalt von `ANLEITUNG_CLAUDE_AI.md`
4. Kopiere den Inhalt von `prompt.md`
5. **Kopiere die SVG-Dateien** (grundriss_api.svg, ansicht_api.svg, schnitt_api.svg)
6. Lass Claude die SVGs analysieren und Verbesserungen vorschlagen

## Gebäude-Details

- **Adresse:** {args.address}
- **Name:** {building_name}
- **EGID:** {data.get('egid', 'N/A')}
- **Komplexität:** {data.get('complexity', 'N/A')}
- **Zonen:** {len(zones)}

## Generierte SVGs

{len(svgs)} SVGs wurden von der Claude API generiert:
- grundriss_api.svg - Draufsicht
- ansicht_api.svg - Fassadenansicht
- schnitt_api.svg - Gebäudeschnitt

Diese SVGs können an Claude.ai übergeben werden zur:
- Qualitätsanalyse
- Vergleich mit manuell erstellten SVGs
- Identifikation von Verbesserungspotential

## Generiert

- **Datum:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
- **API:** {api_base}
- **Tool:** generate_svg_analysis.py
'''
    with open(folder / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print(f"      [OK] README.md")

    # 6. Zusammenfassung
    print("[6/6] Zusammenfassung...")
    print()
    print(f"="*60)
    print(f"FERTIG!")
    print(f"="*60)
    print(f"Ordner: {folder.absolute()}")
    print()
    print("Generierte Dateien:")
    print(f"  - prompt.md")
    print(f"  - building_data.json")
    print(f"  - ANLEITUNG_CLAUDE_AI.md")
    for svg_type in svgs.keys():
        print(f"  - {svg_type}_api.svg")
    print(f"  - README.md")
    print()
    print("Naechste Schritte:")
    print("1. Oeffne Claude.ai (https://claude.ai)")
    print("2. Kopiere ANLEITUNG_CLAUDE_AI.md")
    print("3. Kopiere prompt.md")
    print("4. Lade die SVG-Dateien hoch oder kopiere den SVG-Code")
    print("5. Lass Claude die SVGs analysieren und verbessern")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
