# SVG-Generierung: Fassadenansicht WEST - Kirche St. Peter und Paul

Erstelle eine technische Architekturzeichnung der **WESTFASSADE** für die Gerüstplanung.
Folge den unten aufgeführten Daten und Style-Vorgaben EXAKT.

## 1. Gebäude-Identifikation
- **Adresse:** Rathausgasse 2, 3011 Bern
- **EGID:** 191821074
- **Koordinaten (LV95):** E 601009, N 199736
- **Gebäudename:** Kirche St. Peter und Paul
- **Gebäudetyp:** Christkatholische Kathedralkirche
- **Baustil:** Neugotik
- **Baujahr:** 1864
- **Komplexität:** COMPLEX

## 2. ANSICHT-SPEZIFIKATION (NEU!)

### Gewählte Ansicht: WEST (W)
- **Blickrichtung:** Betrachter steht im WESTEN, schaut nach OSTEN
- **Hauptelemente sichtbar:**
  - Westturm (frontal, zentral, dominant)
  - Hauptportal (unter dem Turm)
  - Strebebögen (links und rechts des Turms)
  - Teile der Seitenschiffe (seitlich)

### Foto-Referenz
> Basierend auf Vor-Ort-Foto vom 30.12.2025
> - Turm ist ZENTRAL und FRONTAL sichtbar
> - Portal mit Spitzbogen erkennbar
> - Strebebögen verbinden Turm mit Seitenschiffen

### Verdeckungslogik (KRITISCH!)
```
Von West gesehen:

        ┌─────┐
        │TURM │  ← Im Vordergrund (VERDECKT alles dahinter)
        │     │
        │     │
   ╱────┴─────┴────╲  ← Strebebögen (seitlich sichtbar)
  ╱                 ╲
 │  Seitenschiff    │  ← Teilweise sichtbar (hinter Strebebögen)
 │                  │
 └──────────────────┘
        ↑
    Hauptportal
```

**Was ist SICHTBAR:**
1. Westturm (komplett, 54.6m)
2. Hauptportal (unter Turm)
3. Strebebögen (links/rechts)
4. Seitenschiffe (teilweise, niedrigere Bereiche)

**Was ist NICHT sichtbar (verdeckt):**
1. Kirchenschiff (hinter Turm)
2. Chor (ganz hinten)
3. Ostfassade

## 3. Geometrische Basisdaten
### Dimensionen WESTFASSADE
- **Gesamtbreite:** ca. 25m (Turm 8m + Strebebögen + Seitenschiffe)
- **Gesamthöhe:** 54.6m (Turmspitze)
- **Turm-Breite:** 8.0m
- **Turm-Höhe:** 54.6m
- **Seitenschiffe sichtbar:** ca. 8m Höhe, 8m Breite pro Seite

### Proportionen für viewBox 700×480
- **Massstab:** 1m = 7.0px (ca. 1:143)
- **Zeichenfläche:** 550px × 380px
- **Gebäudehöhe:** 54.6m = 380px
- **Turm-Breite:** 8m = 56px
- **Seitenschiffe:** je 8m = 56px

## 4. Terrain (swissALTI3D)
- **Terrain-Höhe:** 533.5 m ü.M.
- **Referenzpunkt:** Haupteingang = ±0.00 = 533.5 m ü.M.
- **Hanglage:** Nein (eben)

## 5. Höhenzonen (für WEST-Ansicht relevant)

| Zone | Sichtbarkeit | Höhe | In SVG |
|------|--------------|------|--------|
| Westturm | ✅ VOLL | 54.6m | Zentral, dominant |
| Hauptportal | ✅ VOLL | 12m | Unter Turm |
| Strebebögen | ✅ VOLL | 15-25m | Links/rechts vom Turm |
| Seitenschiffe | ⚠️ TEIL | 12m | Seitlich, niedrig |
| Kirchenschiff | ❌ VERDECKT | 25m | Nicht zeichnen! |
| Chor | ❌ VERDECKT | 18m | Nicht zeichnen! |

## 6. Architektonische Details (Neugotik)

### Turm-Elemente (von unten nach oben)
1. **Hauptportal** (0-12m)
   - Grosser Spitzbogen-Eingang
   - Doppelflügeltür
   - Tympanon mit Relief

2. **Fensterzone 1** (12-25m)
   - 2×2 Spitzbogenfenster
   - Maßwerk

3. **Glockengeschoss** (25-40m)
   - Grosse Schallfenster (Spitzbögen)
   - Fialen an Ecken

4. **Turmhelm** (40-54.6m)
   - Achteckiger Spitzhelm
   - Kreuz an der Spitze

