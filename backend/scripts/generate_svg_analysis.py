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
    return f'''# Claude.ai SVG-Analyse: {building_name}

## Auftrag

Du erhältst:
1. Einen **technischen Prompt** für die SVG-Generierung
2. **3 API-generierte SVGs** (grundriss_api.svg, ansicht_api.svg, schnitt_api.svg)

Deine Aufgabe ist es:

1. **Eigene SVGs generieren** - Erstelle 3 SVGs basierend auf dem Prompt
2. **Vergleichen** - Vergleiche deine SVGs mit den API-generierten
3. **Analysieren** - Identifiziere Unterschiede und Probleme
4. **Verbessern** - Schlage konkrete Prompt-Verbesserungen vor
5. **Download bereitstellen** - Stelle alle Dateien zum Download bereit

---

## Gebäude-Information

- **Adresse:** {address}
- **Zeitstempel:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## Schritt 1: Eigene SVGs generieren

Lies den Prompt in `prompt.md` und erstelle **3 separate SVG-Dateien**:

1. `grundriss_claude.svg` - Draufsicht mit Gebäudeumriss und Gerüstzone
2. `ansicht_claude.svg` - Fassadenansicht (Elevation) mit Gerüst
3. `schnitt_claude.svg` - Gebäudeschnitt mit Innenräumen

**Wichtige Vorgaben:**
- ViewBox: `0 0 700 480`
- Hintergrund: Weiss (#FFFFFF)
- Gebäude: Schraffur-Pattern url(#hatch)
- Gerüst: Blau (#0066CC)
- Keine künstlerische Interpretation!

---

## Schritt 2: Vergleich mit API-SVGs

Vergleiche deine generierten SVGs mit den API-generierten SVGs:

### Vergleichs-Tabelle

| Aspekt | API-SVG | Dein SVG | Bewertung |
|--------|---------|----------|-----------|
| **Grundriss** | | | |
| Gebäudeform | ___ | ___ | besser/gleich/schlechter |
| Proportionen | ___ | ___ | |
| Beschriftungen | ___ | ___ | |
| Gerüst-Zone | ___ | ___ | |
| **Ansicht** | | | |
| Zonen-Darstellung | ___ | ___ | |
| Höhen korrekt | ___ | ___ | |
| Gerüst-Position | ___ | ___ | |
| **Schnitt** | | | |
| Innenräume | ___ | ___ | |
| Schnittflächen | ___ | ___ | |

### Unterschiede dokumentieren

Für jeden signifikanten Unterschied:

```markdown
### Unterschied: [Beschreibung]

**API-SVG:** [Was die API generiert hat]
**Dein SVG:** [Was du generiert hast]
**Besser:** API / Claude.ai / Beide gleich
**Grund:** [Warum einer besser ist]
```

---

## Schritt 3: Selbst-Analyse

### Checkliste Grundriss
- [ ] Gebäudeform korrekt (rechteckig/U-Form/L-Form)?
- [ ] Innenhöfe als Freifläche markiert?
- [ ] Fassaden beschriftet?
- [ ] Nordpfeil vorhanden?
- [ ] Massstab korrekt?

### Checkliste Ansicht
- [ ] Proportionen stimmen (Höhe/Breite)?
- [ ] Zonen erkennbar (unterschiedliche Höhen)?
- [ ] Gerüst VOR der Fassade?
- [ ] Höhenskala links?
- [ ] Terrain-Linie unten?

### Checkliste Schnitt
- [ ] Schnittflächen dicht schraffiert?
- [ ] Innenräume LEER (weiss)?
- [ ] Geschossdecken horizontal?
- [ ] Gerüst links und rechts?

---

## Schritt 4: Prompt-Verbesserungen

Basierend auf dem Vergleich, schlage konkrete Verbesserungen vor:

### Format für Verbesserungen

```markdown
### Problem: [Kurze Beschreibung]

**Beobachtung:** Was ist falsch oder fehlt in beiden SVGs?

**Ursache:** Was fehlt im Prompt?

**Lösung (Prompt-Änderung):**
```
[Vorgeschlagener neuer Prompt-Abschnitt]
```

**Beispiel-Code (SVG):**
```xml
[Korrigierter SVG-Code-Ausschnitt]
```
```

---

## Schritt 5: Download-Paket

Erstelle ein ZIP-Archiv mit folgenden Dateien:

```
{building_name.lower().replace(" ", "_")}_svg_analyse/
├── grundriss_claude.svg      # Dein generierter Grundriss
├── ansicht_claude.svg        # Deine generierte Ansicht
├── schnitt_claude.svg        # Dein generierter Schnitt
├── grundriss_api.svg         # API-generierter Grundriss (Kopie)
├── ansicht_api.svg           # API-generierte Ansicht (Kopie)
├── schnitt_api.svg           # API-generierter Schnitt (Kopie)
├── vergleich.md              # Deine Vergleichs-Analyse
├── verbesserungen.md         # Prompt-Verbesserungsvorschläge
└── prompt_original.md        # Der ursprüngliche Prompt
```

---

## Bewertungskriterien

| Kriterium | Gewichtung |
|-----------|------------|
| Technische Korrektheit | 30% |
| Vergleichs-Qualität | 25% |
| Prompt-Verbesserungen | 25% |
| Vollständigkeit | 20% |

---

## Hinweise

1. **Generiere ZUERST deine eigenen SVGs** bevor du die API-SVGs anschaust
2. **Dokumentiere alle Unterschiede** - auch kleine Details
3. **Sei kritisch** - auch gegenüber deinen eigenen SVGs
4. **Konkrete Lösungen** - Jede Kritik braucht einen Verbesserungsvorschlag

---

*Generiert mit Gerüstplanung Schweiz App*
*https://cooperative-commitment-production.up.railway.app*
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
