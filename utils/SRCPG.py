"""
SRCPG Designer - Split Ring Compound Planetary Gear

Outil de conception pour engrenages planétaires compound à double couronne.
Approche par contraintes d'encombrement (système métrique uniquement).

Architecture SRCPG:
    Soleil (entrée) → Planète (double denture) → Couronne fixe (bloquée)
                                              ↘ Couronne sortie (sortie)

Formule de Willis: i = (1 + Z_F/Z_S) / (1 - Z_F/Z_O)

Système métrique:
- Module (m) en mm/dent
- Diamètre primitif: d = Z × m
- Addendum standard: a = 1.0 × m
"""

import numpy as np
from matplotlib.patches import Circle
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Sequence
import matplotlib.pyplot as plt

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


def _pitch_diameter_mm(teeth: int, module_mm: float) -> float:
    """Diamètre primitif en mm pour un engrenage de N dents avec module m."""
    if module_mm <= 0:
        raise ValueError("module_mm doit être > 0")
    return teeth * module_mm


def _addendum_mm(module_mm: float) -> float:
    """Addendum standard en mm pour une denture involute sans correction."""
    # En système métrique : addendum = 1.0 × module (standard)
    return 1.0 * module_mm


@dataclass
class SRCPGConstraints:
    """Contraintes et entrées inspirées du tableur de David Hartkop.

    Objectif : "meilleur des deux mondes".
    - Paramétrisation/équations : style Hartkop (Ns1, Np1, Na1, Ns2, Np2, Na2, m1, m2, n, P)
    - Vérifications pratiques : encombrement, anti-collision, min dents, etc.

    Notes :
    - Le système autorise m2 != m1 pour ajuster la coaxialité.
    - n est typiquement rationnel ; dans la pratique on explore souvent n = 1.
    """

    max_diameter: float  # mm, diamètre extérieur max (approx)
    module_stage1: float  # mm/dent pour l'étage 1
    target_ratio: float
    ratio_tolerance: float = 0.1 # %
    num_planets: int = 3  # P
    n_values: Sequence[float] = (1.0,)  # multiplicateur n (étage 2)
    min_teeth: int = 17  # nombre minimum de dents (évite sous-denture)
    planet_clearance_factor: float = 1.10  # marge grossière (moyeu/vis/impression)