### Strebebögen
- Verbinden Turm mit Seitenschiffen
- Ca. 15m Ansatzhöhe am Turm
- Fallen auf ca. 8m bei Seitenschiffen ab

## 7. SVG Style-Vorgaben

```xml
<defs>
  <!-- LOCKERE Schraffur für Aussenflächen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | SVG-Hintergrund |
| Gebäude-Fassade | url(#hatch) | Alle sichtbaren Flächen |
| Fenster | #FFFFFF | Weiss mit Rahmen |
| Terrain | url(#ground) | Boden unter Gebäude |
| Gerüst-Ständer | #0066CC (blau) | Vertikale Stützen |
| Beläge | #8B4513 (braun) | Horizontale Arbeitsflächen |
| Verankerungen | #CC0000 gestrichelt | Verbindung zur Fassade |

## 8. Gerüst-Spezifikation (Layher Blitz 70)

### Turm-Gerüst (Sonderkonstruktion)
- **Höhe:** 56m (28 Lagen à 2.0m)
- **Breite:** 12m (5 Felder à 2.57m, umschliessend)
- **Breitenklasse:** W09 (0.73m)
- **Verankerungen:** Alle 4m horizontal/vertikal

### Seitenschiff-Gerüst (Standard)
- **Höhe:** 14m (7 Lagen)
- **Breite:** Je 10m (4 Felder)

## 9. Anforderungen SVG: Fassadenansicht WEST

### Perspektive
- **Blick:** Frontal von WESTEN nach OSTEN
- **Projektion:** Orthogonal (2D, keine Perspektive)
- **Verdeckung:** Vordere Elemente verdecken hintere

### Aufbau (Zeichenreihenfolge)
1. **ZUERST (hinten):** Seitenschiffe (niedrig, seitlich)
2. **DANN:** Strebebögen
3. **ZULETZT (vorne):** Westturm (verdeckt alles dahinter)

### Elemente im SVG
1. **Terrain-Linie** bei ±0.00
2. **Seitenschiffe** (links und rechts, 12m hoch)
3. **Strebebögen** (diagonale Linien)
4. **Westturm** (zentral, 54.6m hoch)
   - Spitzbogen-Portal
   - Fensterreihen
   - Schallfenster
   - Turmhelm mit Kreuz
5. **Gerüst** vor der Fassade
   - Ständer (blau)
   - Beläge (braun)
   - Verankerungen (rot gestrichelt)
6. **Höhenskala** links
7. **Lagenbeschriftung** rechts

### Layout (viewBox 700×480)
```
┌─────────────────────────────────────────────────────────────┐
│ TITEL: Fassadenansicht West - Kirche St. Peter und Paul     │ y=20
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Höhen-  │                                    │ Lagen-      │
│  skala   │         [TURM MIT GERÜST]          │ beschrift.  │
│          │                                    │             │
│  +54.6m ─┤              /\                    │─ 28. Lage   │
│          │             /  \                   │             │
│          │            │    │                  │             │
│  +40m   ─┤            │ 🔔 │                  │─ 20. Lage   │
│          │            │    │                  │             │
│          │            │ ⬜ │                  │             │
│  +25m   ─┤     ╱──────┴────┴──────╲           │─ 12. Lage   │
│          │    ╱                    ╲          │             │
│  +12m   ─┤   │   Seitenschiff      │         │─ 6. Lage    │
│          │   │                      │         │             │
│  ±0.00  ─┼───┴──────────────────────┴─────────┼─ Terrain    │
│          │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │             │
│          │  ~~~~~~~~~ TERRAIN ~~~~~~~~~~~~    │             │
│                                                             │
│  x=50    x=100                  x=350                  x=600│
└─────────────────────────────────────────────────────────────┘
```

## 10. Checkliste für WEST-Ansicht

### Muss enthalten:
- [x] Westturm zentral und dominant (54.6m)
- [x] Hauptportal mit Spitzbogen
- [x] Schallfenster im Glockengeschoss
- [x] Turmhelm mit Kreuz
- [x] Strebebögen links/rechts
- [x] Seitenschiffe seitlich (12m)
- [x] Terrain-Linie
- [x] Höhenskala links
- [x] Gerüst vor der Fassade

### Darf NICHT enthalten:
- [ ] Kirchenschiff (verdeckt!)
- [ ] Chor (verdeckt!)
- [ ] Ostfassade
- [ ] Rosettenfenster (ist auf Südseite)

## 11. Beispiel SVG-Struktur

```xml
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" .../>
    <pattern id="ground" .../>
  </defs>
  
  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Titel -->
  <text x="350" y="22" text-anchor="middle" font-weight="bold">
    FASSADENANSICHT WEST - Kirche St. Peter und Paul
  </text>
  <text x="350" y="38" text-anchor="middle" fill="#666">
    Blickrichtung: Von West nach Ost | Massstab 1:143
  </text>
  
  <!-- Terrain -->
  <rect x="60" y="420" width="580" height="40" fill="url(#ground)"/>
  <line x1="60" y1="420" x2="640" y2="420" stroke="#333" stroke-width="2"/>
  
  <!-- ZEICHENREIHENFOLGE: Hinten nach vorne -->
  
  <!-- 1. Seitenschiffe (hinten, seitlich) -->
  <g id="seitenschiffe">
    <!-- Linkes Seitenschiff -->
    <rect x="120" y="336" width="80" height="84" fill="url(#hatch)" stroke="#333"/>
    <!-- Rechtes Seitenschiff -->
    <rect x="500" y="336" width="80" height="84" fill="url(#hatch)" stroke="#333"/>
  </g>
  
  <!-- 2. Strebebögen -->
  <g id="strebeboegen">
    <path d="M200,300 Q250,280 280,340" fill="none" stroke="#333" stroke-width="2"/>
    <path d="M500,300 Q450,280 420,340" fill="none" stroke="#333" stroke-width="2"/>
  </g>
  
  <!-- 3. Westturm (vorne, zentral) - VERDECKT alles dahinter -->
  <g id="westturm">
    <!-- Turm-Körper -->
    <rect x="280" y="40" width="140" height="380" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
    
    <!-- Turmhelm -->
    <polygon points="280,40 350,10 420,40" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
    <line x1="350" y1="10" x2="350" y2="0" stroke="#333" stroke-width="2"/>
    <line x1="345" y1="5" x2="355" y2="5" stroke="#333" stroke-width="2"/>
    
    <!-- Schallfenster (Spitzbögen) -->
    <path d="M300,80 L300,130 A25,30 0 0,0 350,130 L350,80 A25,30 0 0,0 300,80" 
          fill="#FFF" stroke="#333"/>
    <path d="M350,80 L350,130 A25,30 0 0,0 400,130 L400,80 A25,30 0 0,0 350,80" 
          fill="#FFF" stroke="#333"/>
    
    <!-- Fensterreihen -->
    <rect x="310" y="160" width="30" height="50" fill="#FFF" stroke="#333"/>
    <rect x="360" y="160" width="30" height="50" fill="#FFF" stroke="#333"/>
    <rect x="310" y="230" width="30" height="50" fill="#FFF" stroke="#333"/>
    <rect x="360" y="230" width="30" height="50" fill="#FFF" stroke="#333"/>
    
    <!-- Hauptportal (Spitzbogen) -->
    <path d="M310,350 L310,420 L390,420 L390,350 A40,50 0 0,0 310,350" 
          fill="#FFF" stroke="#333" stroke-width="1.5"/>
  </g>
  
  <!-- 4. Gerüst (ganz vorne) -->
  <g id="geruest">
    <!-- Ständer -->
    <line x1="260" y1="420" x2="260" y2="20" stroke="#0066CC" stroke-width="2"/>
    <line x1="440" y1="420" x2="440" y2="20" stroke="#0066CC" stroke-width="2"/>
    
    <!-- Beläge (alle 14px = 2m) -->
    <g fill="#8B4513">
      <rect x="258" y="406" width="184" height="3"/>
      <rect x="258" y="392" width="184" height="3"/>
      <!-- ... weitere Beläge ... -->
    </g>
    
    <!-- Verankerungen -->
    <g stroke="#CC0000" stroke-width="1.5" stroke-dasharray="4,3">
      <line x1="260" y1="350" x2="280" y2="350"/>
      <line x1="260" y1="280" x2="280" y2="280"/>
      <!-- ... weitere Verankerungen ... -->
    </g>
  </g>
  
  <!-- 5. Beschriftungen -->
  <g id="beschriftungen">
    <!-- Höhenskala links -->
    <line x1="55" y1="420" x2="55" y2="20" stroke="#333"/>
    <text x="45" y="424" text-anchor="end" font-size="9">±0.00</text>
    <text x="45" y="44" text-anchor="end" font-size="9">+54.6m</text>
    
    <!-- Zonenbeschriftung -->
    <text x="350" y="450" text-anchor="middle">Westturm (54.6m)</text>
    <text x="160" y="450" text-anchor="middle" font-size="8">Seitenschiff</text>
    <text x="540" y="450" text-anchor="middle" font-size="8">Seitenschiff</text>
  </g>
