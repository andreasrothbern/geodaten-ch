# Umfassende Prompt-Analyse: Claude.ai vs. API

## Übersicht der analysierten Prompts

| Quelle | Gebäude | Dateien | Zeitstempel |
|--------|---------|---------|-------------|
| **Claude.ai** | Bundeshaus (Bundesplatz 3) | 1 kombiniertes Prompt | 2025-12-30 00:28 |
| **API (NEU)** | St. Peter und Paul (Rathausgasse 2) | 3 separate Prompts | 2025-12-30 01:30 |
| **API (ALT)** | St. Peter und Paul (Rathausgasse 2) | 3 separate Prompts | 2025-12-30 00:45 |

---

## 1. Struktureller Vergleich

### 1.1 Prompt-Architektur

| Aspekt | Claude.ai | API (3 Prompts) |
|--------|-----------|-----------------|
| **Anzahl Dateien** | 1 kombiniert | 3 separate |
| **Token pro Prompt** | ~1'800 | ~1'500 × 3 = ~4'500 |
| **Redundanz** | Keine (alles in 1 Datei) | ~80% (gleiche Basis 3×) |
| **SVG-Output** | 3 SVGs in 1 Response | 1 SVG pro Response |

### 1.2 Strukturelle Unterschiede

```
CLAUDE.AI (1 Prompt → 3 SVGs)          API (3 Prompts → 3 SVGs)
================================       ================================
# SVG-Generierung: Grundriss +         # SVG-Generierung: Grundriss
  Fassadenansicht + Gebäudeschnitt     
                                       ─────────────────────────────────
## 1. Gebäude-Identifikation           # SVG-Generierung: Fassadenansicht
## 2. RECHERCHE-ANWEISUNG              
## 3. Geometrische Basisdaten          ─────────────────────────────────
## 4. Terrain                          # SVG-Generierung: Gebäudeschnitt
## 5. Dach-Analyse                     
## 6. Höhenzonen                       (Jedes Prompt enthält die
## 7. Fassaden                          gleichen Abschnitte 1-10!)
## 8. Gerüst-Zugänge                   
## 10. SVG Style-Vorgaben              
## 11. Anforderungen (ALLE 3!)         ## 11. Anforderungen (NUR 1!)
## 12. Output: 3 SVGs                  ## 12. Output: 1 SVG
```

**Bewertung:**
- ✅ Claude.ai: Effizienter (1 Call statt 3)
- ❌ API: 80% Redundanz, 3× Kosten

---

## 2. Datenqualität-Vergleich

### 2.1 Bundeshaus (Claude.ai Prompt)

| Feld | Wert | Bewertung |
|------|------|-----------|
| Gebäudename | Bundeshaus | ✅ Korrekt |
| Gebäudetyp | Parlamentsgebäude | ✅ Korrekt |
| Baustil | Neorenaissance | ✅ Korrekt |
| Baujahr | 1902 | ✅ Korrekt |
| Komplexität | COMPLEX | ✅ Korrekt |
| Höhenzonen | 1 Zone (!) | ⚠️ UNZUREICHEND |
| Kuppel | Nicht erwähnt | ❌ FEHLT |
| Dachform | Pultdach (!) | ❌ FALSCH (Kuppel!) |

**Kritische Probleme Bundeshaus:**
```
IST (Prompt):
| Zone | Typ | Höhe | Traufe | Gerüst |
|------|-----|------|--------|--------|
| Hauptgebäude Bundeshaus | hauptgebaeude | 62.6m | 53.2m | Sonderkonstruktion |

SOLL (Realität):
| Zone | Typ | Höhe | Traufe | Gerüst |
|------|-----|------|--------|--------|
| Hauptgebäude West | hauptgebaeude | 30m | 25m | Standard |
| Hauptgebäude Ost | hauptgebaeude | 30m | 25m | Standard |
| Verbindungsgang West | verbindung | 25m | 20m | Standard |
| Verbindungsgang Ost | verbindung | 25m | 20m | Standard |
| Zentralbau | hauptgebaeude | 30m | 25m | Standard |
| Kuppel | kuppel | 64m | - | Spezialgerüst |
```

### 2.2 St. Peter und Paul (API Prompts - NEU)

| Feld | Wert | Bewertung |
|------|------|-----------|
| Gebäudename | RECHERCHIEREN | ⚠️ Muss recherchiert werden |
| Gebäudetyp | Sakralbau (Kirche mit Turm) | ✅ Verbessert! (war: Wohngebäude) |
| Baustil | Nicht angegeben | ⚠️ Fehlt |
| Baujahr | Nicht angegeben | ⚠️ Fehlt |
| Komplexität | COMPLEX | ✅ Korrekt |
| Höhenzonen | 2 Zonen | ✅ Verbessert! |
| Turm | 54.6m, Sonderkonstruktion | ✅ Erkannt |
| Dachform | Mansarddach | ⚠️ Fraglich für Kirche |

