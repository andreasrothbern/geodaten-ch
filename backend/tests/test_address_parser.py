"""
Tests für den Adress-Range Parser.

Testet:
1. Verschiedene Adress-Formate
2. Range-Erkennung (gerade/ungerade)
3. Explizite Listen
4. Edge Cases
"""

import pytest
from app.services.address_parser import (
    parse_address_range,
    AddressRangeType,
    _parse_number_range,
    _determine_step,
)


class TestParseNumberRange:
    """Tests für die Hausnummern-Parsing Funktion."""

    def test_simple_range_even(self):
        """Gerade Range: 2-10 → [2, 4, 6, 8, 10]"""
        numbers, range_type = _parse_number_range("2-10")
        assert numbers == ["2", "4", "6", "8", "10"]
        assert range_type == AddressRangeType.RANGE

    def test_simple_range_odd(self):
        """Ungerade Range: 1-9 → [1, 3, 5, 7, 9]"""
        numbers, range_type = _parse_number_range("1-9")
        assert numbers == ["1", "3", "5", "7", "9"]
        assert range_type == AddressRangeType.RANGE

    def test_mixed_range(self):
        """Gemischte Range: 1-4 → [1, 2, 3, 4]"""
        numbers, range_type = _parse_number_range("1-4")
        assert numbers == ["1", "2", "3", "4"]
        assert range_type == AddressRangeType.RANGE

    def test_slash_notation(self):
        """Slash-Notation: 27/29 → [27, 29]"""
        numbers, range_type = _parse_number_range("27/29")
        assert numbers == ["27", "29"]
        assert range_type == AddressRangeType.EXPLICIT

    def test_single_number(self):
        """Einzelne Nummer: 15 → [15]"""
        numbers, range_type = _parse_number_range("15")
        assert numbers == ["15"]
        assert range_type == AddressRangeType.SINGLE

    def test_number_with_suffix(self):
        """Nummer mit Suffix: 15a → [15a]"""
        numbers, range_type = _parse_number_range("15a")
        assert numbers == ["15a"]
        assert range_type == AddressRangeType.SINGLE

    def test_range_with_spaces(self):
        """Range mit Leerzeichen: 2 - 10"""
        numbers, range_type = _parse_number_range("2 - 10")
        assert numbers == ["2", "4", "6", "8", "10"]
        assert range_type == AddressRangeType.RANGE


class TestDetermineStep:
    """Tests für die Schritt-Bestimmung."""

    def test_both_even(self):
        """Beide gerade → Schritt 2"""
        assert _determine_step(2, 10) == 2

    def test_both_odd(self):
        """Beide ungerade → Schritt 2"""
        assert _determine_step(1, 9) == 2

    def test_mixed(self):
        """Gemischt → Schritt 1"""
        assert _determine_step(1, 4) == 1
        assert _determine_step(2, 5) == 1


class TestParseAddressRange:
    """Tests für die vollständige Adress-Parsing Funktion."""

    def test_basic_address_with_range(self):
        """Knospenweg 2-10, Bern"""
        result = parse_address_range("Knospenweg 2-10, Bern")

        assert result.street == "Knospenweg"
        assert result.city == "Bern"
        assert result.numbers == ["2", "4", "6", "8", "10"]
        assert result.range_type == AddressRangeType.RANGE

    def test_address_with_plz(self):
        """Kramgasse 27/29, 3011 Bern"""
        result = parse_address_range("Kramgasse 27/29, 3011 Bern")

        assert result.street == "Kramgasse"
        assert result.city == "Bern"
        assert result.postal_code == "3011"
        assert result.numbers == ["27", "29"]
        assert result.range_type == AddressRangeType.EXPLICIT

    def test_single_address(self):
        """Bundesplatz 3, 3011 Bern"""
        result = parse_address_range("Bundesplatz 3, 3011 Bern")

        assert result.street == "Bundesplatz"
        assert result.city == "Bern"
        assert result.postal_code == "3011"
        assert result.numbers == ["3"]
        assert result.range_type == AddressRangeType.SINGLE

    def test_full_addresses_generation(self):
        """Generierung vollständiger Adressen"""
        result = parse_address_range("Knospenweg 2-6, 3006 Bern")
        addresses = result.get_full_addresses()

        assert len(addresses) == 3
        assert addresses[0] == "Knospenweg 2, 3006 Bern"
        assert addresses[1] == "Knospenweg 4, 3006 Bern"
        assert addresses[2] == "Knospenweg 6, 3006 Bern"

    def test_street_with_multiple_words(self):
        """Strasse mit mehreren Wörtern"""
        result = parse_address_range("Alter Aargauerstalden 2-6, Bern")

        assert result.street == "Alter Aargauerstalden"
        assert result.numbers == ["2", "4", "6"]

    def test_zurich_address(self):
        """Zürcher Adresse"""
        result = parse_address_range("Bahnhofstrasse 46-50, 8001 Zürich")

        assert result.street == "Bahnhofstrasse"
        assert result.city == "Zürich"
        assert result.postal_code == "8001"
        assert result.numbers == ["46", "48", "50"]


