"""
Tender/Ausschreibungs-Extrahierung
===================================

Extrahiert strukturierte Daten aus Ausschreibungs-PDFs und Fotos
mittels Claude Vision API.

Verwendung:
    from app.services.geruestbau.tender_extractor import TenderExtractor

    extractor = TenderExtractor()
    result = await extractor.extract_from_file(file_bytes, filename)

Stand: 31.12.2025
"""

import os
import base64
import logging
import json
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from io import BytesIO

logger = logging.getLogger(__name__)

# Model for extraction
EXTRACTION_MODEL = "claude-sonnet-4-20250514"


@dataclass
class ExtractionResult:
    """Ergebnis der Dokumenten-Extraktion"""
    success: bool = False
    confidence: float = 0.0
    raw_text: Optional[str] = None
    error: Optional[str] = None

    # Extrahierte Daten
    project_name: Optional[str] = None
    address: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    description: Optional[str] = None
    tender_number: Optional[str] = None
    submission_deadline: Optional[str] = None  # ISO format YYYY-MM-DD
    project_start: Optional[str] = None
    project_end: Optional[str] = None
    estimated_area_m2: Optional[float] = None
    requirements: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu API-Response-Format"""
        return {
            "success": self.success,
            "confidence": self.confidence,
            "raw_text": self.raw_text,
            "error": self.error,
            "data": {
                "project_name": self.project_name,
                "address": self.address,
                "client_name": self.client_name,
                "client_contact": self.client_contact,
                "description": self.description,
                "tender_number": self.tender_number,
                "submission_deadline": self.submission_deadline,
                "project_start": self.project_start,
                "project_end": self.project_end,
                "estimated_area_m2": self.estimated_area_m2,
                "requirements": self.requirements,
            } if self.success else None
        }


class TenderExtractor:
    """Service für die Extraktion von Ausschreibungsdaten"""

    EXTRACTION_PROMPT = """
Du bist ein Experte für die Analyse von Bauausschreibungen und Gerüstbau-Projekten.

Analysiere das hochgeladene Dokument (Ausschreibung, Offertanfrage, Baugesuch o.ä.) und extrahiere alle relevanten Informationen für ein Gerüstbau-Projekt.

WICHTIG:
- Extrahiere nur Informationen, die explizit im Dokument stehen
- Wenn eine Information nicht vorhanden ist, setze den Wert auf null
- Datumsangaben müssen im Format YYYY-MM-DD sein (z.B. 2025-03-01)
- Für Schweizer Adressen: Format "Strasse Nr, PLZ Ort"
- Schätze die Gerüstfläche nur, wenn Masse angegeben sind

Antworte im folgenden JSON-Format (NUR das JSON, keine weitere Erklärung):

```json
{
    "project_name": "Name des Projekts oder kurze Beschreibung",
    "address": "Strasse Nr, PLZ Ort",
    "client_name": "Name des Auftraggebers / Bauherrn",
    "client_contact": "Telefon oder E-Mail falls vorhanden",
    "description": "Kurze Beschreibung der Gerüstarbeiten",
    "tender_number": "Ausschreibungs-Nummer falls vorhanden",
    "submission_deadline": "YYYY-MM-DD",
    "project_start": "YYYY-MM-DD",
    "project_end": "YYYY-MM-DD",
    "estimated_area_m2": 0,
    "requirements": ["Liste", "spezieller", "Anforderungen"],
    "confidence": 0.85
}
```

