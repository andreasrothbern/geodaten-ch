# Prompt-Verbesserungsvorschläge

## Kirche St. Peter und Paul - SVG-Analyse

---

## Kritische Probleme (P0)

### Problem 1: Grundriss-Generator verwendet falsches Format

**Beobachtung:** 
Der API-generierte Grundriss hat:
- ViewBox 600×500 statt 700×480
- Interaktive CSS-Klassen
- Keine Zonen-Darstellung
- Inkompatibles Format

**Ursache:** 
Der Grundriss-Endpoint verwendet einen anderen Generator als Ansicht/Schnitt.

**Lösung (Backend):**
```python
# In svg_generator.py oder ähnlich

def generate_grundriss(building_data: dict, prompt: str) -> str:
    """Generiere Grundriss mit gleichem Format wie Ansicht/Schnitt."""
    
    # WICHTIG: Gleiche viewBox verwenden!
    svg = f'''<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
    <defs>
        {STANDARD_PATTERNS}  # Gleiche Patterns wie bei anderen SVGs
    </defs>
    ...
    '''
    
    # Zonen einzeln zeichnen, nicht nur Polygon
    for zone in building_data['zones']:
        svg += generate_zone_rect(zone)
    
    return svg
```

**Lösung (Prompt-Ergänzung):**
```markdown
## KRITISCH: Grundriss-Format

Der Grundriss MUSS folgende Anforderungen erfüllen:
- ViewBox: `0 0 700 480` (NICHT 600×500!)
- Hintergrund: #FFFFFF
- KEINE interaktiven Elemente (kein CSS, keine Hover-Effekte)
- Zonen SEPARAT zeichnen (nicht nur ein Polygon)

**Zonen im Grundriss:**
1. Westturm (links) - Quadrat, beschriftet "54.6m"
2. Kirchenschiff (zentral) - Rechteck, beschriftet "25.0m"
3. Seitenschiffe (oben/unten) - Schmalere Rechtecke, beschriftet "12.0m"
4. Chor (rechts) - Rechteck, beschriftet "18.0m"
```

---

### Problem 2: Zonen-Validierung fehlerhaft

**Beobachtung:**
```
Zone 'Kirchenschiff' (25.0m) deutlich unter API-Traufhöhe (46.4m)
```

Die API-Traufhöhe (46.4m) ist die **Turm**-Traufhöhe, nicht die des Kirchenschiffs.

**Ursache:**
Validierung vergleicht alle Zonen mit der maximalen API-Höhe.

**Lösung (Backend):**
```python
def validate_zone_heights(zones: list, api_traufe: float, api_first: float):
    """Validiere Zonen intelligent."""
    
    warnings = []
    
    # Finde höchste Zone (das ist der Turm)
    max_zone = max(zones, key=lambda z: z['firsthoehe_m'])
    
    for zone in zones:
        # Nur warnen wenn Zone > API-First (sollte nicht vorkommen)
        if zone['firsthoehe_m'] > api_first * 1.1:
            warnings.append(f"Zone '{zone['name']}' höher als API-First!")
        
        # NICHT warnen wenn Zone < API-Traufe (das ist normal bei Kirchen!)
        # Türme sind höher als Schiffe
    
    return warnings
```

**Lösung (Prompt-Ergänzung):**
```markdown
## Höhen-Hinweis für Kirchen

Bei Kirchen ist es NORMAL, dass:
- Westturm (54.6m) deutlich höher ist als andere Zonen
- Kirchenschiff (25.0m) niedriger als API-Traufhöhe
- Seitenschiffe (12.0m) am niedrigsten

Die API-Traufhöhe bezieht sich auf den HÖCHSTEN Punkt (Turm).
Die Zonen-Höhen sind KORREKT.
```

---

## Mittlere Probleme (P1)

### Problem 3: Fehlende Stil-Hinweise für SVG

**Beobachtung:**
API-SVGs zeigen keine gotischen Architekturdetails, obwohl "Neugotik" im Prompt steht.

**Ursache:**
Kein expliziter Hinweis, wie der Stil gezeichnet werden soll.

