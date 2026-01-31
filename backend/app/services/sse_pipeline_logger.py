"""
SSE Pipeline Logger - Detailliertes Timing und Logging für die SSE-Pipeline.

NEU 30.01.2026: Zentrales Logging für die SSE-Pipeline um Konflikte
und Performance-Probleme zu analysieren.

Verwendung:
    from app.services.sse_pipeline_logger import SSEPipelineLogger

    logger = SSEPipelineLogger(address="Bundesplatz 3, Bern")
    logger.start_step("geocoding")
    # ... Geocoding durchführen ...
    logger.end_step("geocoding", {"egid": "123", "source": "swisstopo"})

    # Am Ende der Pipeline
    logger.finish()
    report = logger.get_report()
"""

import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


# Logging-Konfiguration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sse_pipeline")


@dataclass
class StepTiming:
    """Timing-Informationen für einen Pipeline-Schritt."""
    step: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "in_progress"  # in_progress, completed, failed, skipped
    error: Optional[str] = None


@dataclass
class PipelineReport:
    """Vollständiger Report einer Pipeline-Ausführung."""
    address: str
    request_id: str
    started_at: datetime
    finished_at: Optional[datetime]
    total_duration_ms: Optional[float]
    steps: List[StepTiming]
    concurrent_info: Dict[str, Any]
    warnings: List[str]
    errors: List[str]


