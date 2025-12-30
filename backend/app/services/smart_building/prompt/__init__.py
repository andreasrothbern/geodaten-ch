# backend/app/services/smart_building/prompt/__init__.py
"""
Prompt-Templates fuer SVG-Generierung.

Dieses Modul enthaelt:
- base_template.md: Haupt-Vorlage fuer Claude SVG-Generierung
- sections/: Aufgeteilte Template-Abschnitte

Die Templates werden vom UnifiedPromptGenerator verwendet.
"""

from pathlib import Path

# Pfad zu diesem Modul
PROMPTS_DIR = Path(__file__).parent
SECTIONS_DIR = PROMPTS_DIR / "sections"


def get_template_path(name: str) -> Path:
    """Gibt den Pfad zu einem Template zurueck."""
    return PROMPTS_DIR / name


def get_section_path(name: str) -> Path:
    """Gibt den Pfad zu einem Section-Template zurueck."""
    return SECTIONS_DIR / name


def load_template(name: str) -> str:
    """Laedt ein Template als String."""
    path = get_template_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Template nicht gefunden: {path}")
    return path.read_text(encoding="utf-8")


def load_section(name: str) -> str:
    """Laedt ein Section-Template als String."""
    path = get_section_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Section nicht gefunden: {path}")
    return path.read_text(encoding="utf-8")
