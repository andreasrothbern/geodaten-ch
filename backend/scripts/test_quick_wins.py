#!/usr/bin/env python3
"""Test Quick Wins Implementation"""

import sys
sys.path.insert(0, r'C:\Users\vonro\projects\lawil\geodaten-ch\backend')

from app.services.smart_building.prompt_generator import UnifiedPromptGenerator, get_prompt_generator
from app.services.smart_building.models import BuildingDataBundle, ZoneInfo

def test_quick_wins():
    """Test all Quick Win implementations"""
    print("Testing Quick Wins Implementation...")
    print("=" * 50)

    # Test: Instanz erstellen
    gen = get_prompt_generator()
    print(f"[OK] UnifiedPromptGenerator erstellt")

    # Test: Konstanten pruefen
    print(f"[OK] ViewBox: {gen.VIEWBOX_WIDTH}x{gen.VIEWBOX_HEIGHT}")
    print(f"[OK] Offsets: L={gen.OFFSET_LEFT}, B={gen.OFFSET_BOTTOM}, R={gen.OFFSET_RIGHT}, T={gen.OFFSET_TOP}")

    # Test: Einfaches Bundle
    bundle = BuildingDataBundle(
        address_input='Teststrasse 1',
        address_matched='Teststrasse 1, 3000 Bern',
        complexity='simple',
        zones=[],
    )
    bundle.traufhoehe_m = 12.0
    bundle.firsthoehe_m = 15.0
    bundle.bbox_width_m = 20.0

    # Test: Proportionen-Section (Quick Win #1)
    props = gen._proportions_section(bundle)
    assert "## 10. Proportionen" in props, "Proportionen-Section fehlt!"
    assert "Massstab" in props, "Massstab fehlt!"
    print("[OK] Quick Win #1: Proportionen-Section generiert")

    # Test: Scaffolding-Section (Quick Win #3)
    scaff = gen._scaffolding_spec_section()
    assert "## 11." in scaff and "Spezifikation" in scaff, "Scaffolding-Section fehlt!"
    assert "2.57m" in scaff, "Feldbreite fehlt!"
    assert "2.0m" in scaff, "Lagenhoehe fehlt!"
    assert "Layher Blitz" in scaff, "System-Name fehlt!"
    print("[OK] Quick Win #3: Geruest-Spezifikation generiert")

    # Test: Innenhof-BoundingBox (Quick Win #4)
    # Braucht U-Form Polygon zum Testen
    courtyard = gen._calculate_courtyard_bbox(bundle)
    print("[OK] Quick Win #4: Innenhof-Berechnung vorhanden (braucht U-Form Polygon)")

    # Test: Full Prompt Generation
    from app.services.smart_building.prompt_generator import SVGType
    prompt = gen.generate(bundle, svg_type=SVGType.ALL)

    assert "## 10. Proportionen" in prompt, "Proportionen fehlt im Prompt!"
    assert "## 11." in prompt and "Spezifikation" in prompt, "Geruest-Spezifikation fehlt im Prompt!"
    assert "## 12. SVG Style-Vorgaben" in prompt, "Style-Guide fehlt!"
    assert "## 13. Anforderungen pro SVG" in prompt, "Anforderungen fehlt!"
    assert "## 14. Output" in prompt, "Output fehlt!"
    print("[OK] Vollstaendiger Prompt mit allen Quick Wins generiert")

    print("=" * 50)
    print("ALLE TESTS BESTANDEN!")
    return True

if __name__ == "__main__":
    test_quick_wins()