class SSEPipelineLogger:
    """
    Logger für die SSE-Pipeline mit detailliertem Timing.

    Features:
    - Timing pro Schritt (geocoding, gwr, polygon, heights, terrain, zones, research, complete)
    - Concurrent Access Tracking (welche Tiles werden gerade geladen)
    - Warnings bei langsamen Schritten
    - Vollständiger Report am Ende

    Example:
        logger = SSEPipelineLogger("Bundesplatz 3, Bern")
        logger.start_step("geocoding")
        # ... work ...
        logger.end_step("geocoding", {"egid": "123"})
        logger.finish()
    """

    # Schwellenwerte für Warnungen (ms)
    SLOW_THRESHOLDS = {
        "geocoding": 2000,
        "gwr": 2000,
        "polygon": 5000,
        "heights": 3000,
        "terrain": 3000,
        "zones": 5000,
        "research": 10000,
        "prefetch": 10000,
        "complete": 500,
    }

    def __init__(self, address: str, request_id: Optional[str] = None):
        """
        Initialisiert den Pipeline-Logger.

        Args:
            address: Gesuchte Adresse
            request_id: Optionale Request-ID für Tracking
        """
        self.address = address
        self.request_id = request_id or f"sse-{int(time.time() * 1000)}"
        self.started_at = datetime.now()
        self.start_time = time.time()
        self.finished_at: Optional[datetime] = None

        self.steps: Dict[str, StepTiming] = {}
        self.step_order: List[str] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.concurrent_info: Dict[str, Any] = {}

        # Initial Log
        logger.info(f"[SSE-PIPELINE] {self.request_id} STARTED: {address}")

    def start_step(self, step: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Startet das Timing für einen Pipeline-Schritt.

        Args:
            step: Name des Schritts (geocoding, gwr, polygon, etc.)
            metadata: Optionale Metadaten
        """
        self.steps[step] = StepTiming(
            step=step,
            start_time=time.time(),
            metadata=metadata or {},
            status="in_progress"
        )
        self.step_order.append(step)
        logger.info(f"[SSE-PIPELINE] {self.request_id} → {step.upper()} started")

    def end_step(
        self,
        step: str,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "completed",
        error: Optional[str] = None
    ) -> float:
        """
        Beendet das Timing für einen Pipeline-Schritt.

        Args:
            step: Name des Schritts
            metadata: Optionale zusätzliche Metadaten
            status: completed, failed, skipped
            error: Fehlerdetails wenn status=failed

        Returns:
            Dauer in Millisekunden
        """
        if step not in self.steps:
            logger.warning(f"[SSE-PIPELINE] {self.request_id} Step {step} wurde nicht gestartet!")
            return 0.0

        timing = self.steps[step]
        timing.end_time = time.time()
        timing.duration_ms = round((timing.end_time - timing.start_time) * 1000, 1)
        timing.status = status
        timing.error = error

        if metadata:
            timing.metadata.update(metadata)

        # Check für langsame Schritte
        threshold = self.SLOW_THRESHOLDS.get(step, 5000)
        if timing.duration_ms > threshold:
            warning = f"{step} war langsam: {timing.duration_ms}ms (Schwellenwert: {threshold}ms)"
            self.warnings.append(warning)
            logger.warning(f"[SSE-PIPELINE] {self.request_id} ⚠️ {warning}")

        if status == "failed":
            self.errors.append(f"{step}: {error}")
            logger.error(f"[SSE-PIPELINE] {self.request_id} ✗ {step.upper()} FAILED: {error}")
        else:
            logger.info(
                f"[SSE-PIPELINE] {self.request_id} ✓ {step.upper()} "
                f"{timing.duration_ms}ms {self._format_metadata(timing.metadata)}"
            )

        return timing.duration_ms

    def skip_step(self, step: str, reason: str) -> None:
        """Markiert einen Schritt als übersprungen."""
        self.steps[step] = StepTiming(
            step=step,
            start_time=time.time(),
            end_time=time.time(),
            duration_ms=0,
            metadata={"skip_reason": reason},
            status="skipped"
        )
        self.step_order.append(step)
        logger.info(f"[SSE-PIPELINE] {self.request_id} ⊘ {step.upper()} skipped: {reason}")

    def log_concurrent_access(self, tile_id: str, action: str, details: Optional[Dict] = None) -> None:
        """
        Loggt Concurrent-Access-Informationen für Tile-Operationen.

        Args:
            tile_id: Tile-ID (z.B. "1088-22")
            action: acquire, skip, release
            details: Zusätzliche Details
        """
        if "tiles" not in self.concurrent_info:
            self.concurrent_info["tiles"] = []

        self.concurrent_info["tiles"].append({
            "tile_id": tile_id,
            "action": action,
            "timestamp": time.time(),
            "details": details or {}
        })

        logger.info(f"[SSE-PIPELINE] {self.request_id} TILE {action.upper()}: {tile_id}")

    def add_warning(self, warning: str) -> None:
        """Fügt eine Warnung hinzu."""
        self.warnings.append(warning)
        logger.warning(f"[SSE-PIPELINE] {self.request_id} ⚠️ {warning}")

    def add_error(self, error: str) -> None:
        """Fügt einen Fehler hinzu."""
        self.errors.append(error)
        logger.error(f"[SSE-PIPELINE] {self.request_id} ✗ {error}")

    def finish(self) -> None:
        """Beendet die Pipeline und gibt Summary aus."""
        self.finished_at = datetime.now()
        total_ms = round((time.time() - self.start_time) * 1000, 1)

        # Step-Timings zusammenfassen
        step_summary = []
        for step_name in self.step_order:
            timing = self.steps.get(step_name)
            if timing:
                step_summary.append(f"{step_name}={timing.duration_ms}ms")

        logger.info(
            f"[SSE-PIPELINE] {self.request_id} FINISHED in {total_ms}ms | "
            f"Steps: {', '.join(step_summary)}"
        )

        if self.warnings:
            logger.warning(f"[SSE-PIPELINE] {self.request_id} Warnings: {len(self.warnings)}")

        if self.errors:
            logger.error(f"[SSE-PIPELINE] {self.request_id} Errors: {len(self.errors)}")

    def get_report(self) -> PipelineReport:
        """Gibt den vollständigen Pipeline-Report zurück."""
        total_ms = None
        if self.finished_at:
            total_ms = round((time.time() - self.start_time) * 1000, 1)

        return PipelineReport(
            address=self.address,
            request_id=self.request_id,
            started_at=self.started_at,
            finished_at=self.finished_at,
            total_duration_ms=total_ms,
            steps=list(self.steps.values()),
            concurrent_info=self.concurrent_info,
            warnings=self.warnings,
            errors=self.errors
        )

    def get_timing_summary(self) -> Dict[str, float]:
        """Gibt eine kompakte Timing-Übersicht zurück."""
        return {
            step_name: timing.duration_ms or 0
            for step_name, timing in self.steps.items()
        }

    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Formatiert Metadaten für Log-Ausgabe."""
        if not metadata:
            return ""

        parts = []
        for key, value in metadata.items():
            if value is not None:
                # Kürze lange Werte
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                parts.append(f"{key}={value}")

        return f"({', '.join(parts)})" if parts else ""


# ============================================================================
# Integration Helper für building_data_stream.py
# ============================================================================

def create_pipeline_logger(address: str) -> SSEPipelineLogger:
    """Factory-Funktion für Pipeline-Logger."""
    return SSEPipelineLogger(address)


def log_step_timing(logger: SSEPipelineLogger, step: str, duration_ms: float, metadata: Optional[Dict] = None) -> None:
    """
    Hilfsfunktion für einfaches Step-Logging ohne start/end.

    Verwendung wenn Timing bereits gemessen wurde:
        log_step_timing(logger, "geocoding", 150, {"egid": "123"})
    """
    timing = StepTiming(
        step=step,
        start_time=time.time() - (duration_ms / 1000),
        end_time=time.time(),
        duration_ms=duration_ms,
        metadata=metadata or {},
        status="completed"
    )
    logger.steps[step] = timing
    logger.step_order.append(step)

    # Log
    threshold = SSEPipelineLogger.SLOW_THRESHOLDS.get(step, 5000)
    if duration_ms > threshold:
        logger.warnings.append(f"{step} war langsam: {duration_ms}ms")