class TestEdgeCases:
    """Edge Cases und Spezialfälle."""

    def test_no_house_number(self):
        """Adresse ohne Hausnummer"""
        result = parse_address_range("Bundesplatz, Bern")

        assert result.street == "Bundesplatz"
        assert result.city == "Bern"
        assert result.numbers == []

    def test_reversed_range(self):
        """Umgekehrte Range: 10-2 → [2, 4, 6, 8, 10]"""
        numbers, _ = _parse_number_range("10-2")
        assert numbers == ["2", "4", "6", "8", "10"]

    def test_short_range(self):
        """Kurze Range: 2-4 → [2, 4]"""
        numbers, _ = _parse_number_range("2-4")
        assert numbers == ["2", "4"]

    def test_same_number_range(self):
        """Gleiche Nummer: 5-5 → [5]"""
        numbers, _ = _parse_number_range("5-5")
        assert numbers == ["5"]

    def test_large_range(self):
        """Grosse Range: 2-20 → 10 Nummern"""
        numbers, _ = _parse_number_range("2-20")
        assert len(numbers) == 10
        assert numbers[0] == "2"
        assert numbers[-1] == "20"

    def test_triple_slash(self):
        """Dreifach-Slash: 1/3/5 → geht nicht, wird als "1/3" geparst"""
        # Aktuell nur 2 Nummern unterstützt
        numbers, range_type = _parse_number_range("1/3/5")
        # Parser unterstützt aktuell nur 2er-Slash
        assert range_type == AddressRangeType.SINGLE  # Fallback


class TestAddressPatterns:
    """Tests für spezielle Schweizer Adress-Muster."""

    def test_strasse_ending(self):
        """Strasse mit -strasse Endung"""
        result = parse_address_range("Bahnhofstrasse 10-14, Zürich")
        assert result.street == "Bahnhofstrasse"
        assert result.numbers == ["10", "12", "14"]

    def test_gasse_ending(self):
        """Strasse mit -gasse Endung"""
        result = parse_address_range("Kramgasse 49-53, Bern")
        assert result.street == "Kramgasse"
        assert result.numbers == ["49", "51", "53"]

    def test_weg_ending(self):
        """Strasse mit -weg Endung"""
        result = parse_address_range("Knospenweg 2-10, 3027 Bern")
        assert result.street == "Knospenweg"
        assert result.postal_code == "3027"

    def test_platz_ending(self):
        """Platz (meist keine Range)"""
        result = parse_address_range("Bundesplatz 3, 3011 Bern")
        assert result.street == "Bundesplatz"
        assert result.range_type == AddressRangeType.SINGLE

    def test_address_with_canton(self):
        """Adresse mit Kanton (selten, aber möglich)"""
        result = parse_address_range("Marktgasse 10, 9000 St. Gallen")
        assert result.city == "St. Gallen"