**Verbesserung API NEU vs. ALT:**
```
ALT:                                    NEU:
─────────────────────────────────       ─────────────────────────────────
Gebäudetyp: Wohngebäude ❌              Gebäudetyp: Sakralbau ✅
Komplexität: SIMPLE ❌                  Komplexität: COMPLEX ✅
Höhenzonen: 1 (Hauptgebäude) ❌         Höhenzonen: 2 (Haupt + Turm) ✅
Turm: Nicht erkannt ❌                  Turm: 54.6m erkannt ✅
```

---

## 3. Encoding-Analyse

### 3.1 Encoding-Fehler in API-Prompts

| Original | Kaputt | Häufigkeit |
|----------|--------|------------|
| ä | Ã¤ | ~50× |
| ö | Ã¶ | ~20× |
| ü | Ã¼ | ~30× |
| ß | Ã | ~5× |
| → | â†' | ~10× |
| ± | Â± | ~5× |
| ² | Â² | ~5× |
| ✅ | âœ… | ~3× |

**Ursache:** UTF-8 wird als ISO-8859-1 interpretiert

**Lösung:**
```typescript
// Server-seitig vor dem Speichern:
const fixEncoding = (text: string): string => {
  return text
    .replace(/Ã¤/g, 'ä')
    .replace(/Ã¶/g, 'ö')
    .replace(/Ã¼/g, 'ü')
    .replace(/Ã/g, 'ß')
    .replace(/â†'/g, '→')
    .replace(/Â±/g, '±')
    .replace(/Â²/g, '²')
    .replace(/âœ…/g, '✅');
};

// Oder: Korrekte Content-Type Header setzen
headers: { 'Content-Type': 'text/markdown; charset=utf-8' }
```

### 3.2 Claude.ai Prompt

✅ **Keine Encoding-Fehler** - UTF-8 korrekt

---

## 4. Höhenzonen-Analyse

### 4.1 Automatische Turm-Erkennung

Die API hat eine Turm-Erkennung implementiert:

```
Traufhöhe: 9.3m
Firsthöhe: 54.6m
Differenz: 45.3m → Turm erkannt!
```

**Aber:** Die Höhe des Hauptgebäudes ist falsch:

| Zone | IST (Prompt) | SOLL (Realität) |
|------|--------------|-----------------|
| Hauptgebäude | 9.3m | 25m (Kirchenschiff) |
| Turm | 54.6m | 54.6m ✅ |
| Seitenschiffe | - | 15m (fehlt!) |
| Chor | - | 18m (fehlt!) |

**Problem:** `Traufhöhe = 9.3m` wird als Hauptgebäude-Höhe verwendet.
- Das ist die NIEDRIGSTE Traufe (vermutlich Seitenschiff)
- Das Kirchenschiff ist ~25m hoch

### 4.2 Empfohlene Zonen-Logik

```typescript
function analyzeChurchZones(traufhoehe: number, firsthoehe: number): Zone[] {
  const heightDiff = firsthoehe - traufhoehe;
  
  if (heightDiff > 30) {
    // Kirche mit hohem Turm
    return [
      { name: 'Kirchenschiff', height: traufhoehe + 15, type: 'hauptgebaeude' },
      { name: 'Seitenschiffe', height: traufhoehe + 5, type: 'anbau' },
      { name: 'Turm', height: firsthoehe, type: 'turm', scaffold: 'Spezialgerüst' },
      { name: 'Chor', height: traufhoehe + 8, type: 'anbau' }
    ];
  }
  // ...
}
```

---

## 5. Token-Effizienz

### 5.1 Aktuelle Situation

| Variante | Tokens | API-Calls | Kosten (relativ) |
|----------|--------|-----------|------------------|
| Claude.ai (1 Prompt) | ~1'800 | 1 | 1× |
| API (3 Prompts) | ~4'500 | 3 | 2.5× |

### 5.2 Optimierte Variante

```
OPTIMIERT: System-Prompt + 3 kurze User-Prompts
─────────────────────────────────────────────────
System-Prompt (1×):     ~800 Tokens (Style, Regeln)
User-Prompt Grundriss:  ~400 Tokens (nur Gebäudedaten + Anforderung)
User-Prompt Fassade:    ~400 Tokens
User-Prompt Schnitt:    ~400 Tokens
─────────────────────────────────────────────────
TOTAL:                  ~2'000 Tokens (55% Einsparung!)
```

---

## 6. Fehlende Informationen

### 6.1 Beide Prompts fehlt:

| Information | Wichtigkeit | Auswirkung |
|-------------|-------------|------------|
| Baustil-Merkmale | Hoch | Falsche Fenster/Portal-Darstellung |
| Turmform (Spitzhelm/Kuppel) | Hoch | Falsche Turm-Darstellung |
| Turmanzahl | Kritisch | 1 vs. 2 Türme |
| Turm-Position | Hoch | Zentral vs. Flankierend |
| Innenraum-Struktur | Mittel | Falscher Schnitt |
| Architekt | Niedrig | Nur für Dokumentation |