Setze confidence zwischen 0.0 und 1.0:
- 1.0: Alle Daten klar lesbar
- 0.8: Die meisten Daten gefunden
- 0.5: Einige wichtige Daten fehlen oder sind unklar
- 0.3: Nur wenige Daten extrahierbar
"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy-load Anthropic client"""
        if self._client is None:
            try:
                from anthropic import Anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    logger.warning("ANTHROPIC_API_KEY nicht gesetzt")
                    return None
                self._client = Anthropic(api_key=api_key)
            except ImportError:
                logger.warning("anthropic package nicht installiert")
                return None
        return self._client

    def _is_pdf(self, filename: str) -> bool:
        """Prüft ob Datei ein PDF ist"""
        return filename.lower().endswith('.pdf')

    def _is_image(self, filename: str) -> bool:
        """Prüft ob Datei ein Bild ist"""
        return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))

    def _get_media_type(self, filename: str) -> str:
        """Bestimmt den MIME-Type"""
        ext = filename.lower().split('.')[-1]
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'pdf': 'application/pdf',
        }
        return mime_types.get(ext, 'application/octet-stream')

    async def extract_from_file(
        self,
        file_bytes: bytes,
        filename: str
    ) -> ExtractionResult:
        """
        Extrahiert Daten aus einer Datei (PDF oder Bild).

        Args:
            file_bytes: Dateiinhalt als Bytes
            filename: Originaler Dateiname (für Typ-Erkennung)

        Returns:
            ExtractionResult mit extrahierten Daten
        """
        client = self._get_client()

        if not client:
            return ExtractionResult(
                success=False,
                error="Claude API nicht verfügbar (ANTHROPIC_API_KEY fehlt)"
            )

        try:
            # Prepare content based on file type
            if self._is_pdf(filename):
                content = await self._extract_from_pdf(client, file_bytes)
            elif self._is_image(filename):
                content = await self._extract_from_image(client, file_bytes, filename)
            else:
                return ExtractionResult(
                    success=False,
                    error=f"Nicht unterstütztes Dateiformat: {filename}"
                )

            return content

        except Exception as e:
            logger.exception(f"Fehler bei Extraktion: {e}")
            return ExtractionResult(
                success=False,
                error=f"Fehler bei der Analyse: {str(e)}"
            )

    async def _extract_from_pdf(
        self,
        client,
        file_bytes: bytes
    ) -> ExtractionResult:
        """Extrahiert Daten aus PDF mittels Claude"""
        # Encode PDF as base64
        pdf_base64 = base64.standard_b64encode(file_bytes).decode('utf-8')

        # Call Claude with PDF
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": self.EXTRACTION_PROMPT
                        }
                    ]
                }
            ]
        )

        return self._parse_response(response)

    async def _extract_from_image(
        self,
        client,
        file_bytes: bytes,
        filename: str
    ) -> ExtractionResult:
        """Extrahiert Daten aus Bild mittels Claude Vision"""
        # Encode image as base64
        image_base64 = base64.standard_b64encode(file_bytes).decode('utf-8')
        media_type = self._get_media_type(filename)

        # Call Claude with image
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": self.EXTRACTION_PROMPT
                        }
                    ]
                }
            ]
        )

        return self._parse_response(response)

    def _parse_response(self, response) -> ExtractionResult:
        """Parst die Claude-Response und erstellt ExtractionResult"""
        try:
            # Get text content from response
            text_content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    text_content += block.text

            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', text_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to parse the whole response as JSON
                json_str = text_content.strip()

            data = json.loads(json_str)

            # Build result
            result = ExtractionResult(
                success=True,
                confidence=data.get('confidence', 0.5),
                raw_text=text_content,
                project_name=data.get('project_name'),
                address=data.get('address'),
                client_name=data.get('client_name'),
                client_contact=data.get('client_contact'),
                description=data.get('description'),
                tender_number=data.get('tender_number'),
                submission_deadline=data.get('submission_deadline'),
                project_start=data.get('project_start'),
                project_end=data.get('project_end'),
                estimated_area_m2=data.get('estimated_area_m2'),
                requirements=data.get('requirements', []),
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Fehler: {e}")
            return ExtractionResult(
                success=False,
                confidence=0.0,
                raw_text=text_content if 'text_content' in dir() else None,
                error="Antwort konnte nicht als JSON geparst werden"
            )


# Singleton instance
_extractor_instance = None


def get_tender_extractor() -> TenderExtractor:
    """Gibt Singleton-Instanz des TenderExtractors zurück"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = TenderExtractor()
    return _extractor_instance
