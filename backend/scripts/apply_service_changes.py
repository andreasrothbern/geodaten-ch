#!/usr/bin/env python
"""Apply BUG-011 and BUG-012 fixes to service.py"""

import os

SERVICE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "app",
    "services",
    "smart_building",
    "service.py"
)

# Read file
with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"File read, length: {len(content)}")

changes_made = 0

# 1. Fix Haiku -> Sonnet in docstring
if 'Claude Haiku)' in content:
    content = content.replace('Claude Haiku)', 'Claude Sonnet)')
    print("1. Fixed: Haiku -> Sonnet in docstring")
    changes_made += 1

# 2. Add import after models import
old_import = '''from .models import (
    BuildingDataBundle,
    DataSource,
    DataQuality,
    ZoneInfo,
    TerrainProfile,
    AccessPoint,
)'''

new_import = '''from .models import (
    BuildingDataBundle,
    DataSource,
    DataQuality,
    ZoneInfo,
    TerrainProfile,
    AccessPoint,
)
from .validation import validate_heights, validate_zone_consistency'''

if old_import in content and 'from .validation import' not in content:
    content = content.replace(old_import, new_import)
    print("2. Added: validation import")
    changes_made += 1

# 3. Add validation calls after Phase 2
old_phase2 = '''await asyncio.gather(*phase2_tasks, return_exceptions=True)
            logger.info(f"Phase 2 complete: GWR, Heights, Polygon, Terrain")

            # PHASE 3: Parallel'''

new_phase2 = '''await asyncio.gather(*phase2_tasks, return_exceptions=True)
            logger.info(f"Phase 2 complete: GWR, Heights, Polygon, Terrain")

            # VALIDIERUNG: Höhen-Plausibilität prüfen (BUG-011)
            validate_heights(bundle)

            # PHASE 3: Parallel'''

if old_phase2 in content and 'validate_heights(bundle)' not in content:
    content = content.replace(old_phase2, new_phase2)
    print("3. Added: validate_heights call after Phase 2")
    changes_made += 1

# 4. Add zone validation after Phase 4
old_phase4 = '''else:
                self._create_default_zone(bundle)

            # PHASE 5: Berechnungen'''

new_phase4 = '''else:
                self._create_default_zone(bundle)

            # VALIDIERUNG: Zone/API-Konsistenz prüfen (BUG-012)
            validate_zone_consistency(bundle)

            # PHASE 5: Berechnungen'''

if old_phase4 in content and 'validate_zone_consistency(bundle)' not in content:
    content = content.replace(old_phase4, new_phase4)
    print("4. Added: validate_zone_consistency call after Phase 4")
    changes_made += 1

# Write file
with open(SERVICE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nDone! {changes_made} changes applied to service.py")
