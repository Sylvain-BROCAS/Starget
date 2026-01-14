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
    import pygad
except ImportError:
    pygad = None

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
    module_min: float  # mm/dent minimum pour les deux étages
    module_max: float  # mm/dent maximum pour les deux étages
    target_ratio: float
    ratio_tolerance: float = 0.1 # %
    num_planets: int = 3  # P
    n_values: Sequence[float] = (1.0,)  # multiplicateur n (étage 2)
    min_teeth: int = 17  # nombre minimum de dents (évite sous-denture)
    planet_clearance_factor: float = 1.10  # marge grossière (moyeu/vis/impression)
    
    # Options impression 3D
    printing_technology: str = "none"  # "none", "fdm", "sla"
    min_feature_size: Optional[float] = None  # mm, taille minimale de détail imprimable (auto-ajusté selon technologie si None)

    def __post_init__(self):
        """Ajuste min_feature_size selon la technologie d'impression si non spécifié."""
        if self.min_feature_size is None:
            tech = self.printing_technology.lower()
            if tech == "fdm":
                self.min_feature_size = 0.4
            elif tech == "sla":
                self.min_feature_size = 0.1
            else:
                self.min_feature_size = 0.1  # default


def validate_srcpg_design(
    zs: int, zf: int, zpf: int, n: float, p: int,
    module_stage1: float, module_stage2: float,
    max_diameter: float = 100.0,
    module_min: float = 0.1,
    module_max: float = 5.0,
    printing_technology: str = "none",
    min_feature_size: Optional[float] = None,
    verbose: bool = True
) -> Tuple[bool, List[str], List[str], Optional[SRCPGSolution]]:
    """
    Valide un design SRCPG à partir des paramètres des deux étages.

    Parameters:
    -----------
    zs : int
        Nombre de dents du soleil étage 1
    zf : int
        Nombre de dents de la couronne fixe
    zpf : int
        Nombre de dents des planètes étage 1
    n : float
        Facteur de multiplication entre étages
    p : int
        Nombre de planètes
    module_stage1 : float
        Module de l'étage 1 (mm/dent)
    module_stage2 : float
        Module de l'étage 2 (mm/dent)
    max_diameter : float
        Diamètre maximum autorisé (mm)
    module_min : float
        Module minimum pour les deux étages (mm/dent)
    module_max : float
        Module maximum pour les deux étages (mm/dent)
    printing_technology : str
        Technologie d'impression ("none", "fdm", "sla")
    min_feature_size : float, optional
        Taille minimale de détail (auto-ajusté si None)
    verbose : bool
        Afficher les détails de validation

    Returns:
    --------
    Tuple[bool, List[str], List[str], Optional[SRCPGSolution]]
        (is_valid, errors, warnings, solution_object)
    """
    errors = []
    warnings = []

    # Créer les contraintes
    constraints = SRCPGConstraints(
        max_diameter=max_diameter,
        module_min=module_min,
        module_max=module_max,
        target_ratio=1.0,  # non utilisé pour validation
        printing_technology=printing_technology,
        min_feature_size=min_feature_size
    )

    # Calculer les paramètres dérivés
    try:
        # Vérifier la géométrie étage 1
        if (zf - zs) % 2 != 0:
            errors.append(f"Géométrie étage 1 invalide: (Zf - Zs) = {zf - zs} doit être pair")
        else:
            zpf_calc = (zf - zs) // 2
            if zpf_calc != zpf:
                errors.append(f"Zp,f incorrect: calculé {zpf_calc}, fourni {zpf}")

        # Calculer étage 2
        zpo = int(round(zpf * n))
        zo = int(round(n * zf + p))
        zs2 = zo - 2 * zpo

        # Vérifier cohérence étage 2
        if zs2 <= constraints.min_teeth:
            errors.append(f"Zs2 = {zs2} < min_teeth = {constraints.min_teeth}")

        # Calculer module_stage2 si nécessaire
        module_stage2_calc = module_stage1 * (zf - zpf) / (zo - zpo)
        if abs(module_stage2_calc - module_stage2) > 0.01:
            warnings.append(f"Module étage 2 incohérent: calculé {module_stage2_calc:.3f}, fourni {module_stage2:.3f}")

        # Créer la solution temporaire
        solution = SRCPGSolution(
            zs=zs, zf=zf, p=p, n=n, module_stage1=module_stage1
        )
        # Forcer les valeurs calculées
        solution.zpf = zpf
        solution.zpo = zpo
        solution.zo = zo
        solution.zs2 = zs2
        solution.module_stage2 = module_stage2

        # Calculer les ratios
        solution.r1 = (zf / zs) + 1
        solution.r2 = (n * zf) / (zo - n * zf) if zo != n * zf else float('inf')
        solution.rf = solution.r1 * solution.r2

        # Vérifier les contraintes
        is_valid, geom_errors, geom_warnings = solution.is_geometry_ok(constraints)
        errors.extend(geom_errors)
        warnings.extend(geom_warnings)

        # Vérifier diamètre
        if not solution.is_diameter_ok(constraints):
            errors.append(f"Diamètre trop grand: {solution.approx_overall_diameter_mm:.1f}mm > {max_diameter}mm")

        # Vérifier ratio
        if not np.isfinite(solution.rf) or solution.rf <= 1:
            errors.append(f"Ratio invalide: {solution.rf}")

        if verbose:
            print("🔍 Validation du design SRCPG:")
            print(f"   Étage 1: Zs={zs}, Zf={zf}, Zp,f={zpf}, m1={module_stage1:.2f}mm")
            print(f"   Étage 2: Zs2={zs2}, Zo={zo}, Zp,o={zpo}, m2={module_stage2:.2f}mm")
            print(f"   Géométrie: P={p}, n={n}")
            print(f"   Ratios: R1={solution.r1:.2f}, R2={solution.r2:.2f}, Rf={solution.rf:.2f}")
            print(f"   Diamètre: Ø≈{solution.approx_overall_diameter_mm:.1f}mm")

            if errors:
                print(f"❌ Erreurs ({len(errors)}):")
                for err in errors:
                    print(f"   - {err}")
            else:
                print("✅ Géométrie valide")

            if warnings:
                print(f"⚠️  Avertissements ({len(warnings)}):")
                for warn in warnings:
                    print(f"   - {warn}")

    except Exception as e:
        errors.append(f"Erreur de calcul: {str(e)}")
        solution = None

    is_valid = len(errors) == 0
    return is_valid, errors, warnings, solution


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

    def is_ratio_ok(self, constraints: SRCPGConstraints) -> bool:
        """Vérifie seulement le ratio."""
        ratio_min = constraints.target_ratio * (1 - constraints.ratio_tolerance)
        ratio_max = constraints.target_ratio * (1 + constraints.ratio_tolerance)
        return ratio_min <= self.rf <= ratio_max

    def is_diameter_ok(self, constraints: SRCPGConstraints) -> bool:
        """Vérifie seulement l'encombrement."""
        return self.approx_overall_diameter_mm <= constraints.max_diameter

    def is_geometry_ok(self, constraints: SRCPGConstraints) -> Tuple[bool, List[str]]:
        """Vérifie seulement les conditions géométriques (divisibilité, coaxialité, etc.)."""
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

    def is_geometry_ok(self, constraints: SRCPGConstraints) -> Tuple[bool, List[str], List[str]]:
        """Vérifie les contraintes géométriques. Retourne (ok, errors, warnings)."""
        errors = []
        warnings = []
        
        # Min dents (avertissement si trop petit, pas erreur)
        for name, z in [("Zs", self.zs), ("Zf", self.zf), ("Zp,f", self.zpf), ("Zs2", self.zs2), ("Zo", self.zo), ("Zp,o", self.zpo)]:
            if z < constraints.min_teeth:
                warnings.append(f"{name}: {z} dents < {constraints.min_teeth} (risque sous-denture)")
            elif z < 12:  # Seuil très bas pour warning fort
                warnings.append(f"{name}: {z} dents très petit")

        # Divisibilités par P
        for name, z in [("Zs", self.zs), ("Zf", self.zf), ("Zs2", self.zs2)]:
            if z % self.p != 0:
                warnings.append(f"{name}={z} non divisible par P={self.p} (équilibrage sous-optimal)")

        # Condition d'assemblage (pratique, plus générale) : (Z_sun + Z_ring) divisible par P
        if (self.zs + self.zf) % self.p != 0:
            errors.append(f"Assemblage étage 1: (Zs+Zf)={self.zs + self.zf} non divisible par P={self.p}")
        if (self.zs2 + self.zo) % self.p != 0:
            errors.append(f"Assemblage étage 2: (Zs2+Zo)={self.zs2 + self.zo} non divisible par P={self.p}")

        # module_stage2 doit être fini et positif
        if not (self.module_stage2 > 0 and np.isfinite(self.module_stage2)):
            errors.append("module_stage2 invalide (<=0 ou non fini)")

        # Contraintes de module pour les deux étages
        if self.module_stage1 < constraints.module_min or self.module_stage1 > constraints.module_max:
            errors.append(f"Module étage 1 hors limites: {self.module_stage1:.2f}mm ∉ [{constraints.module_min:.2f}, {constraints.module_max:.2f}]mm")
        if self.module_stage2 < constraints.module_min or self.module_stage2 > constraints.module_max:
            errors.append(f"Module étage 2 hors limites: {self.module_stage2:.2f}mm ∉ [{constraints.module_min:.2f}, {constraints.module_max:.2f}]mm")

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

        # Contraintes impression 3D
        if constraints.printing_technology != "none":
            # Définir le module minimum selon la technologie : 2x la taille de détail minimale
            min_module = 2 * constraints.min_feature_size
            
            if self.module_stage1 < min_module:
                warnings.append(f"Impression {constraints.printing_technology.upper()}: module_stage1={self.module_stage1:.2f}mm < {min_module:.2f}mm")
            if self.module_stage2 < min_module:
                warnings.append(f"Impression {constraints.printing_technology.upper()}: module_stage2={self.module_stage2:.2f}mm < {min_module:.2f}mm")
            
            # Vérifier les rayons de courbure minimum (approximation pour profil involute)
            min_curvature_radius = 0.38 * min(self.module_stage1, self.module_stage2)  # Rayon de courbure au pied de dent
            if min_curvature_radius < constraints.min_feature_size:
                warnings.append(f"Impression {constraints.printing_technology.upper()}: rayon courbure min≈{min_curvature_radius:.2f}mm < taille détail {constraints.min_feature_size:.2f}mm")

        return len(errors) == 0, errors, warnings

    def is_valid(self, constraints: SRCPGConstraints) -> Tuple[bool, List[str], List[str]]:
        """Vérifie toutes les contraintes. Retourne (valid, errors, warnings)."""
        ratio_ok = self.is_ratio_ok(constraints)
        diam_ok = self.is_diameter_ok(constraints)
        geom_ok, geom_errors, geom_warnings = self.is_geometry_ok(constraints)
        
        all_ok = ratio_ok and diam_ok and geom_ok
        all_errors = []
        all_warnings = geom_warnings.copy()
        
        if not ratio_ok:
            all_errors.append("Ratio hors tolérance")
        if not diam_ok:
            all_errors.append("Encombrement dépassé")
        all_errors.extend(geom_errors)
        
        return all_ok, all_errors, all_warnings

    @property
    def approx_overall_diameter_mm(self) -> float:
        """Diamètre extérieur approximatif du système (au pire des deux couronnes)."""
        od1 = _pitch_diameter_mm(self.zf, self.module_stage1) + 2 * _addendum_mm(self.module_stage1)
        od2 = _pitch_diameter_mm(self.zo, self.module_stage2) + 2 * _addendum_mm(self.module_stage2)
        return max(od1, od2)


