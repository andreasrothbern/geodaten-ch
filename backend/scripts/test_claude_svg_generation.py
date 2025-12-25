"""
Test: Claude API für direkte SVG-Generierung

Testet ob Claude API mit strukturierten Daten + Referenz-SVG
professionelle Grafiken generieren kann.

Ausführen:
  cd backend
  python scripts/test_claude_svg_generation.py
"""

import anthropic
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Lade .env Datei
load_dotenv(Path(__file__).parent.parent / ".env")

# Bundeshaus-Daten (aus unserer App)
BUNDESHAUS_DATA = {
    "gebaeude": {
        "adresse": "Bundesplatz 3, 3011 Bern",
        "egid": 1017961,
        "gkat": 1040,
        "gkat_text": "Gebäude mit Nebennutzung",
        "garea": 4850,
        "gastw": 4,
        "gbauj": 1902
    },
    "hoehen": {
        "traufhoehe_m": 14.53,
        "firsthoehe_m": 62.57,
        "geschosse": 4,
        "quelle": "swissBUILDINGS3D"
    },
    "zonen": [
        {
            "id": "zone_arkade",
            "name": "Arkaden/Erdgeschoss",
            "typ": "arkade",
            "gebaeudehoehe_m": 14.5,
            "traufhoehe_m": 14.5,
            "beschreibung": "Niedrige Arkaden mit Rundbögen, Sandstein"
        },
        {
            "id": "zone_parlament",
            "name": "Hauptgebäude",
            "typ": "hauptgebaeude",
            "gebaeudehoehe_m": 28.0,
            "traufhoehe_m": 25.0,
            "firsthoehe_m": 32.0,
            "beschreibung": "Neorenaissance Parlamentsgebäude, 4 Geschosse"
        },
        {
            "id": "zone_kuppel",
            "name": "Kuppel/Turm",
            "typ": "kuppel",
            "gebaeudehoehe_m": 30.0,
            "firsthoehe_m": 64.0,
            "spezialgeruest": True,
            "beschreibung": "Kupferkuppel mit Laterne, Tambour mit Fenstern"
        }
    ],
    "geruest": {
        "system": "Layher Blitz 70",
        "breitenklasse": "W09",
        "fassadenabstand_m": 0.30,
        "lagen_hoehe_m": 2.0,
        "verankerung_h_m": 4.0,
        "verankerung_v_m": 4.0
    },
    "breite_schnitt_m": 60.0  # Nord-Süd
}


def load_reference_svg():
    """Lädt das Referenz-SVG"""
    ref_path = Path(__file__).parent.parent.parent / "docs" / "claude_ai_bundeshaus" / "anhang_c_schnitt.svg"
    if not ref_path.exists():
        ref_path = Path("C:/Users/vonro/projects/lawil/claude_ai_bundeshaus/anhang_c_schnitt.svg")

    if ref_path.exists():
        return ref_path.read_text(encoding="utf-8")
    return None


def create_prompt(data: dict, reference_svg: str) -> str:
    """Erstellt den Prompt für Claude"""

    return f"""Du bist ein Experte für technische Architekturzeichnungen im SVG-Format.

## Aufgabe

Erstelle einen **Gebäudeschnitt** als SVG basierend auf den folgenden Daten.
Der Stil soll wie die Referenz sein: professionell, architektonisch, handgezeichnet wirkend.

## Gebäudedaten

```json
{json.dumps(data, indent=2, ensure_ascii=False)}
```

## Wichtige Anforderungen

1. **NUR die Grafik** - Kein Titelblock, keine Fusszeile
2. **Massstab beachten** - Proportionen aus den Daten
3. **3 Zonen darstellen:**
   - Arkaden (14.5m) - niedrig, mit Bögen
   - Hauptgebäude (25-32m) - mit Geschossdecken
   - Kuppel (bis 64m) - mit Tambour, Kupferkuppel, Laterne
4. **Gerüst links und rechts** - Ständer, Riegel, Beläge
5. **Verankerungen** - Rote Punkte/Linien
6. **Höhenskala links** - ±0.00 bis +64m
7. **Lagenbeschriftung** - 1. Lage, 2. Lage, etc.
8. **Hinweis Kuppelgerüst** - "Spezialgerüst erforderlich"

## Referenz-SVG (Stil-Vorlage)

Hier ist ein Beispiel für den gewünschten Stil. Übernimm:
- Die Patterns (hatch, ground, copper)
- Die Farben (Gerüst blau #0066CC, Anker rot #CC0000, Belag braun #8B4513)
- Die Liniendicken und Schriftarten
- Die Art wie Geschossdecken, Kuppel, Gerüst gezeichnet sind

```svg
{reference_svg[:8000]}
```
(... gekürzt für Kontext ...)

## Output

Generiere ein vollständiges, valides SVG mit viewBox="0 0 800 600".
Gib NUR das SVG aus, keine Erklärungen.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
"""