**Lösung (Prompt-Ergänzung):**
```markdown
## Stil-Hinweise für Neugotik

**Fassadenansicht:**
- Spitzbogenfenster im Turm (oben)
- Spitzbogen-Portal (Haupteingang)
- Fialen/Türmchen an Ecken (optional)
- Maßwerk in Fenstern (optional)

**Schnitt:**
- Kreuzrippengewölbe andeuten (gestrichelte Bögen)
- Hoher Innenraum im Kirchenschiff
- Spitzbogige Arkaden zwischen Haupt- und Seitenschiffen

**SVG-Umsetzung:**
```xml
<!-- Spitzbogenfenster -->
<path d="M125,60 L125,100 A12,15 0 0,0 150,100 L150,60 A12,15 0 0,0 125,60" 
      fill="#FFF" stroke="#333"/>

<!-- Gewölbe-Andeutung -->
<path d="M260,246 Q350,200 440,246" 
      fill="none" stroke="#999" stroke-dasharray="4,2"/>
```
```

---

### Problem 4: Gerüst-Parameter nicht genutzt

**Beobachtung:**
Der Prompt enthält Layher Blitz 70 Spezifikationen, aber die SVGs zeigen generische Gerüste.

**Ursache:**
Gerüst-Zeichnung ist hardcoded, nutzt nicht die Parameter.

**Lösung (Prompt-Ergänzung):**
```markdown
## Gerüst-Zeichnung (Layher Blitz 70)

**Berechnung für SVG:**
- Massstab: 1m = 7.0px
- Feldbreite 2.57m = 18px
- Lagenhöhe 2.0m = 14px
- Fassadenabstand 0.30m = 2px

**Ständer-Positionen:**
- Turm (8m breit): 4 Ständer (alle 2.57m)
- Kirchenschiff (48m breit): 19 Ständer

**Lagen:**
- Turm (54.6m): 27 Lagen
- Kirchenschiff (25m): 12 Lagen
- Chor (18m): 9 Lagen

**SVG-Code-Beispiel:**
```xml
<!-- Ständer alle 18px (2.57m) -->
<line x1="70" y1="420" x2="70" y2="40" stroke="#0066CC" stroke-width="2"/>
<line x1="88" y1="420" x2="88" y2="40" stroke="#0066CC" stroke-width="2"/>
...

<!-- Beläge alle 14px (2.0m) -->
<rect x="68" y="406" width="22" height="3" fill="#8B4513"/>
<rect x="68" y="392" width="22" height="3" fill="#8B4513"/>
...
```
```

---

## Niedrige Probleme (P2)

### Problem 5: Proportionen-Berechnung im Prompt

**Beobachtung:**
Der Prompt enthält jetzt Pixel-Berechnungen, aber sie werden nicht konsistent verwendet.

**Lösung (Prompt-Ergänzung):**
```markdown
## Proportionen-Referenz

| Element | Meter | Pixel | Berechnung |
|---------|-------|-------|------------|
| Gesamthöhe | 54.6m | 380px | Zeichenfläche |
| Turm | 54.6m | 380px | 54.6 × 7.0 |
| Kirchenschiff | 25.0m | 175px | 25.0 × 7.0 |
| Chor | 18.0m | 126px | 18.0 × 7.0 |
| Seitenschiffe | 12.0m | 84px | 12.0 × 7.0 |
| Breite | 48.2m | 337px | 48.2 × 7.0 |

**Y-Koordinaten (von unten nach oben):**
- Terrain: y=420
- +12m (Seitenschiffe): y=420-84=336
- +18m (Chor): y=420-126=294
- +25m (Kirchenschiff): y=420-175=245
- +54.6m (Turm): y=420-380=40
```

---

### Problem 6: Kirchen-spezifische Zonen-Legende

**Beobachtung:**
Die Zone-Typen Legende ist generisch (hauptgebaeude, turm, anbau).