class SRCPGDesigner:
    """Recherche de configurations compatibles, basée sur les équations Hartkop + checks pratiques."""

    def __init__(self, constraints: SRCPGConstraints):
        self.constraints = constraints
        self.solutions: List[SRCPGSolution] = []

    def search(self, verbose=False) -> List[SRCPGSolution]:
        c = self.constraints
        self.solutions = []

        # Plage ratio
        ratio_min = c.target_ratio * (1 - c.ratio_tolerance)
        ratio_max = c.target_ratio * (1 + c.ratio_tolerance)

        # Plage de modules pour l'étage 1
        module_step = 0.1  # pas de 0.1 mm/dent
        modules = np.arange(c.module_min, c.module_max + module_step, module_step)

        candidates: List[SRCPGSolution] = []
        
        for m1 in modules:
            # Bornes de dents (heuristiques) dépendent du module
            # - Zs petit aide le ratio
            # - Zf est borné par le diamètre max (OD ~ PD + 2m)
            max_zf = int((c.max_diameter - 2 * _addendum_mm(m1)) / m1)
            max_zf = max(max_zf, c.min_teeth * 2)

            zs_max = min(80, max_zf)  # garde-fou perf

            # Estimation du nombre total d'itérations pour la barre de progression
            zs_range = zs_max - c.min_teeth + 1
            zf_avg_range = max_zf - (c.min_teeth + 2 * c.min_teeth) + 1  # approximatif
            total_estimated = zs_range * zf_avg_range * len(c.n_values)
            counter = 0

            zs_list = list(range(c.min_teeth, zs_max + 1))
            if tqdm:
                zs_iter = tqdm(zs_list, desc=f"Recherche SRCPG (m1={m1:.1f})")
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

                        ok, errs, warns = sol.is_valid(c)
                        
                        if verbose:
                            status = "✅" if ok else ("⚠️" if warns else "❌")
                            print(f"{status} m1={m1:.1f}, Zs={zs:2d}, Zf={zf:2d}, n={n:.2f}, Rf={sol.rf:6.1f}, Ø={sol.approx_overall_diameter_mm:5.1f}mm")
                            if not ok and errs:
                                print(f"    Erreurs: {', '.join(errs[:2])}")  # Top 2 erreurs
                            if warns:
                                print(f"    Avertissements: {', '.join(warns[:2])}")  # Top 2 warnings
                        
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

    def search_ga(self, population_size=100, num_generations=50, verbose=False) -> List[SRCPGSolution]:
        """Recherche de solutions utilisant un algorithme génétique avec pygad.
        
        Args:
            population_size: Taille de la population
            num_generations: Nombre de générations  
            verbose: Si True, affiche une trace des meilleurs paramètres à chaque génération
        """
        if pygad is None:
            raise ImportError("pygad n'est pas installé. Installez-le avec pip install pygad")

        c = self.constraints

        # Plages pour les gènes
        # Utiliser module_max pour les bornes conservatrices (plus grand module = diamètres plus grands)
        zs_min, zs_max = c.min_teeth, min(100, int(c.max_diameter / (2 * c.module_max)))
        zf_max = int((c.max_diameter - 2 * _addendum_mm(c.module_max)) / c.module_max)
        n_min, n_max = min(c.n_values), max(c.n_values)
        m1_min, m1_max = c.module_min, c.module_max

        best_solutions_per_gen = []  # Pour tracer l'évolution
        
        def fitness_func(ga_instance, solution, solution_idx):
            zs = int(solution[0])
            zf = int(solution[1])
            n = solution[2]
            m1 = solution[3]

            # Vérifier que zf >= zs + 2*min_teeth et (zf - zs) pair
            if zf < zs + 2 * c.min_teeth or (zf - zs) % 2 != 0:
                return 0.0

            sol = SRCPGSolution(zs=zs, zf=zf, p=c.num_planets, n=n, module_stage1=m1)
            
            fitness = 0.0
            
            # Vérifications dures (contraintes critiques) - seulement les sommes
            # Condition d'assemblage : (Z_sun + Z_ring) divisible par P
            if (sol.zs + sol.zf) % c.num_planets != 0 or (sol.zs2 + sol.zo) % c.num_planets != 0:
                return 0.0  # Fitness nulle si assemblage impossible
            
            # Priorité 1: Ratio
            if sol.is_ratio_ok(c):
                fitness += 10.0  # Bonus fort pour ratio OK
                ratio_error = abs(sol.rf - c.target_ratio) / c.target_ratio
                fitness += 1.0 / (1.0 + ratio_error)  # Proximité ratio
            else:
                return 0.0  # Si ratio pas OK, fitness nulle
            
            # Priorité 2: Diamètre (avec bonus pour minimisation)
            if sol.is_diameter_ok(c):
                # Bonus de base + bonus proportionnel à la petitesse du diamètre
                diameter_bonus = 5.0 * (1 - sol.approx_overall_diameter_mm / c.max_diameter)
                fitness += diameter_bonus
            
            # Priorité 3: Géométrie (autres contraintes)
            geom_ok, _, geom_warnings = sol.is_geometry_ok(c)
            if geom_ok:
                fitness += 2.0  # Bonus pour géométrie OK
                # Pénalité légère pour warnings
                fitness -= len(geom_warnings) * 0.1
            
            return fitness

        def on_generation(ga_instance):
            """Callback appelé à chaque génération pour tracer l'évolution."""
            if verbose:
                best_solution = ga_instance.best_solution()[0]
                zs = int(best_solution[0])
                zf = int(best_solution[1])
                n = best_solution[2]
                m1 = best_solution[3]
                
                # Créer la solution même si elle n'est pas valide
                sol = SRCPGSolution(zs=zs, zf=zf, p=c.num_planets, n=n, module_stage1=m1)
                best_solutions_per_gen.append(sol)
                
                gen = ga_instance.generations_completed
                fitness = ga_instance.best_solution()[1]
                is_valid, errs, warns = sol.is_valid(c)
                
                status = "✅" if is_valid else ("⚠️" if warns else "❌")
                print(f"Gén {gen:2d}: m1={m1:.2f}, Zs={zs:2d}, Zf={zf:2d}, n={n:.2f}, "
                      f"Rf={sol.rf:6.1f}, Ø={sol.approx_overall_diameter_mm:5.1f}mm, "
                      f"Fitness={fitness:.3f}, {status}")
                if warns:
                    print(f"    Avertissements: {', '.join(warns[:2])}")

        ga_instance = pygad.GA(
            num_generations=num_generations,
            num_parents_mating=20,
            fitness_func=fitness_func,
            sol_per_pop=population_size,
            num_genes=4,
            gene_type=[int, int, float, float],
            gene_space=[
                {'low': zs_min, 'high': zs_max},  # zs
                {'low': zs_min + 2 * c.min_teeth, 'high': zf_max},  # zf min approximatif
                {'low': n_min, 'high': n_max},  # n
                {'low': m1_min, 'high': m1_max}  # m1
            ],
            parent_selection_type="tournament",
            crossover_type="two_points",
            mutation_type="random",
            mutation_num_genes=1,
            keep_parents=5,
            on_generation=on_generation if verbose else None,
            stop_criteria=None
        )

        ga_instance.run()

        # Récupérer les meilleures solutions
        solutions, fitnesses, _ = ga_instance.best_solution()
        best_solutions = []

        # Générer plusieurs solutions à partir des individus
        num_solutions = min(20, population_size)
        for i in range(num_solutions):
            sol_data = solutions[i] if len(solutions.shape) > 1 else solutions
            zs = int(sol_data[0])
            zf = int(sol_data[1])
            n = sol_data[2]
            m1 = sol_data[3]

            sol = SRCPGSolution(zs=zs, zf=zf, p=c.num_planets, n=n, module_stage1=m1)
            is_valid, errs, warns = sol.is_valid(c)
            if is_valid and abs(sol.rf - c.target_ratio) / c.target_ratio <= c.ratio_tolerance:
                best_solutions.append(sol)

        # Trier par proximité ratio
        best_solutions.sort(key=lambda s: abs(s.rf - c.target_ratio))
        self.solutions = best_solutions
        
        # Si aucune solution valide, retourner les meilleures tentatives invalides
        if not best_solutions:
            print(f"\n⚠️ Aucune solution valide trouvée. Voici les meilleures tentatives:")
            # Prendre les top solutions du GA, même invalides
            top_solutions = []
            for i in range(min(10, population_size)):
                sol_data = solutions[i] if len(solutions.shape) > 1 else solutions
                zs = int(sol_data[0])
                zf = int(sol_data[1])
                n = sol_data[2]
                m1 = sol_data[3]
                sol = SRCPGSolution(zs=zs, zf=zf, p=c.num_planets, n=n, module_stage1=m1)
                top_solutions.append(sol)
            
            for i, sol in enumerate(top_solutions):
                is_valid, errors, warns = sol.is_valid(c)
                status = "✅" if is_valid else ("⚠️" if warns else "❌")
                print(f"{status} Tentative {i+1}: Zs={sol.zs}, Zf={sol.zf}, n={sol.n:.2f}, "
                      f"Rf={sol.rf:.1f}, Ø={sol.approx_overall_diameter_mm:.1f}mm")
                if not is_valid and errors:
                    print(f"    Erreurs: {', '.join(errors[:3])}")  # Top 3 erreurs
                if warns:
                    print(f"    Avertissements: {', '.join(warns[:3])}")  # Top 3 warnings
            return top_solutions  # Retourner quand même les meilleures tentatives
        
        print(f"✅ SRCPG GA: {len(self.solutions)} solutions valides trouvées")
        return self.solutions


