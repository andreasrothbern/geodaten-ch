# backend/app/services/access_calculator.py
"""
Automatische Berechnung von Gerüst-Zugängen (Treppen).

Basiert auf SUVA-Vorschriften:
- Max. 50m Fluchtweg zum nächsten Abstieg
- Mindestens 2 Zugänge pro Gerüst
- Bevorzugt an Ecken/Stirnseiten

Version: 1.0
Datum: 25.12.2025
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Literal
from pydantic import BaseModel


# =============================================================================
# KONSTANTEN (SUVA-konform)
# =============================================================================

MAX_FLUCHTWEG_M = 50.0           # Max. Abstand zum nächsten Zugang
MIN_ZUGAENGE = 2                 # Mindestens 2 pro Gerüst
ZUGANG_BREITE_M = 0.6            # Treppenbreite (Standard)
CORNER_THRESHOLD_M = 3.0         # Abstand zur Ecke für Optimierung
MIN_FASSADE_FOR_ACCESS_M = 5.0   # Mindestlänge Fassade für Zugang


# =============================================================================
# DATENMODELLE
# =============================================================================

class AccessPoint(BaseModel):
    """Gerüst-Zugang (Treppe)"""
    
    id: str                                    # "Z1", "Z2", etc.
    fassade_id: str                            # "N", "E", "S", "W" oder "F1", "F2"
    position_m: float                          # Position auf der Fassade (vom Start)
    position_percent: float                    # 0.0 - 1.0 relativ zur Fassadenlänge
    source: Literal["auto", "claude", "manual"] = "auto"
    grund: str | None = None                   # Begründung für Platzierung
    
    # Koordinaten (werden nachträglich berechnet)
    koordinate_e: float | None = None          # LV95 Ost
    koordinate_n: float | None = None          # LV95 Nord


class AccessCalculationResult(BaseModel):
    """Ergebnis der Zugangsberechnung"""
    
    zugaenge: List[AccessPoint]
    geruest_umfang_m: float
    max_fluchtweg_m: float                     # Längster Fluchtweg
    suva_konform: bool                         # Alle Fluchtwege <= 50m?
    warnungen: List[str] = []


# =============================================================================
# HAUPTFUNKTIONEN
# =============================================================================

def calculate_access_points(
    fassaden: List[dict],
    geruest_umfang_m: float | None = None,
    min_zugaenge: int = MIN_ZUGAENGE,
    max_fluchtweg: float = MAX_FLUCHTWEG_M
) -> AccessCalculationResult:
    """
    Berechnet optimale Zugangspositionen für ein Gerüst.
    
    Args:
        fassaden: Liste der Fassaden mit:
            - id: str ("N", "E", "S", "W" oder "F1", "F2", ...)
            - laenge_m: float
            - start_m: float (optional, kumulierte Position)
            - ausrichtung_grad: float (optional, für Koordinatenberechnung)
        geruest_umfang_m: Gesamtumfang (wenn None, wird aus Fassaden berechnet)
        min_zugaenge: Mindestanzahl Zugänge
        max_fluchtweg: Maximaler Fluchtweg in Metern
    
    Returns:
        AccessCalculationResult mit Zugängen und Metadaten
    """
    
    warnungen = []
    
    # Umfang berechnen falls nicht gegeben
    if geruest_umfang_m is None:
        geruest_umfang_m = sum(f.get('laenge_m', 0) for f in fassaden)
    
    if geruest_umfang_m == 0:
        return AccessCalculationResult(
            zugaenge=[],
            geruest_umfang_m=0,
            max_fluchtweg_m=0,
            suva_konform=True,
            warnungen=["Keine Fassaden vorhanden"]
        )
    
    # Fassaden mit kumulierter Position versehen
    fassaden_mit_pos = _add_cumulative_positions(fassaden)
    
    # Schritt 1: Anzahl Zugänge berechnen
    anzahl = max(min_zugaenge, math.ceil(geruest_umfang_m / max_fluchtweg))
    
    # Schritt 2: Gleichmässig auf Umfang verteilen
    abstand = geruest_umfang_m / anzahl
    
    zugaenge = []
    for i in range(anzahl):
        # Position auf dem Umfang (versetzt um halben Abstand für bessere Verteilung)
        pos_umfang = (i + 0.5) * abstand
        
        # Wraparound für geschlossenen Umfang
        pos_umfang = pos_umfang % geruest_umfang_m
        
        # Finde zugehörige Fassade
        fassade, pos_auf_fassade = _find_fassade_at_position(fassaden_mit_pos, pos_umfang)
        
        if fassade is None:
            warnungen.append(f"Zugang Z{i+1}: Keine Fassade gefunden bei Position {pos_umfang:.1f}m")
            continue
        
        fassade_laenge = fassade.get('laenge_m', 1)
        
        zugaenge.append(AccessPoint(
            id=f"Z{i+1}",
            fassade_id=fassade['id'],
            position_m=pos_auf_fassade,
            position_percent=pos_auf_fassade / fassade_laenge if fassade_laenge > 0 else 0,
            source="auto",
            grund=f"Automatisch verteilt ({abstand:.1f}m Abstand)"
        ))
    
    # Schritt 3: Zu Ecken optimieren
    zugaenge = _optimize_to_corners(zugaenge, fassaden_mit_pos)
    
    # Schritt 4: Fluchtwege berechnen und validieren
    max_fluchtweg_actual = _calculate_max_fluchtweg(zugaenge, fassaden_mit_pos, geruest_umfang_m)
    suva_konform = max_fluchtweg_actual <= max_fluchtweg
    
    if not suva_konform:
        warnungen.append(
            f"SUVA-Vorschrift verletzt: Max. Fluchtweg {max_fluchtweg_actual:.1f}m > {max_fluchtweg}m"
        )
    
    return AccessCalculationResult(
        zugaenge=zugaenge,
        geruest_umfang_m=geruest_umfang_m,
        max_fluchtweg_m=max_fluchtweg_actual,
        suva_konform=suva_konform,
        warnungen=warnungen
    )


def calculate_access_for_zones(
    zones: List[dict],
    fassaden: List[dict]
) -> AccessCalculationResult:
    """
    Berechnet Zugänge unter Berücksichtigung von Gebäudezonen.
    
    Bei komplexen Gebäuden mit mehreren Zonen:
    - Mindestens ein Zugang pro Zone mit beruesten=True
    - Zugänge an Zonengrenzen bevorzugt
    
    Args:
        zones: Liste von BuildingZone-Dicts
        fassaden: Liste der Fassaden
    
    Returns:
        AccessCalculationResult
    """
    
    warnungen = []
    zugaenge = []
    zugang_counter = 1
    
    # Filtere Zonen die eingerüstet werden
    aktive_zonen = [z for z in zones if z.get('beruesten', True)]
    
    if not aktive_zonen:
        return AccessCalculationResult(
            zugaenge=[],
            geruest_umfang_m=0,
            max_fluchtweg_m=0,
            suva_konform=True,
            warnungen=["Keine Zonen zum Einrüsten"]
        )
    
    for zone in aktive_zonen:
        zone_fassaden_ids = zone.get('fassaden_ids', [])
        zone_fassaden = [f for f in fassaden if f['id'] in zone_fassaden_ids]
        
        if not zone_fassaden:
            warnungen.append(f"Zone {zone.get('name', zone.get('id'))}: Keine Fassaden gefunden")
            continue
        
        # Berechne Umfang dieser Zone
        zone_umfang = sum(f.get('laenge_m', 0) for f in zone_fassaden)
        
        # Mindestens 1 Zugang pro Zone, mehr bei grossen Zonen
        zone_zugaenge_count = max(1, math.ceil(zone_umfang / MAX_FLUCHTWEG_M))
        
        # Verteile Zugänge auf die Fassaden der Zone
        zone_fassaden_mit_pos = _add_cumulative_positions(zone_fassaden)
        abstand = zone_umfang / zone_zugaenge_count
        
        for i in range(zone_zugaenge_count):
            pos_umfang = (i + 0.5) * abstand
            fassade, pos_auf_fassade = _find_fassade_at_position(zone_fassaden_mit_pos, pos_umfang)
            
            if fassade:
                fassade_laenge = fassade.get('laenge_m', 1)
                zugaenge.append(AccessPoint(
                    id=f"Z{zugang_counter}",
                    fassade_id=fassade['id'],
                    position_m=pos_auf_fassade,
                    position_percent=pos_auf_fassade / fassade_laenge if fassade_laenge > 0 else 0,
                    source="auto",
                    grund=f"Zone '{zone.get('name', zone.get('id'))}'"
                ))
                zugang_counter += 1
    
    # Optimierung und Validierung
    zugaenge = _optimize_to_corners(zugaenge, fassaden)
    zugaenge = _remove_duplicates(zugaenge)
    
    geruest_umfang = sum(f.get('laenge_m', 0) for f in fassaden)
    max_fluchtweg = _calculate_max_fluchtweg(zugaenge, fassaden, geruest_umfang)
    
    return AccessCalculationResult(
        zugaenge=zugaenge,
        geruest_umfang_m=geruest_umfang,
        max_fluchtweg_m=max_fluchtweg,
        suva_konform=max_fluchtweg <= MAX_FLUCHTWEG_M,
        warnungen=warnungen
    )


# =============================================================================
# HILFSFUNKTIONEN
# =============================================================================

def _add_cumulative_positions(fassaden: List[dict]) -> List[dict]:
    """Fügt kumulierte Start-Positionen zu Fassaden hinzu."""
    
    result = []
    cumulative = 0.0
    
    for f in fassaden:
        f_copy = f.copy()
        f_copy['start_m'] = cumulative
        f_copy['end_m'] = cumulative + f.get('laenge_m', 0)
        result.append(f_copy)
        cumulative += f.get('laenge_m', 0)
    
    return result


def _find_fassade_at_position(
    fassaden: List[dict], 
    pos_umfang: float
) -> Tuple[Optional[dict], float]:
    """
    Findet die Fassade an einer Position auf dem Umfang.
    
    Returns:
        (fassade, position_auf_fassade) oder (None, 0)
    """
    
    for fassade in fassaden:
        start = fassade.get('start_m', 0)
        end = fassade.get('end_m', start + fassade.get('laenge_m', 0))
        
        if start <= pos_umfang < end:
            return fassade, pos_umfang - start
    
    # Fallback: letzte Fassade
    if fassaden:
        last = fassaden[-1]
        return last, last.get('laenge_m', 0)
    
    return None, 0


def _optimize_to_corners(
    zugaenge: List[AccessPoint],
    fassaden: List[dict],
    threshold_m: float = CORNER_THRESHOLD_M
) -> List[AccessPoint]:
    """
    Verschiebt Zugänge zu Ecken wenn sie nahe genug sind.
    
    Ecken sind praktisch für den Treppenaufbau, da dort
    oft mehr Platz ist und die Treppe nicht im Weg steht.
    """
    
    fassaden_dict = {f['id']: f for f in fassaden}
    optimized = []
    
    for z in zugaenge:
        fassade = fassaden_dict.get(z.fassade_id)
        if not fassade:
            optimized.append(z)
            continue
        
        fassade_laenge = fassade.get('laenge_m', 0)
        if fassade_laenge == 0:
            optimized.append(z)
            continue
        
        z_copy = z.model_copy()
        
        # Prüfe Nähe zum Fassaden-Start (= Ecke)
        if z.position_m < threshold_m:
            z_copy.position_m = 0.5  # Leicht versetzt von der Ecke
            z_copy.position_percent = 0.5 / fassade_laenge
            z_copy.grund = (z.grund or "") + " → Ecke (Start)"
        
        # Prüfe Nähe zum Fassaden-Ende (= nächste Ecke)
        elif fassade_laenge - z.position_m < threshold_m:
            z_copy.position_m = fassade_laenge - 0.5
            z_copy.position_percent = z_copy.position_m / fassade_laenge
            z_copy.grund = (z.grund or "") + " → Ecke (Ende)"
        
        optimized.append(z_copy)
    
    return optimized


def _remove_duplicates(
    zugaenge: List[AccessPoint],
    min_distance_m: float = 2.0
) -> List[AccessPoint]:
    """
    Entfernt Zugänge die zu nahe beieinander sind.
    
    Bei Zonen-basierter Berechnung können Zugänge an
    Zonengrenzen doppelt erscheinen.
    """
    
    if len(zugaenge) <= 1:
        return zugaenge
    
    # Sortiere nach Fassade und Position
    sorted_zugaenge = sorted(zugaenge, key=lambda z: (z.fassade_id, z.position_m))
    
    result = [sorted_zugaenge[0]]
    
    for z in sorted_zugaenge[1:]:
        last = result[-1]
        
        # Wenn gleiche Fassade und zu nahe
        if z.fassade_id == last.fassade_id:
            if abs(z.position_m - last.position_m) < min_distance_m:
                # Behalte den mit besserem Grund oder den ersten
                continue
        
        result.append(z)
    
    # IDs neu vergeben
    for i, z in enumerate(result):
        z.id = f"Z{i+1}"
    
    return result


def _calculate_max_fluchtweg(
    zugaenge: List[AccessPoint],
    fassaden: List[dict],
    geruest_umfang_m: float
) -> float:
    """
    Berechnet den längsten Fluchtweg (Abstand zwischen Zugängen).
    
    Der Fluchtweg ist der halbe Abstand zum nächsten Zugang,
    da man in beide Richtungen fliehen kann.
    """
    
    if len(zugaenge) <= 1:
        return geruest_umfang_m / 2 if zugaenge else geruest_umfang_m
    
    # Berechne absolute Positionen auf dem Umfang
    fassaden_mit_pos = _add_cumulative_positions(fassaden)
    fassaden_dict = {f['id']: f for f in fassaden_mit_pos}
    
    positionen = []
    for z in zugaenge:
        fassade = fassaden_dict.get(z.fassade_id)
        if fassade:
            pos_abs = fassade.get('start_m', 0) + z.position_m
            positionen.append(pos_abs)
    
    if not positionen:
        return geruest_umfang_m
    
    positionen.sort()
    
    # Berechne Abstände zwischen aufeinanderfolgenden Zugängen
    max_abstand = 0.0
    
    for i in range(len(positionen)):
        next_i = (i + 1) % len(positionen)
        
        if next_i == 0:
            # Abstand über den "Umfang-Wrap"
            abstand = (geruest_umfang_m - positionen[i]) + positionen[0]
        else:
            abstand = positionen[next_i] - positionen[i]
        
        max_abstand = max(max_abstand, abstand)
    
    # Fluchtweg ist max. halber Abstand (man kann in beide Richtungen)
    return max_abstand / 2


# =============================================================================
# KOORDINATEN-BERECHNUNG
# =============================================================================

def add_coordinates_to_access_points(
    zugaenge: List[AccessPoint],
    fassaden: List[dict]
) -> List[AccessPoint]:
    """
    Berechnet die LV95-Koordinaten für jeden Zugang.
    
    Benötigt fassaden mit:
    - start_coord: (e, n) Startpunkt
    - end_coord: (e, n) Endpunkt
    
    oder:
    - polygon_points: Liste der Eckpunkte
    """
    
    result = []
    
    for z in zugaenge:
        z_copy = z.model_copy()
        
        fassade = next((f for f in fassaden if f['id'] == z.fassade_id), None)
        if not fassade:
            result.append(z_copy)
            continue
        
        # Koordinaten aus Start/End
        start = fassade.get('start_coord')
        end = fassade.get('end_coord')
        
        if start and end:
            # Lineare Interpolation
            t = z.position_percent
            z_copy.koordinate_e = start[0] + t * (end[0] - start[0])
            z_copy.koordinate_n = start[1] + t * (end[1] - start[1])
        
        result.append(z_copy)
    
    return result


# =============================================================================
# EXPORT FÜR SVG
# =============================================================================

def zugaenge_to_svg_elements(
    zugaenge: List[AccessPoint],
    fassaden: List[dict],
    scale: float = 1.0,
    offset_x: float = 0,
    offset_y: float = 0
) -> str:
    """
    Generiert SVG-Elemente für die Zugänge.
    
    Returns:
        SVG-Gruppe als String
    """
    
    zugaenge_with_coords = add_coordinates_to_access_points(zugaenge, fassaden)
    
    elements = ['<g id="zugaenge">']
    
    for z in zugaenge_with_coords:
        if z.koordinate_e is None or z.koordinate_n is None:
            continue
        
        x = (z.koordinate_e - offset_x) * scale
        y = (z.koordinate_n - offset_y) * scale
        
        # Rechteck für Zugang
        elements.append(f'''
        <g id="zugang-{z.id}" class="zugang">
            <rect x="{x - 10}" y="{y - 15}" 
                  width="20" height="30" 
                  fill="#FFC107" stroke="#F57F17" stroke-width="1"/>
            <text x="{x}" y="{y + 5}" 
                  text-anchor="middle" font-size="12" fill="#333">{z.id}</text>
        </g>''')
    
    elements.append('</g>')
    
    return '\n'.join(elements)