@dataclass
class SRCPGSolution:
    """Solution au sens du tableur Hartkop (2 dentures sur la même planète compound)."""

    # Entrées principales (étage 1)
    zs: int
    zf: int
    p: int
    n: float
    module_stage1: float  # mm/dent

    # Dérivés
    zpf: int = field(init=False)
    zpo: int = field(init=False)
    zo: int = field(init=False)
    zs2: int = field(init=False)
    module_stage2: float = field(init=False)

    r1: float = field(init=False)
    r2: float = field(init=False)
    rf: float = field(init=False)

    def __post_init__(self):
        # Formules du CSV (David Hartkop)
        # Zp,f = (Zf - Zs) / 2
        self.zpf = int((self.zf - self.zs) // 2)

        # Zp,o = Zp,f · n (doit être entier en pratique)
        self.zpo = int(round(self.zpf * self.n))

        # Zo = n·Zf + P
        self.zo = int(round(self.n * self.zf + self.p))

        # Zs2 = Zo - 2·Zp,o
        self.zs2 = int(self.zo - 2 * self.zpo)

        # m2 = m1 * (Zf - Zp,f) / (Zo - Zp,o)
        # Formule métrique pour assurer la coaxialité des deux étages
        denom = (self.zo - self.zpo)
        self.module_stage2 = (self.module_stage1 * (self.zf - self.zpf)) / denom if denom != 0 else float("inf")

        # Ratios du CSV
        self.r1 = (self.zf / self.zs) + 1.0
        # Attention: singularité si Zo == n*Zf
        denom_r2 = (self.zo - self.n * self.zf)
        self.r2 = (self.n * self.zf) / denom_r2 if abs(denom_r2) > 1e-12 else float("inf")
        self.rf = self.r1 * self.r2

    def is_valid(self, constraints: SRCPGConstraints) -> Tuple[bool, List[str]]:
        """Vérifie intégralité, cohérence géométrique et contraintes pratiques."""
        errors: List[str] = []

        if self.p <= 0:
            errors.append("P doit être > 0")

        if self.zs <= 0 or self.zf <= 0:
            errors.append("Zs et Zf doivent être > 0")

        if self.zf <= self.zs:
            errors.append("Zf doit être > Zs (sinon Zp,f <= 0)")

        # Entier: Zp,f=(Zf-Zs)/2
        if (self.zf - self.zs) % 2 != 0:
            errors.append("Zp,f non entier: (Zf - Zs) doit être pair")

        # Min dents (pratique)
        for name, z in [("Zs", self.zs), ("Zf", self.zf), ("Zp,f", self.zpf), ("Zs2", self.zs2), ("Zo", self.zo), ("Zp,o", self.zpo)]:
            if z < constraints.min_teeth:
                errors.append(f"{name}: {z} dents < {constraints.min_teeth}")

        # Divisibilités par P
        for name, z in [("Zs", self.zs), ("Zf", self.zf), ("Zs2", self.zs2)]:
            if z % self.p != 0:
                errors.append(f"Hartkop: {name}={z} non divisible par P={self.p}")

        # Condition d'assemblage (pratique, plus générale) : (Z_sun + Z_ring) divisible par P
        if (self.zs + self.zf) % self.p != 0:
            errors.append(f"Assemblage étage 1: (Zs+Zf)={self.zs + self.zf} non divisible par P={self.p}")
        if (self.zs2 + self.zo) % self.p != 0:
            errors.append(f"Assemblage étage 2: (Zs2+Zo)={self.zs2 + self.zo} non divisible par P={self.p}")

        # module_stage2 doit être fini et positif
        if not (self.module_stage2 > 0 and np.isfinite(self.module_stage2)):
            errors.append("module_stage2 invalide (<=0 ou non fini)")

        # Coaxialité / même rayon de carrier entre étages (le module2 est justement calculé pour)
        # On vérifie numériquement pour attraper les cas pathologiques.
        if self.module_stage2 > 0 and np.isfinite(self.module_stage2):
            a1 = (self.zs + self.zpf) * self.module_stage1 / 2
            a2 = (self.zs2 + self.zpo) * self.module_stage2 / 2
            if abs(a1 - a2) > 0.25:  # tolérance pratique (mm)
                errors.append(f"Coaxialité: entraxes étages diffèrent (a1={a1:.2f}mm, a2={a2:.2f}mm)")

        # Anti-collision (grossier) : distance entre centres de planètes vs diamètre extérieur de la planète
        # On estime le rayon extérieur de la planète par (rayon primitif + addendum) au pire des 2 dentures.
        a_carrier = (self.zs + self.zpf) * self.module_stage1 / 2
        planet_pitch_radius_mm = max(_pitch_diameter_mm(self.zpf, self.module_stage1), _pitch_diameter_mm(self.zpo, self.module_stage2)) / 2
        planet_outer_radius_mm = planet_pitch_radius_mm + max(_addendum_mm(self.module_stage1), _addendum_mm(self.module_stage2))

        if self.p > 1:
            min_center_spacing = 2 * a_carrier * np.sin(np.pi / self.p)
            required = 2 * planet_outer_radius_mm * constraints.planet_clearance_factor
            if min_center_spacing < required:
                errors.append(
                    f"Planètes trop proches: espacement centres={min_center_spacing:.2f}mm < requis≈{required:.2f}mm"
                )

        # Encombrement (grossier) : Øext ≈ Øprimitif(anneau) + 2*addendum
        od1 = _pitch_diameter_mm(self.zf, self.module_stage1) + 2 * _addendum_mm(self.module_stage1)
        od2 = _pitch_diameter_mm(self.zo, self.module_stage2) + 2 * _addendum_mm(self.module_stage2)
        overall = max(od1, od2)
        if overall > constraints.max_diameter:
            errors.append(f"Encombrement: Ø≈{overall:.2f}mm > {constraints.max_diameter:.2f}mm")

        return len(errors) == 0, errors

    @property
    def approx_overall_diameter_mm(self) -> float:
        od1 = _pitch_diameter_mm(self.zf, self.module_stage1) + 2 * _addendum_mm(self.module_stage1)
        od2 = _pitch_diameter_mm(self.zo, self.module_stage2) + 2 * _addendum_mm(self.module_stage2)
        return max(od1, od2)


class SRCPGDesigner:
    """Recherche de configurations compatibles, basée sur les équations Hartkop + checks pratiques."""

    def __init__(self, constraints: SRCPGConstraints):
        self.constraints = constraints
        self.solutions: List[SRCPGSolution] = []

    def search(self) -> List[SRCPGSolution]:
        c = self.constraints
        self.solutions = []

        # Plage ratio
        ratio_min = c.target_ratio * (1 - c.ratio_tolerance)
        ratio_max = c.target_ratio * (1 + c.ratio_tolerance)

        # Bornes de dents (heuristiques)
        # - Zs petit aide le ratio
        # - Zf est borné par le diamètre max (OD ~ PD + 2m)
        m1 = c.module_stage1
        max_zf = int((c.max_diameter - 2 * _addendum_mm(m1)) / m1)
        max_zf = max(max_zf, c.min_teeth * 2)

        zs_max = min(80, max_zf)  # garde-fou perf

        # Estimation du nombre total d'itérations pour la barre de progression
        zs_range = zs_max - c.min_teeth + 1
        zf_avg_range = max_zf - (c.min_teeth + 2 * c.min_teeth) + 1  # approximatif
        total_estimated = zs_range * zf_avg_range * len(c.n_values)
        counter = 0

        candidates: List[SRCPGSolution] = []
        zs_list = list(range(c.min_teeth, zs_max + 1))
        if tqdm:
            zs_iter = tqdm(zs_list, desc="Recherche SRCPG")
        else:
            zs_iter = zs_list
        for zs in zs_iter:
            # Zf doit laisser un Zp,f >= min_teeth : (Zf-Zs)/2 >= min_teeth => Zf >= Zs + 2*min_teeth
            zf_min = zs + 2 * c.min_teeth
            for zf in range(zf_min, max_zf + 1):
                if (zf - zs) % 2 != 0:
                    continue

                for n in c.n_values:
                    sol = SRCPGSolution(zs=zs, zf=zf, p=c.num_planets, n=float(n), module_stage1=m1)

                    ok, _errs = sol.is_valid(c)
                    if not ok:
                        continue

                    if not (ratio_min <= sol.rf <= ratio_max):
                        continue

                    candidates.append(sol)

        print()  # Nouvelle ligne après la barre
        # Tri par proximité ratio
        candidates.sort(key=lambda s: abs(s.rf - c.target_ratio))
        self.solutions = candidates
        print(f"✅ SRCPG: {len(self.solutions)} solutions (ratio≈{c.target_ratio} ±{c.ratio_tolerance*100:.0f}%)")
        return self.solutions

    def print_solutions(self, max_display: int = 20):
        if not self.solutions:
            print("❌ Aucune solution SRCPG trouvée")
            return

        print(f"✅ {len(self.solutions)} solutions SRCPG trouvées!\n")
        print("=" * 110)
        print(
            f"{'#':>3} | {'Zs':>4} | {'Zf':>4} | {'Zp,f':>4} || {'Zs2':>4} | {'Zo':>4} | {'Zp,o':>4} || "
            f"{'m1':>6} | {'m2':>6} | {'Rf':>10} | {'Ø~':>8} | {'n':>5}"
        )
        print("-" * 110)
        for i, sol in enumerate(self.solutions[:max_display]):
            print(
                f"{i+1:>3} | {sol.zs:>4} | {sol.zf:>4} | {sol.zpf:>4} || {sol.zs2:>4} | {sol.zo:>4} | {sol.zpo:>4} || "
                f"{sol.module_stage1:>6.2f} | {sol.module_stage2:>6.2f} | {sol.rf:>10.2f} | {sol.approx_overall_diameter_mm:>7.1f}mm | {sol.n:>5.1f}"
            )
        print("=" * 110)