class SRCPGIterativeDesigner:
    """Designer itératif inspiré du dimensionnement de ressort : analyse et correction."""

    def __init__(self, constraints: SRCPGConstraints):
        self.constraints = constraints
        self.solution = None
        self.trace = None

    def init_solution(self, zs=20, zf=60, n=1.5):
        """Initialiser une solution de départ."""
        self.solution = SRCPGSolution(zs=zs, zf=zf, p=self.constraints.num_planets, n=n, module_stage1=self.constraints.module_stage1)

    def init_trace(self):
        """Initialiser la trace pour suivre les itérations."""
        class Trace:
            def __init__(self):
                self.iteration = 0
                self.zs = []
                self.zf = []
                self.n = []
                self.rf = []
                self.valid = []
                self.errors = []

        self.trace = Trace()

    def inc_trace(self):
        """Incrémenter la trace."""
        if self.trace:
            self.trace.zs.append(self.solution.zs)
            self.trace.zf.append(self.solution.zf)
            self.trace.n.append(self.solution.n)
            self.trace.rf.append(self.solution.rf)
            valid, errors = self.solution.is_valid(self.constraints)
            self.trace.valid.append(valid)
            self.trace.errors.append(errors)
            self.trace.iteration += 1

    def analyze_ratio(self):
        """Analyser l'écart au ratio cible. Retourne <1 si OK, >1 si trop petit, <1 si trop grand?"""
        if self.solution.rf < self.constraints.target_ratio * (1 - self.constraints.ratio_tolerance):
            return self.solution.rf / (self.constraints.target_ratio * (1 - self.constraints.ratio_tolerance))  # <1 si trop petit
        elif self.solution.rf > self.constraints.target_ratio * (1 + self.constraints.ratio_tolerance):
            return (self.constraints.target_ratio * (1 + self.constraints.ratio_tolerance)) / self.solution.rf  # <1 si trop grand
        else:
            return 1.0  # OK

    def analyze_diameter(self):
        """Analyser l'encombrement."""
        return self.solution.approx_overall_diameter_mm / self.constraints.max_diameter  # <=1 OK

    def analyze_geometry(self):
        """Analyser la validité géométrique."""
        geom_ok, _ = self.solution.is_geometry_ok(self.constraints)
        return 1.0 if geom_ok else 0.0

    def correct_ratio(self):
        """Corriger le ratio en ajustant zs, zf ou n."""
        target = self.constraints.target_ratio
        tol = self.constraints.ratio_tolerance
        rf = self.solution.rf

        if rf < target * (1 - tol):
            # Rf trop petit : augmenter Rf en diminuant zs ou augmentant zf
            if self.solution.zs > self.constraints.min_teeth:
                self.solution.zs -= 1  # Diminuer zs pour augmenter Rf
            elif self.solution.zf < 200:  # Limite arbitraire
                self.solution.zf += 2  # Augmenter zf (doit rester pair avec zs)
        elif rf > target * (1 + tol):
            # Rf trop grand : diminuer Rf en augmentant zs ou diminuant zf
            if self.solution.zs < 100:
                self.solution.zs += 1  # Augmenter zs pour diminuer Rf
            elif self.solution.zf > self.solution.zs + 2 * self.constraints.min_teeth:
                self.solution.zf -= 2  # Diminuer zf
            else:
                # Si pas possible, changer n vers une valeur plus petite
                current_n = self.solution.n
                possible_n = [n for n in self.constraints.n_values if n < current_n]
                if possible_n:
                    self.solution.n = max(possible_n)  # Prendre le plus grand < current

    def correct_diameter(self, factor=1.1):
        """Corriger le diamètre en diminuant zf."""
        if self.solution.approx_overall_diameter_mm > self.constraints.max_diameter:
            self.solution.zf = max(self.solution.zs + 2 * self.constraints.min_teeth, int(self.solution.zf * 0.95))

    def correct_validity(self):
        """Corriger la validité en ajustant n ou autres."""
        valid, errors = self.solution.is_valid(self.constraints)
        if not valid:
            # Essayer de changer n
            for n in self.constraints.n_values:
                if n != self.solution.n:
                    test_sol = SRCPGSolution(zs=self.solution.zs, zf=self.solution.zf, p=self.constraints.num_planets, n=n, module_stage1=self.constraints.module_stage1)
                    if test_sol.is_valid(self.constraints)[0]:
                        self.solution = test_sol
                        break

    def iterate(self, max_iter=50):
        """Processus itératif."""
        self.init_trace()
        for _ in range(max_iter):
            self.inc_trace()

            ratio_score = self.analyze_ratio()
            diam_score = self.analyze_diameter()
            geom_score = self.analyze_geometry()

            if ratio_score >= 0.95 and diam_score <= 1.05 and geom_score == 1.0:
                break  # Converge

            if geom_score < 1.0:
                self.correct_validity()
            if diam_score > 1.0:
                self.correct_diameter()
            if ratio_score < 1.0:
                self.correct_ratio()

        return self.solution

    def print_trace(self):
        """Affiche la trace des itérations."""
        if not self.trace or len(self.trace.zs) == 0:
            print("Aucune trace disponible.")
            return

        print("Trace des itérations :")
        print("=" * 100)
        print(f"{'Itér':>4} | {'Zs':>4} | {'Zf':>4} | {'n':>5} | {'Rf':>8} | {'Valide':>6} | Erreurs")
        print("-" * 100)
        for i in range(len(self.trace.zs)):
            errors_str = "; ".join(self.trace.errors[i]) if self.trace.errors[i] else "OK"
            print(f"{i+1:>4} | {self.trace.zs[i]:>4} | {self.trace.zf[i]:>4} | {self.trace.n[i]:>5.1f} | {self.trace.rf[i]:>8.2f} | {int(self.trace.valid[i]):>6} | {errors_str}")
        print("=" * 100)