</svg>
```

---

## Prompt-Änderungen gegenüber aktuellem Prompt

### 1. NEUE Sektion hinzufügen: "ANSICHT-SPEZIFIKATION" (nach Gebäude-Identifikation)

```diff
+ ## 2. ANSICHT-SPEZIFIKATION (NEU!)
+ 
+ ### Gewählte Ansicht: WEST (W)
+ - **Blickrichtung:** Betrachter steht im WESTEN, schaut nach OSTEN
+ - **Hauptelemente sichtbar:**
+   - Westturm (frontal, zentral, dominant)
+   - Hauptportal (unter dem Turm)
+   - Strebebögen (links und rechts des Turms)
+   - Teile der Seitenschiffe (seitlich)
+ 
+ ### Verdeckungslogik (KRITISCH!)
+ **Was ist SICHTBAR:**
+ 1. Westturm (komplett, 54.6m)
+ 2. Hauptportal (unter Turm)
+ 3. Strebebögen (links/rechts)
+ 4. Seitenschiffe (teilweise, niedrigere Bereiche)
+ 
+ **Was ist NICHT sichtbar (verdeckt):**
+ 1. Kirchenschiff (hinter Turm)
+ 2. Chor (ganz hinten)
```

### 2. Höhenzonen-Tabelle ANPASSEN (Sichtbarkeit hinzufügen)

```diff
- | Zone | Typ | Höhe |
- |------|-----|------|
- | Westturm | turm | 54.6m |
- | Kirchenschiff | hauptgebaeude | 25.0m |
- | Chor | anbau | 18.0m |
- | Seitenschiffe | anbau | 12.0m |

