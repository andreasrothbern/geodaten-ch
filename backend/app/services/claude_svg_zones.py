"""
Claude API SVG Generator für Zone-basierte Gebäudeschnitte.

Basiert auf dem getesteten Prompt aus test_claude_svg_generation.py.
Kann parallel zum bestehenden svg_claude_generator.py verwendet werden.
"""

import hashlib
import os
from typing import Optional

# Anthropic SDK
ANTHROPIC_AVAILABLE = False
anthropic_client = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass


def _init_client():
    """Initialisiert den Anthropic Client"""
    global anthropic_client
    if ANTHROPIC_AVAILABLE and anthropic_client is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            anthropic_client = anthropic.Anthropic(api_key=api_key)


def _call_claude(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Ruft Claude API auf und extrahiert SVG"""
    _init_client()

    if not ANTHROPIC_AVAILABLE or anthropic_client is None:
        print("Anthropic SDK not available or no API key")
        return None

    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text

        # SVG aus der Antwort extrahieren
        if '<svg' in response_text and '</svg>' in response_text:
            start = response_text.find('<svg')
            end = response_text.find('</svg>') + 6
            return response_text[start:end]

        return None

    except Exception as e:
        print(f"Claude API error: {e}")
        return None


def generate_cross_section_with_zones(
    address: str,
    egid: Optional[int],
    width_m: float,
    floors: int,
    zones: list,
    svg_width: int = 800,
    svg_height: int = 600
) -> Optional[str]:
    """
    Generiert professionellen Gebäudeschnitt mit Höhenzonen via Claude API.

    Args:
        address: Gebäudeadresse
        egid: Eidg. Gebäudeidentifikator
        width_m: Schnittbreite in Metern
        floors: Anzahl Geschosse
        zones: Liste von Zone-Dictionaries mit keys: name, type, building_height_m, first_height_m, description, special_scaffold
        svg_width: SVG-Breite in Pixel
        svg_height: SVG-Höhe in Pixel

    Returns:
        SVG-String oder None bei Fehler
    """
    import json

    # Zonen-Text aufbereiten
    zones_text = ""
    max_height = 0
    for zone in zones:
        zone_height = zone.get('building_height_m', zone.get('eave_height_m', 0))
        first_height = zone.get('first_height_m', zone_height)
        max_height = max(max_height, first_height, zone_height)
        zone_type = zone.get('type', 'standard')
        zone_name = zone.get('name', 'Zone')
        description = zone.get('description', '')
        special = zone.get('special_scaffold', False)

        zones_text += f"""
   - **{zone_name}** (Typ: {zone_type})
     - Gebäudehöhe: {zone_height:.1f}m, Firsthöhe: {first_height:.1f}m
     - {description}{"" if not special else " - **Spezialgerüst erforderlich**"}"""

    num_layers = int(max_height / 2.0) + 1

    prompt = f"""Du bist ein Experte für technische Architekturzeichnungen im SVG-Format.

## Aufgabe

Erstelle einen **Gebäudeschnitt** als SVG basierend auf den folgenden Daten.
Der Stil soll professionell, architektonisch, handgezeichnet wirkend sein.

## Gebäudedaten

- Adresse: {address}
- EGID: {egid or '-'}
- Geschosse: {floors}
- Breite (Schnitt): {width_m:.1f} m

## Höhenzonen
{zones_text}

## Wichtige Anforderungen

1. **NUR die Grafik** - Kein Titelblock, keine Fusszeile
2. **Alle {len(zones)} Zonen darstellen** mit korrekter Höhe
3. **Zone-Typen:**
   - arkade = niedrig mit Rundbögen, Säulen
   - hauptgebaeude = mit Geschossdecken, Fenster
   - kuppel = Ellipse mit Kupfer-Gradient (fill="url(#copper)"), Laterne oben
4. **Gerüst links und rechts** - Ständer (blau #0066CC), Riegel, Beläge (braun #8B4513)
5. **Verankerungen** - Rote Punkte (#CC0000) alle 4m vertikal
6. **Höhenskala links** - ±0.00 bis +{max_height:.0f}m
7. **Lagenbeschriftung** - 1. Lage bis {num_layers}. Lage

## SVG-Patterns (verwenden!)

```xml
<defs>
    <pattern id="hatch-cut" patternUnits="userSpaceOnUse" width="6" height="6">
      <path d="M0,0 l6,6 M-1,5 l3,3 M5,-1 l3,3" stroke="#333" stroke-width="0.8"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="15">
      <path d="M0,15 L10,0 M10,15 L20,0" stroke="#666" stroke-width="0.5"/>
      <circle cx="5" cy="10" r="1.5" fill="#888"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
</defs>
```

## Farben
- Gerüst: #0066CC (blau)
- Anker: #CC0000 (rot)
- Belag: #8B4513 (braun)
- Gebäude-Schnitt: fill="url(#hatch-cut)"
- Kuppel: fill="url(#copper)"
- Fenster: #87CEEB

## Output

Generiere ein vollständiges, valides SVG mit viewBox="0 0 {svg_width} {svg_height}".
Gib NUR das SVG aus, keine Erklärungen.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}">
"""

    svg = _call_claude(prompt)
    return svg


def generate_elevation_with_zones(
    address: str,
    egid: Optional[int],
    width_m: float,
    floors: int,
    zones: list,
    svg_width: int = 800,
    svg_height: int = 600
) -> Optional[str]:
    """
    Generiert professionelle Fassadenansicht mit Höhenzonen via Claude API.

    Args:
        address: Gebäudeadresse
        egid: Eidg. Gebäudeidentifikator
        width_m: Fassadenbreite in Metern
        floors: Anzahl Geschosse
        zones: Liste von Zone-Dictionaries
        svg_width: SVG-Breite in Pixel
        svg_height: SVG-Höhe in Pixel

    Returns:
        SVG-String oder None bei Fehler
    """
    # Zonen-Text aufbereiten
    zones_text = ""
    max_height = 0
    for zone in zones:
        zone_height = zone.get('building_height_m', zone.get('eave_height_m', 0))
        first_height = zone.get('first_height_m', zone_height)
        max_height = max(max_height, first_height, zone_height)
        zone_type = zone.get('type', 'standard')
        zone_name = zone.get('name', 'Zone')
        description = zone.get('description', '')
        special = zone.get('special_scaffold', False)

        zones_text += f"""
   - **{zone_name}** (Typ: {zone_type})
     - Gebäudehöhe: {zone_height:.1f}m, Firsthöhe: {first_height:.1f}m
     - {description}{"" if not special else " - **Spezialgerüst erforderlich**"}"""

    num_layers = int(max_height / 2.0) + 1

    prompt = f"""Du bist ein Experte für technische Architekturzeichnungen im SVG-Format.

## Aufgabe

Erstelle eine **Fassadenansicht** (Elevation) als SVG basierend auf den folgenden Daten.
Der Stil soll professionell, architektonisch, handgezeichnet wirkend sein.

## Gebäudedaten

- Adresse: {address}
- EGID: {egid or '-'}
- Geschosse: {floors}
- Fassadenbreite: {width_m:.1f} m

## Höhenzonen
{zones_text}

## Wichtige Anforderungen

1. **NUR die Grafik** - Kein Titelblock, keine Fusszeile
2. **Frontalansicht** der Fassade (nicht Schnitt!)
3. **Alle {len(zones)} Zonen darstellen** mit korrekter Höhe
4. **Zone-Typen visuell:**
   - arkade = Rundbogen-Arkaden mit Säulen, Sandstein-Farbe
   - hauptgebaeude = Fensterreihen pro Geschoss, Fassadendetails
   - kuppel = Kuppelform mit Kupfer-Gradient, Laterne oben, Tambour mit Fenstern
5. **Gerüst VOR der Fassade** - Ständer (blau #0066CC), Riegel, Beläge (braun #8B4513)
6. **Verankerungen** - Rote Punkte (#CC0000) alle 4m vertikal, alle 4m horizontal
7. **Höhenskala links** - ±0.00 bis +{max_height:.0f}m
8. **Lagenbeschriftung rechts** - 1. Lage bis {num_layers}. Lage

## SVG-Patterns (verwenden!)

```xml
<defs>
    <pattern id="sandstone" patternUnits="userSpaceOnUse" width="20" height="10">
      <rect width="20" height="10" fill="#E8DCC8"/>
      <path d="M0,5 h20 M10,0 v10" stroke="#D4C4A8" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
    <linearGradient id="sky" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#87CEEB"/>
      <stop offset="100%" style="stop-color:#E0F0FF"/>
    </linearGradient>
</defs>
```

## Farben
- Hintergrund: url(#sky) oder #F5F5F5
- Fassade: #E8DCC8 (Sandstein) oder url(#sandstone)
- Fenster: #4A5568 mit hellem Rahmen
- Kuppel: url(#copper)
- Gerüst: #0066CC (blau)
- Anker: #CC0000 (rot)
- Belag: #8B4513 (braun)

## Output

Generiere ein vollständiges, valides SVG mit viewBox="0 0 {svg_width} {svg_height}".
Gib NUR das SVG aus, keine Erklärungen.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}">
"""

    svg = _call_claude(prompt)
    return svg


def is_available() -> bool:
    """Prüft ob Claude API verfügbar ist"""
    _init_client()
    return ANTHROPIC_AVAILABLE and anthropic_client is not None
