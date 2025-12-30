# backend/tests/test_height_validation.py
"""
pytest Tests für Höhen-Validierung.

TASK 6 aus CLAUDE_TASKS.md:
Formale Tests für validate_heights und validate_zone_consistency.

Erstellt: 30.12.2025
"""

import pytest
import sys
from pathlib import Path

# Backend-Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.smart_building.models import (
    BuildingDataBundle,
    ZoneInfo,
    DataSource,
)
from app.services.smart_building.validation import (
    validate_heights,
    validate_zone_consistency,
    MIN_HEIGHTS_BY_GKAT,
)


class TestValidateHeights:
    """Tests für validate_heights Funktion."""

    def test_valid_normal_building(self):
        """Normales MFH mit plausiblen Höhen - keine Warnungen."""
        bundle = BuildingDataBundle(
            gwr_category_code=1030,  # MFH
            gwr_floors=4,
            traufhoehe_m=10.0,
            firsthoehe_m=13.0,
        )
        warnings = validate_heights(bundle)
        assert len(warnings) == 0

    def test_height_too_low_for_gkat(self):
        """Firsthöhe zu niedrig für Gebäudekategorie (Museum)."""
        bundle = BuildingDataBundle(
            gwr_category_code=1060,  # Bildung/Kultur - min 12m
            gwr_floors=2,
            traufhoehe_m=6.0,
            firsthoehe_m=8.0,  # Zu niedrig!
        )
        warnings = validate_heights(bundle)
        assert len(warnings) >= 1
        assert any("unplausibel niedrig" in w for w in warnings)

    def test_height_too_low_for_floors(self):
        """Höhe zu niedrig für Geschosszahl."""
        bundle = BuildingDataBundle(
            gwr_category_code=1030,  # MFH
            gwr_floors=6,  # 6 Geschosse
            traufhoehe_m=8.0,
            firsthoehe_m=10.0,  # Nur 10m für 6 Geschosse!
        )
        warnings = validate_heights(bundle)
        assert len(warnings) >= 1
        assert any("passt nicht zu" in w for w in warnings)

    def test_height_very_high_for_floors(self):
        """Höhe sehr hoch für Geschosszahl - möglicherweise Turm."""
        bundle = BuildingDataBundle(
            gwr_category_code=1030,  # MFH
            gwr_floors=3,  # 3 Geschosse
            traufhoehe_m=20.0,
            firsthoehe_m=25.0,  # 25m für 3 Geschosse - verdächtig
        )
        warnings = validate_heights(bundle)
        assert len(warnings) >= 1
        assert any("sehr hoch" in w or "moeglicherweise Turm" in w for w in warnings)

    def test_first_lower_than_traufe(self):
        """First niedriger als Traufe - Datenfehler!"""
        bundle = BuildingDataBundle(
            gwr_category_code=1030,
            gwr_floors=3,
            traufhoehe_m=15.0,
            firsthoehe_m=12.0,  # FEHLER: First < Traufe
        )
        warnings = validate_heights(bundle)
        assert len(warnings) >= 1
        assert any("inkonsistent" in w for w in warnings)

    def test_church_high_height_no_warning(self):
        """Kirche mit hoher Firsthöhe - keine Warnung (Turm erwartet)."""
        bundle = BuildingDataBundle(
            gwr_category_code=1110,  # Kirche
            gwr_floors=1,
            traufhoehe_m=20.0,
            firsthoehe_m=60.0,  # Turm - OK für Kirche
        )
        warnings = validate_heights(bundle)
        # Sollte keine "sehr hoch" Warnung für Kirchen geben
        assert not any("sehr hoch" in w for w in warnings)


