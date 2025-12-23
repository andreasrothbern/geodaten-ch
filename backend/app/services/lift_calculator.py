"""
Lift Calculator Service

Berechnet Gerüstlifte nach NPK 114 Positionen.
- Materiallift (einfacher Aufzug für Material)
- Personenlift (für Personen zugelassen)
- Kombinierter Lift (Material + Person)
"""

from dataclasses import dataclass
from typing import Optional, Literal
from enum import Enum


class LiftType(str, Enum):
    """Lift-Typen"""
    MATERIAL = "material"
    PERSON = "person"
    COMBINED = "combined"


@dataclass
class LiftConfiguration:
    """Konfiguration eines Gerüstlifts"""
    lift_type: LiftType
    height_m: float
    width_m: float = 1.35  # Standard-Breite
    levels: int = 1
    facade_index: Optional[int] = None  # Welche Fassade


@dataclass
class LiftCalculationResult:
    """Ergebnis der Lift-Berechnung"""
    lift_type: LiftType
    height_m: float
    width_m: float
    levels: int
    area_m2: float
    npk_positions: list
    weight_estimate_kg: float
    notes: str


class LiftCalculator:
    """
    Berechnet Gerüstlifte nach NPK 114.3xx Positionen.

    NPK-Positionen für Lifte:
    - 114.312.100: Materiallift Grundposition
    - 114.312.110: Materiallift pro Etage
    - 114.312.200: Personenlift Grundposition
    - 114.312.210: Personenlift pro Etage
    """

    # NPK-Positionsnummern
    NPK_POSITIONS = {
        'material_lift_base': {
            'position': '114.312.100',
            'name': 'Materiallift Grundposition',
            'unit': 'Stk',
            'includes': 'Basis mit Antrieb, 1 Plattform'
        },
        'material_lift_per_level': {
            'position': '114.312.110',
            'name': 'Materiallift Erweiterung pro Etage',
            'unit': 'Stk',
            'includes': 'Führungsschienen, Sicherung'
        },
        'person_lift_base': {
            'position': '114.312.200',
            'name': 'Personenlift Grundposition',
            'unit': 'Stk',
            'includes': 'Basis mit Antrieb, Kabine, Sicherheitseinrichtung'
        },
        'person_lift_per_level': {
            'position': '114.312.210',
            'name': 'Personenlift Erweiterung pro Etage',
            'unit': 'Stk',
            'includes': 'Führungsschienen, Haltestelle'
        }
    }

    # Typische Breiten (Layher)
    LIFT_WIDTHS = {
        'narrow': 1.35,  # Schmaler Lift
        'standard': 1.57,  # Standard
        'wide': 2.07,     # Breiter Lift
    }

    # Gewichtsschätzung pro m Höhe (kg)
    WEIGHT_PER_METER = {
        LiftType.MATERIAL: 85,   # Leichter ohne Kabine
        LiftType.PERSON: 120,    # Schwerer mit Kabine
        LiftType.COMBINED: 140   # Schwerster
    }

    def calculate_lift_area(
        self,
        lift_type: LiftType,
        height_m: float,
        width_m: float = 1.35
    ) -> float:
        """
        Berechne die Gerüstfläche, die der Lift einnimmt.

        Lifte sind typischerweise 1.35m breit und benötigen
        die volle Gerüsthöhe.

        Args:
            lift_type: Art des Lifts
            height_m: Höhe des Gerüsts
            width_m: Breite des Lifts (Standard 1.35m)

        Returns:
            Fläche in m² die der Lift benötigt
        """
        # Lift braucht die volle Höhe × Breite
        return height_m * width_m

    def calculate_levels(self, height_m: float, floor_height_m: float = 2.5) -> int:
        """
        Berechne Anzahl Etagen/Haltestellen.

        Args:
            height_m: Gesamthöhe
            floor_height_m: Höhe pro Geschoss

        Returns:
            Anzahl Etagen (mindestens 1)
        """
        import math
        return max(1, math.ceil(height_m / floor_height_m))

    def calculate_lift(self, config: LiftConfiguration) -> LiftCalculationResult:
        """
        Berechne komplette Lift-Daten.

        Args:
            config: Lift-Konfiguration

        Returns:
            Berechnungsergebnis mit NPK-Positionen
        """
        # Fläche berechnen
        area_m2 = self.calculate_lift_area(
            config.lift_type,
            config.height_m,
            config.width_m
        )

        # Etagen berechnen falls nicht angegeben
        levels = config.levels if config.levels > 0 else self.calculate_levels(config.height_m)

        # NPK-Positionen zusammenstellen
        npk_positions = []

        if config.lift_type == LiftType.MATERIAL:
            npk_positions.append({
                **self.NPK_POSITIONS['material_lift_base'],
                'quantity': 1
            })
            if levels > 1:
                npk_positions.append({
                    **self.NPK_POSITIONS['material_lift_per_level'],
                    'quantity': levels - 1  # Basis zählt als 1. Etage
                })

        elif config.lift_type == LiftType.PERSON:
            npk_positions.append({
                **self.NPK_POSITIONS['person_lift_base'],
                'quantity': 1
            })
            if levels > 1:
                npk_positions.append({
                    **self.NPK_POSITIONS['person_lift_per_level'],
                    'quantity': levels - 1
                })

        else:  # COMBINED
            # Kombiniert braucht beide Grundpositionen
            npk_positions.append({
                **self.NPK_POSITIONS['person_lift_base'],
                'quantity': 1,
                'note': 'Basis für Kombilift (Person + Material)'
            })
            npk_positions.append({
                **self.NPK_POSITIONS['material_lift_base'],
                'quantity': 1,
                'note': 'Materialplattform-Erweiterung'
            })
            if levels > 1:
                npk_positions.append({
                    **self.NPK_POSITIONS['person_lift_per_level'],
                    'quantity': levels - 1
                })

        # Gewichtsschätzung
        weight_estimate = config.height_m * self.WEIGHT_PER_METER.get(config.lift_type, 100)

        # Hinweise
        notes = self._generate_notes(config)

        return LiftCalculationResult(
            lift_type=config.lift_type,
            height_m=config.height_m,
            width_m=config.width_m,
            levels=levels,
            area_m2=round(area_m2, 2),
            npk_positions=npk_positions,
            weight_estimate_kg=round(weight_estimate, 0),
            notes=notes
        )

    def _generate_notes(self, config: LiftConfiguration) -> str:
        """Generiere Hinweise basierend auf Konfiguration"""
        notes = []

        if config.lift_type == LiftType.PERSON:
            notes.append("Personenlift erfordert Abnahme durch Fachperson")
            notes.append("Maximale Personenzahl beachten (typisch 2-4 Personen)")

        if config.lift_type == LiftType.COMBINED:
            notes.append("Kombilift: Nicht gleichzeitig Material und Personen befördern")

        if config.height_m > 20:
            notes.append("Bei Höhen >20m: Zwischenverankerung prüfen")

        if config.width_m < 1.5:
            notes.append("Schmaler Lift: Beschränkte Materialabmessungen beachten")

        return "; ".join(notes) if notes else "Standardkonfiguration"

    def get_available_widths(self) -> list:
        """Hole verfügbare Lift-Breiten"""
        return [
            {"id": "narrow", "width_m": 1.35, "name": "Schmal (1.35m)"},
            {"id": "standard", "width_m": 1.57, "name": "Standard (1.57m)"},
            {"id": "wide", "width_m": 2.07, "name": "Breit (2.07m)"}
        ]

    def get_lift_types(self) -> list:
        """Hole verfügbare Lift-Typen"""
        return [
            {
                "id": LiftType.MATERIAL.value,
                "name": "Materiallift",
                "description": "Einfacher Lift für Material, nicht für Personen zugelassen",
                "icon": "📦"
            },
            {
                "id": LiftType.PERSON.value,
                "name": "Personenlift",
                "description": "Für Personen zugelassen, höhere Sicherheitsanforderungen",
                "icon": "👷"
            },
            {
                "id": LiftType.COMBINED.value,
                "name": "Kombilift",
                "description": "Material und Personen (nicht gleichzeitig)",
                "icon": "🔄"
            }
        ]


# Singleton-Instanz
_lift_calculator: Optional[LiftCalculator] = None


def get_lift_calculator() -> LiftCalculator:
    """Hole Singleton-Instanz des Lift-Calculators"""
    global _lift_calculator
    if _lift_calculator is None:
        _lift_calculator = LiftCalculator()
    return _lift_calculator
