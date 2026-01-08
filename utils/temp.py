"""
SRCPG Designer - Split Ring Compound Planetary Gear

Outil de conception pour engrenages planétaires compound à double couronne.
Approche par contraintes d'encombrement.

Architecture SRCPG:
    Soleil (entrée) → Planète (double denture) → Couronne fixe (bloquée)
                                              ↘ Couronne sortie (sortie)

Formule de Willis: i = (1 + Z_F/Z_S) / (1 - Z_F/Z_O)
"""

import numpy as np
from matplotlib.patches import Circle
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Sequence
import matplotlib.pyplot as plt


INCH_TO_MM = 25.4


def _module_to_diametral_pitch(module_mm: float) -> float:
    """Convertit module (mm/dent) -> diametral pitch (dents/pouce)."""
    if module_mm <= 0:
        raise ValueError("module_mm doit être > 0")
    return INCH_TO_MM / module_mm


def _diametral_pitch_to_module(dp: float) -> float:
    """Convertit diametral pitch (dents/pouce) -> module (mm/dent)."""
    if dp <= 0:
        raise ValueError("dp doit être > 0")
    return INCH_TO_MM / dp


def _pitch_diameter_mm(teeth: int, dp: float) -> float:
    """Diamètre primitif en mm pour un engrenage de N dents à diametral pitch dp."""
    return (teeth / dp) * INCH_TO_MM


def _addendum_mm(dp: float) -> float:
    """Addendum standard (approx) en mm pour une denture involute sans correction."""
    # En système diametral pitch : addendum ≈ 1/dp (en pouces)
    return (1.0 / dp) * INCH_TO_MM


@dataclass
class HartkopConstraints:
    """Contraintes et entrées inspirées du tableur de David Hartkop.

    Objectif : "meilleur des deux mondes".
    - Paramétrisation/équations : style Hartkop (Ns1, Np1, Na1, Ns2, Np2, Na2, Dp1, Dp2, n, P)
    - Vérifications pratiques : encombrement, anti-collision, min dents, etc.

    Notes :
    - Le tableur autorise Dp2 != Dp1 (donc module2 != module1). On conserve cette possibilité.
    - n est typiquement rationnel ; dans la pratique on explore souvent n = 1.
    """

    max_diameter: float  # mm, diamètre extérieur max (approx)
    module_stage1: float  # mm/dent pour l'étage 1 (Dp1 dérivé)
    target_ratio: float
    ratio_tolerance: float = 0.1
    num_planets: int = 3  # P
    n_values: Sequence[float] = (1.0,)  # multiplicateur n (étage 2)
    min_teeth: int = 12
    planet_clearance_factor: float = 1.10  # marge grossière (moyeu/vis/impression)
    strict_hartkop_divisibility: bool = True  # si True: impose les “divisible par P” du tableur

    @property
    def dp1(self) -> float:
        return _module_to_diametral_pitch(self.module_stage1)


