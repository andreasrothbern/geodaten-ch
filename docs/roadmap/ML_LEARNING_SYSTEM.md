# ML Learning System - Roadmap

> **Status:** Geplant
> **Prioritaet:** Hoch
> **Branch:** `feature/ml-learning-system` (noch nicht erstellt)
> **Erstellt:** 30.12.2025

---

## Executive Summary

Implementierung eines Machine Learning Systems zur automatischen Zonen-Erkennung bei Gebaeuden. Das System lernt aus Claude.ai-Analysen und ersetzt schrittweise die teuren API-Calls.

---

## Problem

| Aktuell | Ziel |
|---------|------|
| Bekannte Gebaeude: manuell in `known_buildings.py` | Automatisch gelernt |
| Unbekannte Gebaeude: Claude API ($0.05-0.15, 10-20s) | ML-Modell (<10ms, kostenlos) |
| Keine Skalierung | 1000+ Gebaeude |

---

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                    ML LEARNING SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PHASE 1: Datensammlung (0-500 Gebaeude)                        │
│  ─────────────────────────────────────────                      │
│  - TrainingDataCollector Service                                 │
│  - Few-Shot mit Claude fuer Zonen-Analyse                       │
│  - Speicherung in training_data.parquet                         │
│  - Manuelles Review fuer Qualitaetssicherung                    │
│                                                                  │
│  PHASE 2: ML-Training (500+ Gebaeude)                           │
│  ─────────────────────────────────────────                      │
│  - XGBoost / Random Forest Classifier                           │
│  - Multi-Label: zone_template Vorhersage                        │
│  - Cross-Validation + Claude-Review                             │
│  - Modell-Export: model.joblib                                  │
│                                                                  │
│  PHASE 3: Production (1000+ Gebaeude)                           │
│  ─────────────────────────────────────────                      │
│  - ML-Inference fuer 95% der Anfragen                           │
│  - Claude nur bei confidence < 0.8                              │
│  - Kontinuierliches Lernen aus Korrekturen                      │
│  - A/B Testing: ML vs. Claude                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features (Input fuer ML)

| Feature | Quelle | Typ | Beschreibung |
|---------|--------|-----|--------------|
| `gkat` | GWR | Categorical | Gebaeudekategorie (1020, 1030, etc.) |
| `traufhoehe_m` | swissBUILDINGS3D | Numeric | Traufhoehe in Metern |
| `firsthoehe_m` | swissBUILDINGS3D | Numeric | Firsthoehe in Metern |
| `height_diff` | Berechnet | Numeric | First - Traufe |
| `polygon_points` | geodienste.ch | Numeric | Anzahl Polygon-Punkte |
| `area_m2` | geodienste.ch | Numeric | Grundflaeche |
| `perimeter_m` | geodienste.ch | Numeric | Umfang |
| `aspect_ratio` | Berechnet | Numeric | Breite / Tiefe |
| `baujahr` | GWR | Numeric | Baujahr |
| `geschosse` | GWR | Numeric | Anzahl Geschosse |

---

## Target (Output)

```python
ZONE_TEMPLATES = {
    # Einfache Gebaeude
    "wohnhaus_einfach": [
        {"type": "hauptgebaeude", "height_factor": 1.0}
    ],
    "wohnhaus_mit_anbau": [
        {"type": "hauptgebaeude", "height_factor": 1.0},
        {"type": "anbau", "height_factor": 0.6}
    ],

    # Kirchen
    "kirche_mit_turm": [
        {"type": "hauptgebaeude", "height_factor": 0.5},
        {"type": "anbau", "height_factor": 0.3},
        {"type": "turm", "height_factor": 1.0, "sonderkonstruktion": True}
    ],

    # Oeffentliche Gebaeude
    "parlament_kuppel": [
        {"type": "arkade", "height_factor": 0.1},
        {"type": "hauptgebaeude", "height_factor": 0.5},
        {"type": "kuppel", "height_factor": 1.0, "sonderkonstruktion": True}
    ],

    "museum_komplex": [
        {"type": "hauptgebaeude", "height_factor": 0.7},
        {"type": "anbau", "height_factor": 0.5},
        {"type": "turm", "height_factor": 1.0}
    ],

    # Weitere Templates...
}
```

