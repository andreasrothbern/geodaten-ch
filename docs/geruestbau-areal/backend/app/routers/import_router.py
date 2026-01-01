"""
API-Router für URL-Import.

Endpoints:
- POST /import/url - Extrahiert Daten aus URL
- POST /import/url/preview - Vorschau ohne Projekt-Erstellung
- GET /import/sources - Liste der unterstützten Quellen
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import logging

from ..services.importer import url_importer, SourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import", tags=["import"])


class URLImportRequest(BaseModel):
    """Request für URL-Import."""
    url: str
    auto_enrich: bool = True


class LocationData(BaseModel):
    """Standort-Informationen."""
    city: Optional[str] = None
    canton: Optional[str] = None
    plz: Optional[str] = None


class ClientData(BaseModel):
    """Auftraggeber-Informationen."""
    name: Optional[str] = None
    contact: Optional[str] = None


class DatesData(BaseModel):
    """Termin-Informationen."""
    submission_deadline: Optional[str] = None
    execution_start: Optional[str] = None
    execution_end: Optional[str] = None
    publication_date: Optional[str] = None


class ProcedureData(BaseModel):
    """Verfahrens-Informationen."""
    type: Optional[str] = None
    contract_type: Optional[str] = None
    cpv_codes: List[str] = []
    project_number: Optional[str] = None


class AwardData(BaseModel):
    """Zuschlags-Informationen."""
    is_awarded: bool = False
    awarded_to: Optional[str] = None
    awarded_value: Optional[str] = None
    award_reason: Optional[str] = None


class ExtractedDataResponse(BaseModel):
    """Extrahierte Projektdaten."""
    title: str
    description: Optional[str] = None
    address: Optional[str] = None
    location: LocationData
    client: ClientData
    dates: DatesData
    procedure: ProcedureData
    award: AwardData
    estimated_value: Optional[str] = None


class URLImportResponse(BaseModel):
    """Response für URL-Import."""
    success: bool
    source: str
    source_url: str
    source_id: Optional[str] = None
    data: Optional[ExtractedDataResponse] = None
    requires_login: bool = False
    extraction_notes: List[str] = []
    error: Optional[str] = None


class SourceInfo(BaseModel):
    """Information über eine Quelle."""
    id: str
    name: str
    description: str
    example_url: str
    search_url: Optional[str] = None


# Quellen-Informationen
SOURCES = [
    SourceInfo(
        id="simap",
        name="simap.ch",
        description="Offizielle Schweizer Ausschreibungsplattform (Bund, Kantone, Gemeinden)",
        example_url="https://www.simap.ch/de/project-detail/{uuid}",
        search_url='https://www.simap.ch/de?cpvCodes=["44212310","45262100"]&newestPubTypes=["tender"]&orderAddressCountryOnlySwitzerland=true'
    ),
    SourceInfo(
        id="tender24",
        name="tender24.ch",
        description="Private Ausschreibungsplattform",
        example_url="https://www.tender24.ch/ausschreibung/{id}",
        search_url="https://www.tender24.ch/Search?searchText=gerüst"
    ),
    SourceInfo(
        id="baublatt",
        name="baublatt.ch",
        description="Baubranche News und Ausschreibungen",
        example_url="https://www.baublatt.ch/ausschreibungen/{id}",
        search_url="https://www.baublatt.ch/ausschreibungen"
    ),
    SourceInfo(
        id="gemeinde",
        name="Gemeinde-Websites",
        description="Direkte Ausschreibungen von Gemeinden und Kantonen",
        example_url="https://www.bern.ch/ausschreibungen/...",
        search_url=None
    ),
    SourceInfo(
        id="unknown",
        name="Andere Webseiten",
        description="Beliebige URLs mit automatischer Datenextraktion",
        example_url="https://example.ch/...",
        search_url=None
    ),
]


@router.get("/sources", response_model=List[SourceInfo])
async def get_sources():
    """
    Gibt Liste der unterstützten Quellen zurück.
    
    Enthält für jede Quelle:
    - Name und Beschreibung
    - Beispiel-URL
    - Such-URL (falls vorhanden)
    """
    return SOURCES


@router.get("/sources/search-links")
async def get_search_links():
    """
    Gibt die Such-Links für Gerüstbau-Ausschreibungen zurück.
    
    Diese Links können direkt in der App angezeigt werden.
    """
    return {
        "simap_geruestbau": 'https://www.simap.ch/de?cpvCodes=["44212310","45262100"]&newestPubTypes=["tender"]&orderAddressCountryOnlySwitzerland=true',
        "simap_bern": 'https://www.simap.ch/de?cpvCodes=["44212310","45262100"]&orderAddressCantons=["BE"]&orderAddressCountryOnlySwitzerland=true',
        "tender24": "https://www.tender24.ch/Search?searchText=gerüst",
        "baublatt": "https://www.baublatt.ch/ausschreibungen",
    }


@router.post("/url", response_model=URLImportResponse)
async def import_from_url(url: str = Query(..., description="URL der Ausschreibung")):
    """
    Extrahiert Projektdaten aus einer URL.
    
    Unterstützte Quellen:
    - simap.ch (offizielle Ausschreibungen)
    - tender24.ch
    - baublatt.ch
    - Gemeinde-Websites
    - Beliebige URLs (generische Extraktion)
    
    Die Daten werden extrahiert aber noch kein Projekt erstellt.
    """
    try:
        extracted = await url_importer.import_from_url(url)
        
        return URLImportResponse(
            success=True,
            source=extracted.source.value,
            source_url=extracted.source_url,
            source_id=extracted.source_id,
            requires_login=extracted.requires_login,
            extraction_notes=extracted.extraction_notes,
            data=ExtractedDataResponse(
                title=extracted.title,
                description=extracted.description,
                address=extracted.address,
                location=LocationData(
                    city=extracted.location_city,
                    canton=extracted.location_canton,
                    plz=extracted.location_plz,
                ),
                client=ClientData(
                    name=extracted.client_name,
                    contact=extracted.client_contact,
                ),
                dates=DatesData(
                    submission_deadline=extracted.submission_deadline,
                    execution_start=extracted.execution_start,
                    execution_end=extracted.execution_end,
                    publication_date=extracted.publication_date,
                ),
                procedure=ProcedureData(
                    type=extracted.procedure_type,
                    contract_type=extracted.contract_type,
                    cpv_codes=extracted.cpv_codes,
                    project_number=extracted.project_number,
                ),
                award=AwardData(
                    is_awarded=extracted.is_awarded,
                    awarded_to=extracted.awarded_to,
                    awarded_value=extracted.awarded_value,
                    award_reason=extracted.award_reason,
                ),
                estimated_value=extracted.estimated_value,
            )
        )
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return URLImportResponse(
            success=False,
            source="error",
            source_url=url,
            error=str(e),
            extraction_notes=[f"Fehler: {str(e)}"]
        )


@router.post("/url/detect-source")
async def detect_source(url: str = Query(..., description="URL zum Analysieren")):
    """
    Erkennt die Quelle einer URL ohne Daten zu extrahieren.
    
    Nützlich für UI-Feedback bevor der Import gestartet wird.
    """
    source, source_id = url_importer.detect_source(url)
    
    source_info = next((s for s in SOURCES if s.id == source.value), None)
    
    return {
        "source": source.value,
        "source_id": source_id,
        "source_name": source_info.name if source_info else "Unbekannt",
        "source_description": source_info.description if source_info else None,
    }
