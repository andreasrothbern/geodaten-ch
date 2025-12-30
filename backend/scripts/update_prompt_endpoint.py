#!/usr/bin/env python3
"""Update /api/v1/prompt/generate endpoint to use SmartBuildingService"""

import re

def main():
    with open('C:/Users/vonro/projects/lawil/geodaten-ch/backend/app/main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the endpoint using regex
    pattern = r'(@app\.get\("/api/v1/prompt/generate".*?async def generate_claude_prompt\(.*?\):.*?""".*?""".*?try:.*?from app\.services\.prompts import get_prompt_builder.*?except HTTPException:.*?raise.*?except Exception as e:.*?raise HTTPException\(status_code=500, detail=str\(e\)\))'

    new_endpoint = '''@app.get("/api/v1/prompt/generate",
         tags=["Prompt Generation"],
         summary="Generiert Claude-Prompt für SVG-Erstellung")
async def generate_claude_prompt(
    address: str,
    svg_type: str = Query("all", description="SVG-Typ: all, grundriss, ansicht, schnitt"),
    include_research: bool = Query(True, description="Dynamische Claude-Recherche durchführen"),
    force_refresh: bool = Query(False, description="Cache ignorieren")
):
    """
    Generiert einen strukturierten Prompt für Claude SVG-Generierung.

    Verwendet SmartBuildingService + UnifiedPromptGenerator für
    IDENTISCHE Prompts bei Export und automatischer SVG-Generierung.

    **Features:**
    - 10-Schritte Datenpipeline (Geocoding, GWR, Höhen, Terrain, etc.)
    - Automatische Turm-Erkennung bei extremer Höhendifferenz
    - Dynamische Gebäude-Recherche via Claude API (gecacht)
    - Höhenzonen für komplexe Gebäude

    **Kosten:**
    - Gecachtes Bundle: $0.00
    - Neues Bundle mit Recherche: ca. $0.01-0.02

    **Verwendung:**
    - Frontend Export-Button → Clipboard → Claude.ai
    - Backend SVG-Generierung → Identischer Prompt
    """
    try:
        from app.services.smart_building import get_smart_building_service, get_prompt_generator, SVGType

        # SVG-Typ parsen
        svg_type_enum = SVGType.ALL
        if svg_type.lower() == "grundriss":
            svg_type_enum = SVGType.GRUNDRISS
        elif svg_type.lower() == "ansicht":
            svg_type_enum = SVGType.ANSICHT
        elif svg_type.lower() == "schnitt":
            svg_type_enum = SVGType.SCHNITT

        # Daten sammeln via SmartBuildingService
        service = get_smart_building_service()
        bundle = await service.collect_all_data(
            address=address,
            force_refresh=force_refresh,
            include_research=include_research,
            include_zones_analysis=True,
            include_terrain=True
        )

        if not bundle.address_matched:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        # Prompt generieren via UnifiedPromptGenerator
        generator = get_prompt_generator()
        prompt = generator.generate(
            bundle=bundle,
            svg_type=svg_type_enum,
            include_style_guide=True
        )

        return {
            "prompt": prompt,
            "address": bundle.address_matched,
            "egid": bundle.egid,
            "svg_type": svg_type,
            "research_included": include_research,
            "complexity": bundle.complexity,
            "zones_count": len(bundle.zones),
            "building_type": bundle.building_type,
            "data_sources": [s.value for s in bundle.data_sources]
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))'''

    # Simple approach: find the start and end markers
    start_marker = '@app.get("/api/v1/prompt/generate",'
    end_marker = '@app.get("/api/v1/prompt/research/stats",'

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx != -1 and end_idx != -1:
        # Replace everything between start and end
        content = content[:start_idx] + new_endpoint + "\n\n\n" + content[end_idx:]

        with open('C:/Users/vonro/projects/lawil/geodaten-ch/backend/app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("OK: /api/v1/prompt/generate endpoint updated")
    else:
        print(f"ERROR: Could not find markers. start={start_idx}, end={end_idx}")

if __name__ == "__main__":
    main()
