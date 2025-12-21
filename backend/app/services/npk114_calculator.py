"""
NPK 114 Ausmass-Rechner

Berechnung von Gerüst-Ausmassen nach NPK 114 D/2012 (Schweizer Norm).

Grundlagen:
- Längen/Höhen: Meter [m], Genauigkeit 0.1 m
- Flächen: Quadratmeter [m²], Genauigkeit 0.01 m²
- Rundung: Kaufmännisch (0-4 ab, 5-9 auf)
- Minimale Ausmasslänge: LAmin >= 2.5 m
- Minimale Ausmasshöhe: HAmin >= 4.0 m

Zuschläge Fassadengerüst:
- LF = 0.30 m (Fassadenabstand)
- LG = 0.70 m (Gerüstgangbreite bis 0.70m) oder 1.00 m (0.71-1.00m)
- LS = LF + LG = 1.00 m (Stirnseitiger Abschluss)
- Höhenzuschlag: +1.00 m über Arbeitshöhe
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class WidthClass(Enum):
    """Breitenklassen nach EN 12811"""
    W06 = 0.60  # Inspektionsgerüst
    W09 = 0.90  # Standard Fassadengerüst
    W12 = 1.20  # Maurergerüst


@dataclass
class NPKZuschlaege:
    """Zuschläge für NPK 114 Berechnung"""
    fassadenabstand_m: float = 0.30  # LF
    geruest_breite_m: float = 0.70   # LG (W09 Standard)
    hoehenzuschlag_m: float = 1.00   # Über Arbeitshöhe

    @property
    def stirnseitiger_abschluss_m(self) -> float:
        """LS = LF + LG"""
        return self.fassadenabstand_m + self.geruest_breite_m

    @classmethod
    def fuer_breitenklasse(cls, width_class: WidthClass) -> "NPKZuschlaege":
        """Erstelle Zuschläge basierend auf Breitenklasse"""
        if width_class == WidthClass.W06:
            return cls(geruest_breite_m=0.60)
        elif width_class == WidthClass.W09:
            return cls(geruest_breite_m=0.70)
        elif width_class == WidthClass.W12:
            return cls(geruest_breite_m=1.00)
        return cls()


@dataclass
class FassadenAusmass:
    """Ausmass einer einzelnen Fassade"""
    name: str
    laenge_fassade_m: float      # L - Fassadenlänge
    hoehe_traufe_m: float        # Traufhöhe
    hoehe_first_m: Optional[float] = None  # Firsthöhe (bei Giebel)
    ist_giebel: bool = False

    # Berechnete Werte
    ausmass_laenge_m: float = 0.0   # LA
    ausmass_hoehe_m: float = 0.0    # HA
    flaeche_m2: float = 0.0         # A

    # Zuschläge
    zuschlaege: NPKZuschlaege = field(default_factory=NPKZuschlaege)

    def berechne(self) -> "FassadenAusmass":
        """Berechne Ausmass nach NPK 114"""
        ls = self.zuschlaege.stirnseitiger_abschluss_m

        # Ausmasslänge: LA = LS + L + LS
        la = ls + self.laenge_fassade_m + ls
        self.ausmass_laenge_m = max(la, 2.5)  # Minimum 2.5m

        # Ausmasshöhe
        if self.ist_giebel and self.hoehe_first_m:
            # Giebel: H_mittel = H_Traufe + (H_Giebel × 0.5)
            giebel_hoehe = self.hoehe_first_m - self.hoehe_traufe_m
            h_mittel = self.hoehe_traufe_m + (giebel_hoehe * 0.5)
            ha = h_mittel + self.zuschlaege.hoehenzuschlag_m
        else:
            # Normal: HA = H + 1.0m
            ha = self.hoehe_traufe_m + self.zuschlaege.hoehenzuschlag_m

        self.ausmass_hoehe_m = max(ha, 4.0)  # Minimum 4.0m

        # Fläche: A = LA × HA
        self.flaeche_m2 = round(self.ausmass_laenge_m * self.ausmass_hoehe_m, 2)

        return self

    def to_dict(self) -> dict:
        """Konvertiere zu Dictionary"""
        result = {
            "name": self.name,
            "fassade": {
                "laenge_m": self.laenge_fassade_m,
                "hoehe_traufe_m": self.hoehe_traufe_m,
                "ist_giebel": self.ist_giebel
            },
            "ausmass": {
                "laenge_m": round(self.ausmass_laenge_m, 1),
                "hoehe_m": round(self.ausmass_hoehe_m, 1),
                "flaeche_m2": self.flaeche_m2
            },
            "zuschlaege": {
                "fassadenabstand_m": self.zuschlaege.fassadenabstand_m,
                "geruest_breite_m": self.zuschlaege.geruest_breite_m,
                "stirnseitig_m": self.zuschlaege.stirnseitiger_abschluss_m,
                "hoehe_m": self.zuschlaege.hoehenzuschlag_m
            }
        }
        if self.ist_giebel and self.hoehe_first_m:
            result["fassade"]["hoehe_first_m"] = self.hoehe_first_m
            result["fassade"]["giebel_hoehe_m"] = self.hoehe_first_m - self.hoehe_traufe_m
        return result


@dataclass
class GebaeudeAusmass:
    """Gesamtausmass eines Gebäudes"""
    fassaden: list[FassadenAusmass] = field(default_factory=list)
    ecken_anzahl: int = 4  # Standard für rechteckiges Gebäude

    # Berechnete Werte
    gesamt_flaeche_m2: float = 0.0
    eck_zuschlag_m2: float = 0.0
    total_ausmass_m2: float = 0.0

    def berechne(self) -> "GebaeudeAusmass":
        """Berechne Gesamtausmass inkl. Eckzuschläge"""
        # Alle Fassaden berechnen
        for fassade in self.fassaden:
            fassade.berechne()

        # Summe Fassadenflächen
        self.gesamt_flaeche_m2 = sum(f.flaeche_m2 for f in self.fassaden)

        # Eckzuschlag: A_Ecke = LS × HA (pro Ecke)
        # Nimm durchschnittliche Höhe für Eckzuschlag
        if self.fassaden:
            avg_hoehe = sum(f.ausmass_hoehe_m for f in self.fassaden) / len(self.fassaden)
            ls = self.fassaden[0].zuschlaege.stirnseitiger_abschluss_m
            self.eck_zuschlag_m2 = round(self.ecken_anzahl * ls * avg_hoehe, 2)

        # Total
        self.total_ausmass_m2 = round(self.gesamt_flaeche_m2 + self.eck_zuschlag_m2, 2)

        return self

    def to_dict(self) -> dict:
        """Konvertiere zu Dictionary"""
        return {
            "fassaden": [f.to_dict() for f in self.fassaden],
            "zusammenfassung": {
                "anzahl_fassaden": len(self.fassaden),
                "anzahl_ecken": self.ecken_anzahl,
                "fassaden_flaeche_m2": self.gesamt_flaeche_m2,
                "eck_zuschlag_m2": self.eck_zuschlag_m2,
                "total_ausmass_m2": self.total_ausmass_m2
            }
        }


class NPK114Calculator:
    """NPK 114 Ausmass-Rechner"""

    def __init__(self, breitenklasse: WidthClass = WidthClass.W09):
        self.breitenklasse = breitenklasse
        self.zuschlaege = NPKZuschlaege.fuer_breitenklasse(breitenklasse)

    def berechne_fassade(
        self,
        name: str,
        laenge_m: float,
        hoehe_traufe_m: float,
        hoehe_first_m: Optional[float] = None,
        ist_giebel: bool = False
    ) -> FassadenAusmass:
        """Berechne Ausmass einer einzelnen Fassade"""
        fassade = FassadenAusmass(
            name=name,
            laenge_fassade_m=laenge_m,
            hoehe_traufe_m=hoehe_traufe_m,
            hoehe_first_m=hoehe_first_m,
            ist_giebel=ist_giebel,
            zuschlaege=self.zuschlaege
        )
        return fassade.berechne()

    def berechne_rechteckiges_gebaeude(
        self,
        laenge_m: float,
        breite_m: float,
        hoehe_traufe_m: float,
        hoehe_first_m: Optional[float] = None,
        dachform: str = "flach"  # flach, satteldach, walmdach
    ) -> GebaeudeAusmass:
        """
        Berechne Ausmass für rechteckiges Gebäude.

        Args:
            laenge_m: Gebäudelänge (Traufseite bei Satteldach)
            breite_m: Gebäudebreite (Giebelseite bei Satteldach)
            hoehe_traufe_m: Traufhöhe
            hoehe_first_m: Firsthöhe (bei Satteldach/Walmdach)
            dachform: flach, satteldach, oder walmdach

        Returns:
            GebaeudeAusmass mit allen berechneten Fassaden
        """
        fassaden = []

        if dachform == "flach":
            # Alle Seiten gleich hoch
            fassaden = [
                self.berechne_fassade("Fassade Nord", laenge_m, hoehe_traufe_m),
                self.berechne_fassade("Fassade Süd", laenge_m, hoehe_traufe_m),
                self.berechne_fassade("Fassade Ost", breite_m, hoehe_traufe_m),
                self.berechne_fassade("Fassade West", breite_m, hoehe_traufe_m),
            ]

        elif dachform == "satteldach":
            # Traufseiten (Längsseiten) - normale Höhe
            # Giebelseiten (Schmalseiten) - mit Giebel
            fassaden = [
                self.berechne_fassade("Traufseite Nord", laenge_m, hoehe_traufe_m),
                self.berechne_fassade("Traufseite Süd", laenge_m, hoehe_traufe_m),
                self.berechne_fassade("Giebelseite Ost", breite_m, hoehe_traufe_m,
                                      hoehe_first_m, ist_giebel=True),
                self.berechne_fassade("Giebelseite West", breite_m, hoehe_traufe_m,
                                      hoehe_first_m, ist_giebel=True),
            ]

        elif dachform == "walmdach":
            # Alle Seiten haben abgeschrägte Dächer
            # Vereinfachung: Durchschnittshöhe verwenden
            h_mittel = hoehe_traufe_m + ((hoehe_first_m or hoehe_traufe_m) - hoehe_traufe_m) * 0.25
            fassaden = [
                self.berechne_fassade("Fassade Nord", laenge_m, h_mittel),
                self.berechne_fassade("Fassade Süd", laenge_m, h_mittel),
                self.berechne_fassade("Fassade Ost", breite_m, h_mittel),
                self.berechne_fassade("Fassade West", breite_m, h_mittel),
            ]

        gebaeude = GebaeudeAusmass(fassaden=fassaden, ecken_anzahl=4)
        return gebaeude.berechne()

    def berechne_einzelne_fassaden(
        self,
        fassaden_daten: list[dict]
    ) -> GebaeudeAusmass:
        """
        Berechne Ausmass für individuell definierte Fassaden.

        Args:
            fassaden_daten: Liste mit Fassadendaten
                [{"name": "Nord", "laenge_m": 12.0, "hoehe_traufe_m": 6.5,
                  "hoehe_first_m": 10.0, "ist_giebel": False}, ...]

        Returns:
            GebaeudeAusmass
        """
        fassaden = []
        for fd in fassaden_daten:
            fassade = self.berechne_fassade(
                name=fd.get("name", f"Fassade {len(fassaden)+1}"),
                laenge_m=fd["laenge_m"],
                hoehe_traufe_m=fd["hoehe_traufe_m"],
                hoehe_first_m=fd.get("hoehe_first_m"),
                ist_giebel=fd.get("ist_giebel", False)
            )
            fassaden.append(fassade)

        # Ecken = Anzahl Fassaden (angenommen geschlossenes Polygon)
        ecken = len(fassaden)

        gebaeude = GebaeudeAusmass(fassaden=fassaden, ecken_anzahl=ecken)
        return gebaeude.berechne()

    def berechne_mit_geodaten(
        self,
        building_data: dict,
        hoehe_traufe_m: Optional[float] = None,
        hoehe_first_m: Optional[float] = None
    ) -> GebaeudeAusmass:
        """
        Berechne Ausmass basierend auf Geodaten vom API.

        Erwartet building_data mit:
        - garea: Gebäudefläche m²
        - gastw: Anzahl Geschosse
        - gebaeude_hoehe oder height_source Daten
        - Optional: Geometrie für Umfang

        Args:
            building_data: Daten vom /scaffolding API
            hoehe_traufe_m: Manuelle Traufhöhe (überschreibt)
            hoehe_first_m: Manuelle Firsthöhe

        Returns:
            GebaeudeAusmass
        """
        # Höhe bestimmen (Priorität: manuell > API)
        if hoehe_traufe_m is None:
            hoehe_traufe_m = building_data.get("gebaeude_hoehe", 10.0)

        # Gebäudefläche und geschätzte Dimensionen
        garea = building_data.get("garea", 100)

        # Quadratisches Gebäude als Annäherung
        import math
        seite = math.sqrt(garea) if garea else 10.0

        # Prüfe ob Geometrie-Umfang verfügbar
        umfang = building_data.get("umfang_m")
        if umfang:
            # Aus Umfang und Fläche: Rechteck-Dimensionen schätzen
            # P = 2(L+B), A = L*B
            # Quadratische Formel lösen
            p = umfang / 2  # L + B
            a = garea       # L * B
            discriminant = p*p - 4*a
            if discriminant >= 0:
                sqrt_d = math.sqrt(discriminant)
                laenge = (p + sqrt_d) / 2
                breite = (p - sqrt_d) / 2
            else:
                laenge = breite = seite
        else:
            laenge = breite = seite

        # Dachform schätzen
        dachform = "flach"
        if hoehe_first_m and hoehe_first_m > hoehe_traufe_m:
            dachform = "satteldach"

        return self.berechne_rechteckiges_gebaeude(
            laenge_m=round(laenge, 1),
            breite_m=round(breite, 1),
            hoehe_traufe_m=hoehe_traufe_m,
            hoehe_first_m=hoehe_first_m,
            dachform=dachform
        )


# Convenience-Funktionen

def berechne_ausmass_einfach(
    laenge_m: float,
    breite_m: float,
    hoehe_traufe_m: float,
    hoehe_first_m: Optional[float] = None,
    dachform: str = "flach",
    breitenklasse: str = "W09"
) -> dict:
    """
    Einfache Ausmass-Berechnung für ein rechteckiges Gebäude.

    Returns:
        Dictionary mit vollständigem Ausmass
    """
    wk = WidthClass[breitenklasse]
    calc = NPK114Calculator(breitenklasse=wk)

    result = calc.berechne_rechteckiges_gebaeude(
        laenge_m=laenge_m,
        breite_m=breite_m,
        hoehe_traufe_m=hoehe_traufe_m,
        hoehe_first_m=hoehe_first_m,
        dachform=dachform
    )

    return result.to_dict()


def berechne_einzelfassade(
    laenge_m: float,
    hoehe_m: float,
    breitenklasse: str = "W09"
) -> dict:
    """
    Berechne Ausmass einer einzelnen Fassade.

    Returns:
        Dictionary mit Fassaden-Ausmass
    """
    wk = WidthClass[breitenklasse]
    calc = NPK114Calculator(breitenklasse=wk)

    fassade = calc.berechne_fassade(
        name="Fassade",
        laenge_m=laenge_m,
        hoehe_traufe_m=hoehe_m
    )

    return fassade.to_dict()