+ | Zone | Sichtbarkeit | Höhe | In SVG |
+ |------|--------------|------|--------|
+ | Westturm | ✅ VOLL | 54.6m | Zentral, dominant |
+ | Hauptportal | ✅ VOLL | 12m | Unter Turm |
+ | Strebebögen | ✅ VOLL | 15-25m | Links/rechts vom Turm |
+ | Seitenschiffe | ⚠️ TEIL | 12m | Seitlich, niedrig |
+ | Kirchenschiff | ❌ VERDECKT | 25m | Nicht zeichnen! |
+ | Chor | ❌ VERDECKT | 18m | Nicht zeichnen! |
```

### 3. SVG-Anforderungen ANPASSEN (Zeichenreihenfolge)

```diff
+ ### Aufbau (Zeichenreihenfolge)
+ 1. **ZUERST (hinten):** Seitenschiffe (niedrig, seitlich)
+ 2. **DANN:** Strebebögen
+ 3. **ZULETZT (vorne):** Westturm (verdeckt alles dahinter)
```

### 4. Titel im SVG ANPASSEN

```diff
- FASSADENANSICHT - Kirche St. Peter und Paul
+ FASSADENANSICHT WEST - Kirche St. Peter und Paul
+ Blickrichtung: Von West nach Ost
```

---

## API-Endpoint für richtungsspezifische Prompts

```python
@router.get("/api/v1/building/{egid}/svg-prompt")
async def get_svg_prompt(
    egid: str,
    direction: str = Query("W", regex="^(N|NO|O|SO|S|SW|W|NW)$"),
    svg_type: str = Query("ansicht", regex="^(grundriss|ansicht|schnitt)$")
) -> SVGPromptResponse:
    """
    Generiert einen richtungsspezifischen SVG-Prompt.
    
    Args:
        egid: Eidgenössischer Gebäudeidentifikator
        direction: Blickrichtung (N, NO, O, SO, S, SW, W, NW)
        svg_type: Art des SVGs (grundriss, ansicht, schnitt)
    
    Returns:
        SVG-Prompt mit Ansichts-Spezifikation
    """
    
    # Gebäudedaten laden
    building = await building_service.get_by_egid(egid)
    
    # Basis-Prompt generieren
    base_prompt = await prompt_generator.generate_base_prompt(building)
    
    # Richtungs-Spezifikation hinzufügen
    direction_section = generate_direction_section(
        building=building,
        direction=direction,
        svg_type=svg_type
    )
    
    # Sichtbarkeitsanalyse
    visibility = analyze_visibility(
        zones=building.zones,
        direction=direction
    )
    
    # Vollständigen Prompt zusammensetzen
    full_prompt = f"""
{base_prompt}

{direction_section}

## Sichtbare Zonen für {direction}-Ansicht
{format_visibility(visibility)}

## Zeichenreihenfolge
{format_draw_order(visibility)}
"""
    
    return SVGPromptResponse(
        prompt=full_prompt,
        direction=direction,
        visible_zones=[z.name for z in visibility['visible']],
        hidden_zones=[z.name for z in visibility['hidden']]
    )
```

---

*Prompt-Erweiterung erstellt: 30.12.2025*
*Für: Kirche St. Peter und Paul, Ansicht WEST*
*Basierend auf: Vor-Ort-Fotos und geodaten-ch API*
