#!/usr/bin/env python3
"""
Test-Script für den URL-Importer.

Testet verschiedene URLs von simap.ch und anderen Quellen.
"""

import asyncio
import sys
import json
from pathlib import Path

# Füge Backend zum Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.importer import url_importer, SourceType


# Test-URLs
TEST_URLS = [
    # simap.ch - Dein Beispiel
    "https://www.simap.ch/de/project-detail/7bcbe557-5b96-4b74-8fa6-9067363aa4ca",
    
    # simap.ch - Weiteres Beispiel
    "https://www.simap.ch/de/project-detail/0fdc1ae2-cf75-4a49-a0ac-b8f59d68fa6f",
    
    # Generische URL (Bern)
    # "https://www.bern.ch/politik-und-verwaltung/stadtverwaltung/tvs/stadtgruen-bern/bewirtschaftung/baumpflege/ausschreibungen",
]


async def test_source_detection():
    """Testet die Quellen-Erkennung."""
    print("\n" + "="*60)
    print("TEST: Quellen-Erkennung")
    print("="*60)
    
    test_cases = [
        ("https://www.simap.ch/de/project-detail/7bcbe557-5b96-4b74-8fa6-9067363aa4ca", SourceType.SIMAP),
        ("https://simap.ch/de/project-detail/abc123", SourceType.SIMAP),
        ("https://www.tender24.ch/ausschreibung/12345", SourceType.TENDER24),
        ("https://www.baublatt.ch/ausschreibungen/67890", SourceType.BAUBLATT),
        ("https://www.bern.ch/ausschreibungen", SourceType.GEMEINDE),
        ("https://example.com/something", SourceType.UNKNOWN),
    ]
    
    for url, expected_source in test_cases:
        source, source_id = url_importer.detect_source(url)
        status = "✅" if source == expected_source else "❌"
        print(f"{status} {url[:50]}...")
        print(f"   Erkannt: {source.value}, ID: {source_id}")
        print(f"   Erwartet: {expected_source.value}")
        print()


async def test_import(url: str):
    """Testet den Import einer URL."""
    print("\n" + "="*60)
    print(f"TEST: Import von URL")
    print(f"URL: {url}")
    print("="*60)
    
    try:
        result = await url_importer.import_from_url(url)
        
        print(f"\n✅ Import erfolgreich!")
        print(f"\nQuelle: {result.source.value}")
        print(f"Source-ID: {result.source_id}")
        print(f"\n--- Extrahierte Daten ---")
        print(f"Titel: {result.title}")
        print(f"Beschreibung: {result.description[:200] if result.description else '-'}...")
        print(f"Adresse: {result.address}")
        print(f"Ort: {result.location_city}")
        print(f"Kanton: {result.location_canton}")
        print(f"PLZ: {result.location_plz}")
        print(f"Auftraggeber: {result.client_name}")
        print(f"Eingabefrist: {result.submission_deadline}")
        print(f"Verfahrensart: {result.procedure_type}")
        print(f"Auftragsart: {result.contract_type}")
        print(f"CPV-Codes: {result.cpv_codes}")
        print(f"Geschätzter Wert: {result.estimated_value}")
        print(f"\n--- Zuschlag ---")
        print(f"Vergeben: {result.is_awarded}")
        print(f"An: {result.awarded_to}")
        print(f"Wert: {result.awarded_value}")
        print(f"Begründung: {result.award_reason}")
        print(f"\n--- Meta ---")
        print(f"Login erforderlich: {result.requires_login}")
        print(f"Notizen: {result.extraction_notes}")
        
        # Als JSON speichern
        output_file = Path(f"/tmp/import_result_{result.source_id or 'unknown'}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        print(f"\n📄 Ergebnis gespeichert: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Hauptfunktion."""
    print("\n" + "#"*60)
    print("# URL-IMPORTER TEST SUITE")
    print("#"*60)
    
    # Test 1: Quellen-Erkennung
    await test_source_detection()
    
    # Test 2: Echte Imports
    for url in TEST_URLS:
        await test_import(url)
    
    # Cleanup
    await url_importer.close()
    
    print("\n" + "#"*60)
    print("# Tests abgeschlossen")
    print("#"*60)


if __name__ == "__main__":
    asyncio.run(main())
