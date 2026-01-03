#!/usr/bin/env python
"""Test script for the refactored swissBUILDINGS3D service."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.swissbuildings3d_service import get_swissbuildings3d_service
from app.services.swisstopo import SwisstopoService


async def test_service():
    """Test the refactored service."""
    print("=" * 60)
    print("Testing refactored swissBUILDINGS3D service")
    print("=" * 60)

    # 1. Geocode address
    print("\n1. Geocoding 'Kramgasse 10, 3011 Bern'...")
    swisstopo = SwisstopoService()
    geo = await swisstopo.geocode("Kramgasse 10, 3011 Bern")

    if not geo:
        print("   ERROR: Geocoding failed!")
        return

    e, n = geo.coordinates.lv95_e, geo.coordinates.lv95_n
    print(f"   OK: E={e}, N={n}")

    # 2. Get building data
    print("\n2. Getting building data from swissBUILDINGS3D service...")
    service = get_swissbuildings3d_service()
    building = await service.get_building_by_coordinates(e, n)

    if not building:
        print("   ERROR: No building found!")
        return

    print(f"   EGID: {building.egid}")
    print(f"   Polygon: {len(building.polygon)} points (ORIGINAL)")
    print(f"   Polygon Point Count: {building.polygon_point_count}")
    print(f"   Sides from Simplified: {building.sides_from_simplified}")
    print(f"   Traufhöhe: {building.trauf_height_m} m")
    print(f"   Firsthöhe: {building.first_height_m} m")
    print(f"   Height Source: {building.height_source}")
    print(f"   Roof Type: {building.roof_type}")
    print(f"   Sides: {len(building.sides)}")
    print(f"   Confidence: {building.confidence}")

    # 3. Summary
    print("\n" + "=" * 60)
    if building.polygon and len(building.polygon) > 0:
        print("✅ SUCCESS: Original polygon preserved!")
        print(f"   Original Points: {len(building.polygon)}")
        print(f"   Sides calculated from simplified polygon: {building.sides_from_simplified}")
    else:
        print("⚠️  WARNING: No polygon found")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_service())