---

## Dateien (geplant)

```
backend/app/services/ml/
├── __init__.py
├── collector.py          # TrainingDataCollector
├── trainer.py            # ML-Training Pipeline
├── predictor.py          # ML-Inference Service
├── templates.py          # Zone-Templates Definition
└── models/
    └── zone_classifier.joblib  # Trainiertes Modell

backend/data/
├── training_data.parquet       # Trainingsdaten
├── validation_data.parquet     # Validierungsdaten
└── model_metrics.json          # Modell-Performance
```

---

## API-Endpunkte (geplant)

```python
# Trainingsdaten sammeln
POST /api/v1/ml/collect
    ?address=Bundesplatz 3, Bern
    &verify=true  # Manuelles Review erforderlich

# Modell trainieren
POST /api/v1/ml/train
    ?min_samples=500
    &test_size=0.2

# Vorhersage
GET /api/v1/ml/predict
    ?address=...
    # Response: {template: "kirche_mit_turm", confidence: 0.92}

# Statistiken
GET /api/v1/ml/stats
    # Response: {samples: 847, accuracy: 0.89, templates: {...}}
```

---

## Kosten-Vergleich

| Szenario | Claude API | ML-Modell |
|----------|------------|-----------|
| 1 Gebaeude | $0.05-0.15 | $0.00 |
| 100 Gebaeude | $5-15 | $0.00 |
| 1000 Gebaeude | $50-150 | $0.00 |
| 10000 Gebaeude | $500-1500 | $0.00 |

**Training-Kosten (einmalig):**
- Datensammlung: ~$25-50 (500 Gebaeude × $0.05-0.10)
- Training: Compute-Zeit, minimal

---

## Abhaengigkeiten

```
# requirements.txt (neu)
scikit-learn>=1.3.0
xgboost>=2.0.0
pandas>=2.0.0
pyarrow>=14.0.0  # fuer parquet
joblib>=1.3.0
```

---

## Meilensteine

| Phase | Meilenstein | Kriterium | Status |
|-------|-------------|-----------|--------|
| 0 | Bugs beheben | Alle bekannten Bugs gefixt | Ausstehend |
| 1a | TrainingDataCollector | 50 Gebaeude gesammelt | Ausstehend |
| 1b | Datenqualitaet | 90% manuell validiert | Ausstehend |
| 1c | 500 Gebaeude | Trainingsdaten komplett | Ausstehend |
| 2a | Modell v1 | Accuracy > 80% | Ausstehend |
| 2b | Modell v2 | Accuracy > 90% | Ausstehend |
| 3a | Production | ML fuer 50% der Anfragen | Ausstehend |
| 3b | Full ML | ML fuer 95% der Anfragen | Ausstehend |

---

## Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Zu wenig Trainingsdaten | Mittel | Hoch | Mehr Staedte einbeziehen |
| Schlechte Modell-Qualitaet | Mittel | Hoch | Claude als Fallback behalten |
| Overfitting auf Bern | Hoch | Mittel | Daten aus anderen Kantonen |
| Edge Cases | Hoch | Niedrig | Claude fuer komplexe Faelle |

---

## Naechste Schritte

1. **Bugs beheben** (aktuell)
   - Siehe `docs/roadmap/CURRENT_BUGS.md`

2. **Feature-Branch erstellen**
   ```bash
   git checkout -b feature/ml-learning-system
   ```

3. **Phase 1a implementieren**
   - TrainingDataCollector Service
   - Erste 50 Gebaeude sammeln

---

*Dokument erstellt: 30.12.2025*
*Autor: Claude Code + User*