class TestValidateZoneConsistency:
    """Tests für validate_zone_consistency Funktion."""

    def test_valid_bundeshaus(self):
        """Bundeshaus: Korrekte Zonen, Kuppel über First erlaubt."""
        bundle = BuildingDataBundle(
            traufhoehe_m=53.2,
            firsthoehe_m=62.6,
        )
        bundle.zones = [
            ZoneInfo(id="z1", name="Arkaden", zone_type="arkade",
                     traufhoehe_m=6.0, firsthoehe_m=6.0),
            ZoneInfo(id="z2", name="Hauptgebäude", zone_type="hauptgebaeude",
                     traufhoehe_m=25.0, firsthoehe_m=30.0),
            ZoneInfo(id="z3", name="Kuppel", zone_type="kuppel",
                     traufhoehe_m=30.0, firsthoehe_m=64.0),
        ]
        warnings = validate_zone_consistency(bundle)
        # Arkaden/Kuppel sind erlaubt unter/über API-Höhen
        # Hauptgebäude ist unter Traufe - das sollte warnen
        assert any("Hauptgeb" in w and "unter" in w for w in warnings)

    def test_invalid_einsteinhaus_old_data(self):
        """Einsteinhaus mit alten, falschen Zone-Daten."""
        bundle = BuildingDataBundle(
            traufhoehe_m=22.3,
            firsthoehe_m=26.2,
        )
        bundle.zones = [
            ZoneInfo(id="z1", name="Hauptgebäude", zone_type="hauptgebaeude",
                     traufhoehe_m=12.0, firsthoehe_m=16.0),  # FALSCH!
        ]
        warnings = validate_zone_consistency(bundle)
        assert len(warnings) >= 1
        assert any("deutlich unter" in w and "Traufhoehe" in w for w in warnings)

    def test_valid_einsteinhaus_fixed(self):
        """Einsteinhaus mit korrigierten Zone-Daten."""
        bundle = BuildingDataBundle(
            traufhoehe_m=22.3,
            firsthoehe_m=26.2,
        )
        bundle.zones = [
            ZoneInfo(id="z1", name="Hauptgebäude", zone_type="hauptgebaeude",
                     traufhoehe_m=22.0, firsthoehe_m=26.0),  # KORREKT
        ]
        warnings = validate_zone_consistency(bundle)
        # Keine Warnungen erwartet
        assert len(warnings) == 0

    def test_warning_zone_much_higher_than_api(self):
        """Warnung wenn Zone deutlich höher als API (kein Turm)."""
        bundle = BuildingDataBundle(
            traufhoehe_m=15.0,
            firsthoehe_m=18.0,
        )
        bundle.zones = [
            ZoneInfo(id="z1", name="Hauptgebäude", zone_type="hauptgebaeude",
                     traufhoehe_m=15.0, firsthoehe_m=30.0),  # 30m bei 18m API-First
        ]
        warnings = validate_zone_consistency(bundle)
        assert len(warnings) >= 1
        assert any("deutlich ueber" in w for w in warnings)

    def test_turm_zone_allowed_higher(self):
        """Turm-Zone darf höher als API-First sein ohne Warnung."""
        bundle = BuildingDataBundle(
            traufhoehe_m=15.0,
            firsthoehe_m=18.0,
        )
        bundle.zones = [
            ZoneInfo(id="z1", name="Hauptgebäude", zone_type="hauptgebaeude",
                     traufhoehe_m=15.0, firsthoehe_m=18.0),
            ZoneInfo(id="z2", name="Kirchturm", zone_type="turm",
                     traufhoehe_m=18.0, firsthoehe_m=50.0),  # Turm viel höher - OK
        ]
        warnings = validate_zone_consistency(bundle)
        # Turm sollte keine "deutlich über" Warnung erzeugen
        assert not any("Kirchturm" in w and "deutlich ueber" in w for w in warnings)


class TestMinHeightsByGkat:
    """Tests für GKAT-Mindesthöhen Konstanten."""

    def test_efh_min_height(self):
        """EFH (1020) hat Mindesthöhe 6m."""
        assert MIN_HEIGHTS_BY_GKAT[1020] == 6

    def test_mfh_min_height(self):
        """MFH (1030) hat Mindesthöhe 9m."""
        assert MIN_HEIGHTS_BY_GKAT[1030] == 9

    def test_church_min_height(self):
        """Kirche (1110) hat Mindesthöhe 15m."""
        assert MIN_HEIGHTS_BY_GKAT[1110] == 15

    def test_museum_min_height(self):
        """Museum (1060, 1130) hat Mindesthöhe 12m."""
        assert MIN_HEIGHTS_BY_GKAT[1060] == 12
        assert MIN_HEIGHTS_BY_GKAT[1130] == 12


# Integration test
class TestValidationIntegration:
    """Integration Tests für beide Validierungsfunktionen zusammen."""

    def test_full_validation_pipeline(self):
        """Testet beide Validierungen nacheinander."""
        bundle = BuildingDataBundle(
            gwr_category_code=1030,  # MFH
            gwr_floors=4,
            traufhoehe_m=12.0,
            firsthoehe_m=15.0,
        )
        bundle.zones = [
            ZoneInfo(id="z1", name="Hauptgebäude", zone_type="hauptgebaeude",
                     traufhoehe_m=12.0, firsthoehe_m=15.0),
        ]

        # Beide Validierungen durchführen
        height_warnings = validate_heights(bundle)
        zone_warnings = validate_zone_consistency(bundle)

        # Für korrekte Daten sollten keine Fehler auftreten
        assert len(height_warnings) == 0
        assert len(zone_warnings) == 0

    def test_warnings_added_to_bundle(self):
        """Warnungen werden zum Bundle hinzugefügt."""
        bundle = BuildingDataBundle(
            gwr_category_code=1060,  # Kultur - min 12m
            gwr_floors=2,
            traufhoehe_m=5.0,
            firsthoehe_m=7.0,  # Zu niedrig
        )

        validate_heights(bundle)

        # Warnung sollte im Bundle sein
        assert len(bundle.warnings) > 0
        assert any("unplausibel niedrig" in w for w in bundle.warnings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