class TestRealWorldAddresses:
    """Tests mit echten Schweizer Adressen."""

    def test_knospenweg_reihenhaus(self):
        """Knospenweg Reihenhaus-Siedlung (bekannter Testfall)"""
        result = parse_address_range("Knospenweg 2-10, 3027 Bern")

        assert result.street == "Knospenweg"
        assert result.postal_code == "3027"
        assert result.city == "Bern"
        assert result.numbers == ["2", "4", "6", "8", "10"]

        # Adressen generieren
        addresses = result.get_full_addresses()
        assert len(addresses) == 5
        assert "Knospenweg 4, 3027 Bern" in addresses

    def test_bollwerk_double(self):
        """Bollwerk Doppel-Adresse"""
        result = parse_address_range("Bollwerk 27/29, 3011 Bern")

        assert result.street == "Bollwerk"
        assert result.numbers == ["27", "29"]
        assert result.range_type == AddressRangeType.EXPLICIT

    def test_zurich_bahnhof(self):
        """Bahnhofstrasse Zürich"""
        result = parse_address_range("Bahnhofstrasse 46-50, 8001 Zürich")

        assert result.street == "Bahnhofstrasse"
        assert result.postal_code == "8001"
        assert result.city == "Zürich"
        assert result.numbers == ["46", "48", "50"]


class TestAPIIntegration:
    """Tests für die API-Endpunkte (ohne echten Server)."""

    @pytest.fixture
    def client(self):
        """FastAPI Test-Client."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_parse_endpoint(self, client):
        """GET /api/v1/geruestbau/address/parse"""
        response = client.get(
            "/api/v1/geruestbau/address/parse",
            params={"address": "Knospenweg 2-10, Bern"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["street"] == "Knospenweg"
        assert data["numbers"] == ["2", "4", "6", "8", "10"]
        assert data["range_type"] == "range"

    def test_parse_single_address(self, client):
        """Parse einzelne Adresse"""
        response = client.get(
            "/api/v1/geruestbau/address/parse",
            params={"address": "Bundesplatz 3, 3011 Bern"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["range_type"] == "single"
        assert len(data["numbers"]) == 1

    def test_parse_slash_notation(self, client):
        """Parse Slash-Notation"""
        response = client.get(
            "/api/v1/geruestbau/address/parse",
            params={"address": "Kramgasse 27/29, Bern"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["range_type"] == "explicit"
        assert data["numbers"] == ["27", "29"]


@pytest.mark.asyncio
class TestResolveService:
    """Tests für den resolve_to_egids Service (mit Mocking)."""

    async def test_resolve_returns_structure(self):
        """resolve_to_egids gibt korrekte Struktur zurück"""
        from app.services.address_parser import get_address_parser
        from unittest.mock import AsyncMock, patch, MagicMock

        parser = get_address_parser()

        # Mock SwisstopoService
        mock_geo_result = MagicMock()
        mock_geo_result.coordinates.lv95_e = 2600000
        mock_geo_result.coordinates.lv95_n = 1200000
        mock_geo_result.matched_address = "Knospenweg 2, 3027 Bern"

        mock_building = MagicMock()
        mock_building.egid = 1234567

        with patch.object(parser, '_get_swisstopo') as mock_swisstopo:
            mock_service = MagicMock()
            mock_service.geocode = AsyncMock(return_value=mock_geo_result)
            mock_service.identify_buildings = AsyncMock(return_value=[mock_building])
            mock_swisstopo.return_value = mock_service

            result = await parser.resolve_to_egids("Knospenweg 2, 3027 Bern")

        assert "parsed" in result
        assert "buildings" in result
        assert "errors" in result
        assert result["building_count"] >= 0

    async def test_resolve_handles_not_found(self):
        """resolve_to_egids handhabt nicht gefundene Adressen"""
        from app.services.address_parser import get_address_parser
        from unittest.mock import AsyncMock, patch, MagicMock

        parser = get_address_parser()

        with patch.object(parser, '_get_swisstopo') as mock_swisstopo:
            mock_service = MagicMock()
            mock_service.geocode = AsyncMock(return_value=None)
            mock_swisstopo.return_value = mock_service

            result = await parser.resolve_to_egids("Nicht existierende Strasse 999, Bern")

        assert result["error_count"] >= 1
        assert len(result["errors"]) >= 1
