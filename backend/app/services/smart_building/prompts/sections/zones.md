# Hoehenzonen Template

## Zonen-Typen Legende

| Typ | Beschreibung | SVG-Darstellung |
|-----|--------------|-----------------|
| **hauptgebaeude** | Rechteckiger Hauptkoerper | Schraffur url(#hatch) |
| **arkade** | Niedriger Bereich mit Rundbogen (EG) | Rundbogen-Elemente |
| **kuppel** | Halbkreis/Kuppelform | Kupfer-Gradient url(#copper) - EINZIGER Gradient! |
| **turm** | Schmaler, hoher Turm | Sonderkonstruktion, separates Geruest |
| **anbau** | Niedrigerer Anbau am Hauptgebaeude | Eigene Hoehe, verbunden |
| **innenhof** | Nicht einruesten | Freiflaeche, LEER lassen! |

## Gebaeudeform-Hinweise

Bei komplexen Gebaeudeformen MUSS die Form explizit angegeben werden:

| Form | Beschreibung | SVG-Hinweis |
|------|--------------|-------------|
| **U-Form** | Offene Seite, Ehrenhof in der Mitte | Ehrenhof als Freiflaeche, NICHT schraffieren |
| **L-Form** | Zwei Fluegel im rechten Winkel | Deutliche Ecke markieren |
| **Kreuzform** | Basilika-Typ mit Querhaus | Langhaus + Querhaus unterscheiden |
| **Rechteckig** | Standard-Form | Einfaches Rechteck |

## Hoehen-Tabelle Format

```
| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| [Name] | [typ] | [m] | [m] | [m] | [Standard/Sonderkonstruktion/Nein] |
```

**WICHTIG:** Alle drei Hoehenwerte angeben fuer korrekte Proportionen!