def test_claude_svg_generation():
    """Haupttest"""
    print("=" * 60)
    print("TEST: Claude API SVG-Generierung")
    print("=" * 60)

    # Referenz laden
    print("\n1. Lade Referenz-SVG...")
    reference_svg = load_reference_svg()
    if not reference_svg:
        print("   FEHLER: Referenz-SVG nicht gefunden!")
        return
    print(f"   OK - {len(reference_svg)} Zeichen")

    # Prompt erstellen
    print("\n2. Erstelle Prompt...")
    prompt = create_prompt(BUNDESHAUS_DATA, reference_svg)
    print(f"   OK - {len(prompt)} Zeichen")

    # Claude API aufrufen
    print("\n3. Rufe Claude API auf...")
    print("   (Dies kann 10-30 Sekunden dauern)")

    try:
        client = anthropic.Anthropic()

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text
        print(f"   OK - {len(response_text)} Zeichen Antwort")

        # SVG extrahieren
        print("\n4. Extrahiere SVG...")
        svg_content = response_text

        # Falls in Code-Block
        if "```svg" in svg_content:
            start = svg_content.find("```svg") + 6
            end = svg_content.find("```", start)
            svg_content = svg_content[start:end].strip()
        elif "```xml" in svg_content:
            start = svg_content.find("```xml") + 6
            end = svg_content.find("```", start)
            svg_content = svg_content[start:end].strip()
        elif "```" in svg_content:
            start = svg_content.find("```") + 3
            end = svg_content.find("```", start)
            svg_content = svg_content[start:end].strip()

        # Sicherstellen dass es mit <svg beginnt
        if not svg_content.strip().startswith("<svg"):
            svg_start = svg_content.find("<svg")
            if svg_start >= 0:
                svg_content = svg_content[svg_start:]

        # SVG speichern
        output_path = Path(__file__).parent / "test_output_schnitt.svg"
        output_path.write_text(svg_content, encoding="utf-8")
        print(f"   OK - Gespeichert: {output_path}")

        # Statistiken
        print("\n5. Ergebnis:")
        print(f"   - SVG Grösse: {len(svg_content)} Zeichen")
        print(f"   - Input Tokens: {message.usage.input_tokens}")
        print(f"   - Output Tokens: {message.usage.output_tokens}")

        # Kosten schätzen (Sonnet 4 Preise)
        input_cost = message.usage.input_tokens * 0.003 / 1000
        output_cost = message.usage.output_tokens * 0.015 / 1000
        total_cost = input_cost + output_cost
        print(f"   - Geschätzte Kosten: ${total_cost:.4f}")

        print("\n" + "=" * 60)
        print(f"SVG gespeichert in: {output_path}")
        print("Öffnen Sie die Datei im Browser um das Ergebnis zu sehen.")
        print("=" * 60)

    except anthropic.APIError as e:
        print(f"   FEHLER: {e}")
    except Exception as e:
        print(f"   FEHLER: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_claude_svg_generation()