### 6.2 Nur API-Prompts fehlt:

| Information | Status |
|-------------|--------|
| Gebäudename | RECHERCHIEREN (nicht aufgelöst) |
| Baustil | Nicht angegeben |
| Baujahr | Nicht angegeben |

### 6.3 Nur Claude.ai-Prompt fehlt:

| Information | Status |
|-------------|--------|
| Kuppel als Zone | Nicht definiert |
| Flügelbauten | Nicht definiert |
| Verbindungsgänge | Nicht definiert |

---

## 7. Dach-Analyse Probleme

| Gebäude | IST (Prompt) | SOLL (Realität) |
|---------|--------------|-----------------|
| Bundeshaus | Pultdach 15° | Kuppel + Walmdach |
| St. Peter und Paul | Mansarddach 72° | Satteldach + Spitzhelm |

**Problem:** Die automatische Dach-Erkennung liefert falsche Ergebnisse.

**Empfehlung:** Dachform-Override für bekannte Gebäudetypen:
```typescript
if (buildingType === 'Sakralbau') {
  roofType = 'satteldach'; // oder aus Recherche
}
if (buildingType === 'Parlamentsgebäude' && hasKuppel) {
  roofType = 'kuppel';
}
```

---

## 8. Zusammenfassung: Stärken & Schwächen

### 8.1 Claude.ai Prompt

| Stärken | Schwächen |
|---------|-----------|
| ✅ Kein Encoding-Problem | ❌ Nur 1 Höhenzone |
| ✅ Alle 3 SVGs in 1 Call | ❌ Kuppel fehlt |
| ✅ Gebäudename korrekt | ❌ Falsche Dachform |
| ✅ Effizient (Token) | ❌ Keine Flügel-Zonen |

### 8.2 API Prompts (NEU)

| Stärken | Schwächen |
|---------|-----------|
| ✅ Turm erkannt | ❌ Encoding kaputt |
| ✅ 2 Höhenzonen | ❌ 80% Redundanz |
| ✅ Sakralbau erkannt | ❌ RECHERCHIEREN nicht aufgelöst |
| ✅ Komplexität COMPLEX | ❌ Baustil fehlt |
| | ❌ 3× API-Calls nötig |

---

## 9. Empfehlungen

### 9.1 Sofort umsetzbar (Quick Wins)

1. **Encoding fixen:**
   ```typescript
   response.setHeader('Content-Type', 'text/markdown; charset=utf-8');
   ```

2. **Gebäude-Cache nutzen:**
   ```typescript
   const cache = {
     '191821074': { // EGID
       name: 'Kirche St. Peter und Paul',
       type: 'Christkatholische Kathedralkirche',
       style: 'Neugotik',
       year: 1864,
       tower: { count: 1, position: 'zentral', form: 'Spitzhelm', height: 54.6 }
     }
   };
   ```

3. **1 Prompt statt 3:**
   - Alle 3 SVG-Anforderungen in 1 Prompt
   - Trennung durch Kommentar: `<!-- SVG 1: Grundriss -->`

### 9.2 Mittelfristig

4. **Server-seitige Recherche:**
   - VOR dem API-Call Gebäude recherchieren
   - Ergebnis cachen
   - Kein "RECHERCHIEREN" mehr im Prompt

5. **Höhenzonen-Generator:**
   - Basierend auf Gebäudetyp + Höhendifferenz
   - Validierung gegen bekannte Gebäude

6. **Dachform-Override:**
   - Manuelle Korrektur für bekannte Gebäudetypen
   - Konfidenz-Schwelle für automatische Erkennung

### 9.3 Langfristig

7. **Gebäude-Datenbank:**
   - Schweizer Denkmalpflege-Daten integrieren
   - Wikipedia/Wikidata verknüpfen
   - Swisstopo-Daten ergänzen

8. **ML-basierte Klassifikation:**
   - Gebäudetyp aus Polygon-Form
   - Baustil aus Höhenprofil
   - Turm-Erkennung aus Höhendifferenz

---

## 10. Optimiertes Prompt-Template

Siehe separates Dokument: `svg_prompt_optimization/templates/`

**Kernprinzipien:**
1. **Keine RECHERCHIEREN-Felder** → Server-seitig auflösen
2. **Mindestens 3-5 Höhenzonen** für komplexe Gebäude
3. **Turm/Kuppel explizit** mit Form und Position
4. **Baustil-Merkmale** für korrekte Darstellung
5. **1 kombiniertes Prompt** oder System-Prompt + kurze User-Prompts

---

*Analyse erstellt: 30. Dezember 2025*
*Für: Gerüstplanung Schweiz App v3.0*