**Lösung (Prompt-Ergänzung für Kirchen):**
```markdown
## Zone-Typen für Kirchen

| Typ | Bedeutung | SVG-Darstellung |
|-----|-----------|-----------------|
| `turm` | Kirchturm (Westturm, Vierungsturm) | Schmales Rechteck, höchste Zone |
| `hauptgebaeude` | Kirchenschiff (Mittelschiff) | Breites Rechteck, Satteldach |
| `anbau` (Seitenschiff) | Niedrigere Seitenschiffe | Schmale Rechtecke neben Hauptschiff |
| `anbau` (Chor) | Chorraum (Altarbereich) | Rechteck am Ostende |
| `apsis` | Halbrunde Apsis | Halbkreis (optional) |

**Kirchen-Schnitt-Regel:**
Im Querschnitt zeigt eine Kirche typischerweise:
```
        /\           <- Turm (Sonderkonstruktion)
       /  \
      |    |
   /\ |    | /\      <- Dach Hauptschiff
  /  \|    |/  \
 |    |    |    |    <- Hauptschiff (leer)
 | SS | HS | SS |    <- Seitenschiffe (SS), Hauptschiff (HS)
 +----+----+----+
```
```

---

## Zusammenfassung: Priorisierte Massnahmen

| Prio | Problem | Lösung | Aufwand |
|------|---------|--------|---------|
| **P0** | Grundriss falsches Format | Backend-Generator anpassen | 4 Std |
| **P0** | Zonen-Validierung falsch | Validierungs-Logik korrigieren | 1 Std |
| **P1** | Keine Stil-Hinweise | Prompt erweitern | 30 Min |
| **P1** | Gerüst-Parameter nicht genutzt | SVG-Berechnung im Prompt | 1 Std |
| **P2** | Proportionen-Referenz | Tabelle im Prompt | 15 Min |
| **P2** | Kirchen-Zonen-Legende | Spezifische Legende | 15 Min |

---

## Code-Änderungen für Claude Code

### 1. Grundriss-Generator (KRITISCH)

**Datei:** `app/services/svg_generator.py` (oder ähnlich)

```python
def generate_grundriss_svg(building: BuildingBundle) -> str:
    """
    Generiert technischen Grundriss im Standard-Format.
    
    WICHTIG: Muss gleiches Format wie ansicht/schnitt haben!
    - ViewBox: 700×480
    - Patterns: hatch, cut-hatch, ground
    - Keine interaktiven Elemente
    """
    
    svg = '''<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
  </defs>
  
  <rect width="700" height="480" fill="#FFFFFF"/>
'''
    
    # Zonen einzeln zeichnen
    for zone in building.zones:
        svg += generate_zone_shape(zone, building)
    
    # Gerüstzone
    svg += generate_geruest_zone(building)
    
    # Zugänge
    for access in building.access_points:
        svg += generate_access_point(access)
    
    # Nordpfeil, Massstab, Legende
    svg += generate_grundriss_annotations(building)
    
    svg += '</svg>'
    return svg
```

### 2. Zonen-Validierung korrigieren

**Datei:** `app/services/smart_building/validation.py`

```python
def validate_zone_heights_for_churches(
    zones: List[dict], 
    api_traufe: float, 
    api_first: float,
    building_type: str
) -> HeightValidationResult:
    """
    Spezielle Validierung für Kirchen.
    Bei Kirchen ist der Turm viel höher als das Schiff - das ist normal!
    """
    
    warnings = []
    errors = []
    
    # Finde Turm-Zone
    turm_zones = [z for z in zones if z.get('zone_type') == 'turm']
    
    if turm_zones and building_type in ['Kirche', 'Kathedrale', 'Kapelle']:
        # Bei Kirchen: Nur prüfen ob Turm-Höhe zur API passt
        turm = turm_zones[0]
        if abs(turm['firsthoehe_m'] - api_first) > 5:
            warnings.append(
                f"Turm-Höhe ({turm['firsthoehe_m']}m) weicht stark von "
                f"API-First ({api_first}m) ab"
            )
        
        # KEINE Warnung für niedrigere Zonen bei Kirchen!
        # Das Kirchenschiff ist IMMER niedriger als der Turm.
    
    else:
        # Standard-Validierung für andere Gebäude
        # ... bestehende Logik ...
    
    return HeightValidationResult(len(errors) == 0, warnings, errors)
```

---

*Verbesserungsvorschläge erstellt: 30.12.2025*
*Für: geodaten-ch Projekt*
*Basierend auf: SVG-Analyse Kirche St. Peter und Paul*
