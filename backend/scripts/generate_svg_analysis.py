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


def create_claude_instructions(building_name: str, address: str) -> str:
    """Erstellt die Anweisungen für Claude.ai"""
    return f'''# Claude.ai SVG-Analyse: {building_name}

## Auftrag

Du erhältst einen **technischen Prompt** für die SVG-Generierung eines Schweizer Gebäudes.
Deine Aufgabe ist es:

1. **SVGs generieren** - Erstelle 3 SVGs (Grundriss, Ansicht, Schnitt) basierend auf dem Prompt
2. **Analyse durchführen** - Bewerte die Qualität der generierten SVGs
3. **Verbesserungen vorschlagen** - Identifiziere Probleme und schlage Lösungen vor
4. **Download bereitstellen** - Stelle alle Dateien zum Download bereit

---

## Gebäude-Information

- **Adresse:** {address}
- **Zeitstempel:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## Schritt 1: SVG-Generierung

Lies den Prompt in `prompt.md` und erstelle **3 separate SVG-Dateien**:

1. `grundriss.svg` - Draufsicht mit Gebäudeumriss und Gerüstzone
2. `ansicht.svg` - Fassadenansicht (Elevation) mit Gerüst
3. `schnitt.svg` - Gebäudeschnitt mit Innenräumen

**Wichtige Vorgaben:**
- ViewBox: `0 0 700 480`
- Hintergrund: Weiss (#FFFFFF)
- Gebäude: Schraffur-Pattern
- Gerüst: Blau (#0066CC)
- Keine künstlerische Interpretation!

---

## Schritt 2: Selbst-Analyse

Nach der SVG-Generierung, analysiere deine eigenen Ergebnisse:

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

## Schritt 3: Prompt-Verbesserungen

Basierend auf deiner Analyse, schlage konkrete Verbesserungen für den Prompt vor:

### Format für Verbesserungen

```markdown
### Problem: [Kurze Beschreibung]

**Beobachtung:** Was ist falsch oder fehlt?

**Ursache:** Warum ist das passiert?

**Lösung (Prompt-Änderung):**
```
[Vorgeschlagener neuer Prompt-Abschnitt]
```

**Beispiel-Code (SVG):**
```xml
[Korrigierter SVG-Code]
```
```

---

## Schritt 4: Download-Paket

Erstelle ein ZIP-Archiv mit folgenden Dateien:

```
{building_name.lower().replace(" ", "_")}_svg_analyse/
├── grundriss.svg          # Generierter Grundriss
├── ansicht.svg            # Generierte Ansicht
├── schnitt.svg            # Generierter Schnitt
├── analyse.md             # Deine Analyse mit Checklisten
├── verbesserungen.md      # Prompt-Verbesserungsvorschläge
└── prompt_original.md     # Der ursprüngliche Prompt
```

---

## Bewertungskriterien

| Kriterium | Gewichtung |
|-----------|------------|
| Technische Korrektheit | 40% |
| Proportionen & Massstab | 25% |
| Style-Konformität | 20% |
| Vollständigkeit | 15% |

---

## Hinweise

1. **Keine Kreativität!** Halte dich strikt an den Prompt
2. **Frage bei Unklarheiten** statt zu raten
3. **Dokumentiere Annahmen** die du triffst
4. **Verwende die exakten Farben** aus dem Style-Guide

---

*Generiert mit Gerüstplanung Schweiz App*
*https://cooperative-commitment-production.up.railway.app*
'''


def create_output_folder(address: str, output_path: str = None) -> Path:
    """Erstellt den Ausgabe-Ordner"""
    if output_path:
        folder = Path(output_path)
    else:
        # Automatischer Name aus Adresse
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_name = address.split(",")[0].strip().replace(" ", "_").lower()
        folder = Path(f"docs/svg_analysis/{safe_name}_{timestamp}")

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

    # 4. Dateien schreiben
    print("[4/4] Schreibe Dateien...")

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

    # README für den Ordner
    readme = f'''# SVG-Analyse: {building_name}

## Inhalt

| Datei | Beschreibung |
|-------|--------------|
| `prompt.md` | Generierter SVG-Prompt |
| `building_data.json` | Rohdaten vom SmartBuildingService |
| `ANLEITUNG_CLAUDE_AI.md` | Anleitung für Claude.ai Analyse |

## Verwendung

1. Öffne Claude.ai (https://claude.ai)
2. Starte einen neuen Chat
3. Kopiere den Inhalt von `ANLEITUNG_CLAUDE_AI.md`
4. Kopiere den Inhalt von `prompt.md`
5. Lass Claude die SVGs generieren und analysieren

## Gebäude-Details

- **Adresse:** {args.address}
- **Name:** {building_name}
- **EGID:** {data.get('egid', 'N/A')}
- **Komplexität:** {data.get('complexity', 'N/A')}
- **Zonen:** {len(zones)}

## Generiert

- **Datum:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
- **API:** {api_base}
- **Tool:** generate_svg_analysis.py
'''
    with open(folder / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print(f"      [OK] README.md")

    print()
    print(f"="*60)
    print(f"FERTIG!")
    print(f"="*60)
    print(f"Ordner: {folder.absolute()}")
    print()
    print("Nächste Schritte:")
    print("1. Öffne Claude.ai")
    print("2. Kopiere ANLEITUNG_CLAUDE_AI.md")
    print("3. Kopiere prompt.md")
    print("4. Lass Claude die SVGs generieren")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
