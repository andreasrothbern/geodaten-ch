# DuckDB Regeln (Stand 13.01.2026 18:55)

## WICHTIG: Connection-Factory verwenden!

**NIEMALS** direktes `duckdb.connect()` verwenden!

```python
# ❌ FALSCH - Connection-Konflikt möglich!
import duckdb
conn = duckdb.connect("building_3d.duckdb")

# ✅ RICHTIG - Zentrale Factory aus config.py
from app.config import get_building_3d_connection
conn = get_building_3d_connection()  # Für Schreibzugriff
conn = get_building_3d_connection(read_only=True)  # Für Lesezugriff
```

**Warum?** DuckDB erlaubt keine unterschiedlichen Konfigurationen für Connections zur gleichen DB-Datei. Die Factory stellt konsistente Einstellungen sicher.

## WICHTIG: current_timestamp statt datetime()!

**NIEMALS** `datetime('now')` in SQL verwenden - das ist SQLite-Syntax!

```sql
-- ❌ FALSCH (SQLite-Syntax, DuckDB Fehler!)
VALUES (?, ?, datetime('now'))

-- ✅ RICHTIG (DuckDB-kompatibel)
VALUES (?, ?, current_timestamp)
```

**Warum?** DuckDB kennt die SQLite-Funktion `datetime()` nicht. `current_timestamp` funktioniert in beiden Engines.

## SQL-Syntax-Unterschiede

| Feature | SQLite | DuckDB |
|---------|--------|--------|
| Timestamp | `datetime('now')` | `current_timestamp` |
| Auto-Increment | `AUTOINCREMENT` | `SEQUENCE` |
| JSON-Typ | `TEXT` | `JSON` (nativ) |
| Float | `REAL` | `DOUBLE` |
| String | `TEXT` | `VARCHAR` |

## Typ-Mappings (aus building_3d_schema.py)

```python
SQLITE_TYPES = {
    "json_type": "TEXT",
    "float_type": "REAL",
    "text_type": "TEXT",
    "timestamp_type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "blob_type": "BLOB",
}

DUCKDB_TYPES = {
    "json_type": "JSON",  # Native JSON-Unterstützung!
    "float_type": "DOUBLE",
    "text_type": "VARCHAR",
    "timestamp_type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "blob_type": "BLOB",
}
```

## Row-Handling

DuckDB gibt Tuples zurück, SQLite mit `row_factory` gibt Row-Objekte zurück:

```python
row = cursor.fetchone()

# DuckDB: Tuple
if isinstance(row, tuple):
    result = {'egid': row[0], 'polygon': row[1]}
# SQLite: Row mit dict-like Zugriff
else:
    result = dict(row)
```

## Context Manager

DuckDB Connections unterstützen `with`:

```python
# ✅ Funktioniert mit beiden Engines
with get_building_3d_connection() as conn:
    conn.execute("SELECT * FROM buildings_3d")
```

## Betroffene Dateien

| Datei | Funktion |
|-------|----------|
| `config.py` | `get_building_3d_connection()` - Factory |
| `building_3d_service.py` | Haupt-Service |
| `building_3d_schema.py` | Schema-Definitionen |
| `roof_3d_service.py` | Dach-Daten |

## Bei Fehlern

**"Can't open a connection to same database file with a different configuration"**
→ Alle `duckdb.connect()` durch `get_building_3d_connection()` ersetzen

**"Scalar Function with name datetime does not exist"**
→ `datetime('now')` durch `current_timestamp` ersetzen