@dataclass
class HartkopSolution:
    """Solution au sens du tableur Hartkop (2 dentures sur la même planète compound)."""

    # Entrées principales (étage 1)
    ns1: int
    na1: int
    p: int
    n: float
    dp1: float

    # Dérivés
    np1: int = field(init=False)
    np2: int = field(init=False)
    na2: int = field(init=False)
    ns2: int = field(init=False)
    dp2: float = field(init=False)
    module_stage2: float = field(init=False)

    r1: float = field(init=False)
    r2: float = field(init=False)
    rf: float = field(init=False)

    def __post_init__(self):
        # Formules du CSV (David Hartkop)
        # Np1 = (Na1 - Ns1)/2
        self.np1 = int((self.na1 - self.ns1) // 2)

        # Np2 = Np1 * n (doit être entier en pratique)
        self.np2 = int(round(self.np1 * self.n))

        # Na2 = n*Na1 + P
        self.na2 = int(round(self.n * self.na1 + self.p))

        # Ns2 = Na2 - 2*Np2
        self.ns2 = int(self.na2 - 2 * self.np2)

        # Dp2 = Dp1*(Na2-Np2)/(Na1-Np1)
        denom = (self.na1 - self.np1)
        self.dp2 = (self.dp1 * (self.na2 - self.np2)) / denom if denom != 0 else float("inf")
        self.module_stage2 = _diametral_pitch_to_module(self.dp2) if self.dp2 > 0 and np.isfinite(self.dp2) else float("inf")

        # Ratios du CSV
        self.r1 = (self.na1 / self.ns1) + 1.0
        # Attention: singularité si Na2 == n*Na1
        denom_r2 = (self.na2 - self.n * self.na1)
        self.r2 = (self.n * self.na1) / denom_r2 if abs(denom_r2) > 1e-12 else float("inf")
        self.rf = self.r1 * self.r2

    def is_valid(self, constraints: HartkopConstraints) -> Tuple[bool, List[str]]:
        """Vérifie intégralité, cohérence géométrique et contraintes pratiques."""
        errors: List[str] = []

        if self.p <= 0:
            errors.append("P doit être > 0")

        if self.ns1 <= 0 or self.na1 <= 0:
            errors.append("Ns1 et Na1 doivent être > 0")

        if self.na1 <= self.ns1:
            errors.append("Na1 doit être > Ns1 (sinon Np1 <= 0)")

        # Entier: Np1=(Na1-Ns1)/2
        if (self.na1 - self.ns1) % 2 != 0:
            errors.append("Np1 non entier: (Na1 - Ns1) doit être pair")

        # Min dents (pratique)
        for name, z in [("Ns1", self.ns1), ("Na1", self.na1), ("Np1", self.np1), ("Ns2", self.ns2), ("Na2", self.na2), ("Np2", self.np2)]:
            if z < constraints.min_teeth:
                errors.append(f"{name}: {z} dents < {constraints.min_teeth}")

        # Divisibilités du tableur (optionnel / strict)
        if constraints.strict_hartkop_divisibility:
            for name, z in [("Ns1", self.ns1), ("Na1", self.na1), ("Ns2", self.ns2)]:
                if z % self.p != 0:
                    errors.append(f"Hartkop: {name}={z} non divisible par P={self.p}")

        # Condition d'assemblage (pratique, plus générale) : (Z_sun + Z_ring) divisible par P
        if (self.ns1 + self.na1) % self.p != 0:
            errors.append(f"Assemblage étage 1: (Ns1+Na1)={self.ns1 + self.na1} non divisible par P={self.p}")
        if (self.ns2 + self.na2) % self.p != 0:
            errors.append(f"Assemblage étage 2: (Ns2+Na2)={self.ns2 + self.na2} non divisible par P={self.p}")

        # Dp2 doit être fini et positif
        if not (self.dp2 > 0 and np.isfinite(self.dp2)):
            errors.append("Dp2 invalide (<=0 ou non fini)")

        # Coaxialité / même rayon de carrier entre étages (le Dp2 est justement calculé pour)
        # On vérifie numériquement pour attraper les cas pathologiques.
        if self.dp2 > 0 and np.isfinite(self.dp2):
            a1 = ((self.ns1 + self.np1) / (2 * self.dp1)) * INCH_TO_MM
            a2 = ((self.ns2 + self.np2) / (2 * self.dp2)) * INCH_TO_MM
            if abs(a1 - a2) > 0.25:  # tolérance pratique (mm)
                errors.append(f"Coaxialité: entraxes étages diffèrent (a1={a1:.2f}mm, a2={a2:.2f}mm)")

        # Anti-collision (grossier) : distance entre centres de planètes vs diamètre extérieur de la planète
        # On estime le rayon extérieur de la planète par (rayon primitif + addendum) au pire des 2 dentures.
        a_carrier = ((self.ns1 + self.np1) / (2 * self.dp1)) * INCH_TO_MM
        planet_pitch_radius_mm = max(_pitch_diameter_mm(self.np1, self.dp1), _pitch_diameter_mm(self.np2, self.dp2)) / 2
        planet_outer_radius_mm = planet_pitch_radius_mm + max(_addendum_mm(self.dp1), _addendum_mm(self.dp2))

        if self.p > 1:
            min_center_spacing = 2 * a_carrier * np.sin(np.pi / self.p)
            required = 2 * planet_outer_radius_mm * constraints.planet_clearance_factor
            if min_center_spacing < required:
                errors.append(
                    f"Planètes trop proches: espacement centres={min_center_spacing:.2f}mm < requis≈{required:.2f}mm"
                )

        # Encombrement (grossier) : Øext ≈ Øprimitif(anneau) + 2*addendum
        od1 = _pitch_diameter_mm(self.na1, self.dp1) + 2 * _addendum_mm(self.dp1)
        od2 = _pitch_diameter_mm(self.na2, self.dp2) + 2 * _addendum_mm(self.dp2)
        overall = max(od1, od2)
        if overall > constraints.max_diameter:
            errors.append(f"Encombrement: Ø≈{overall:.2f}mm > {constraints.max_diameter:.2f}mm")

        return len(errors) == 0, errors

    @property
    def approx_overall_diameter_mm(self) -> float:
        od1 = _pitch_diameter_mm(self.na1, self.dp1) + 2 * _addendum_mm(self.dp1)
        od2 = _pitch_diameter_mm(self.na2, self.dp2) + 2 * _addendum_mm(self.dp2)
        return max(od1, od2)


class HartkopDesigner:
    """Recherche de configurations compatibles, basée sur les équations Hartkop + checks pratiques."""

    def __init__(self, constraints: HartkopConstraints):
        self.constraints = constraints
        self.solutions: List[HartkopSolution] = []

    def search(self) -> List[HartkopSolution]:
        c = self.constraints
        self.solutions = []

        # Plage ratio
        ratio_min = c.target_ratio * (1 - c.ratio_tolerance)
        ratio_max = c.target_ratio * (1 + c.ratio_tolerance)

        # Bornes de dents (heuristiques)
        # - Ns1 petit aide le ratio
        # - Na1 est borné par le diamètre max (OD ~ PD + 2m)
        dp1 = c.dp1
        max_na1 = int(((c.max_diameter - 2 * _addendum_mm(dp1)) / INCH_TO_MM) * dp1)
        max_na1 = max(max_na1, c.min_teeth * 2)

        ns1_max = min(80, max_na1)  # garde-fou perf

        candidates: List[HartkopSolution] = []
        for ns1 in range(c.min_teeth, ns1_max + 1):
            # Na1 doit laisser un Np1 >= min_teeth : (Na1-Ns1)/2 >= min_teeth => Na1 >= Ns1 + 2*min_teeth
            na1_min = ns1 + 2 * c.min_teeth
            for na1 in range(na1_min, max_na1 + 1):
                if (na1 - ns1) % 2 != 0:
                    continue

                for n in c.n_values:
                    sol = HartkopSolution(ns1=ns1, na1=na1, p=c.num_planets, n=float(n), dp1=dp1)

                    ok, _errs = sol.is_valid(c)
                    if not ok:
                        continue

                    if not (ratio_min <= sol.rf <= ratio_max):
                        continue

                    candidates.append(sol)

        # Tri par proximité ratio
        candidates.sort(key=lambda s: abs(s.rf - c.target_ratio))
        self.solutions = candidates
        print(f"✅ Hartkop: {len(self.solutions)} solutions (ratio≈{c.target_ratio} ±{c.ratio_tolerance*100:.0f}%)")
        return self.solutions

    def print_solutions(self, max_display: int = 20):
        if not self.solutions:
            print("❌ Aucune solution Hartkop trouvée")
            return

        print(f"✅ {len(self.solutions)} solutions Hartkop trouvées!\n")
        print("=" * 110)
        print(
            f"{'#':>3} | {'Ns1':>4} | {'Na1':>4} | {'Np1':>4} || {'Ns2':>4} | {'Na2':>4} | {'Np2':>4} || "
            f"{'Dp1':>6} | {'Dp2':>6} | {'Rf':>10} | {'Ø~':>8}"
        )
        print("-" * 110)
        for i, sol in enumerate(self.solutions[:max_display]):
            print(
                f"{i+1:>3} | {sol.ns1:>4} | {sol.na1:>4} | {sol.np1:>4} || {sol.ns2:>4} | {sol.na2:>4} | {sol.np2:>4} || "
                f"{sol.dp1:>6.2f} | {sol.dp2:>6.2f} | {sol.rf:>10.2f} | {sol.approx_overall_diameter_mm:>7.1f}mm"
            )
        print("=" * 110)


