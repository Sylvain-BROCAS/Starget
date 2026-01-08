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
from typing import Tuple, List, Optional
import matplotlib.pyplot as plt


@dataclass
class SRCPGConstraints:
    """
    Contraintes d'encombrement pour la conception d'un SRCPG
    
    L'utilisateur spécifie:
    - Le diamètre max (encombrement)
    - Le module (taille des dents)
    - Le ratio cible
    - Le nombre de satellites
    
    Le designer trouve les configurations valides.
    """
    max_diameter: float      # mm - Diamètre maximum du système
    module: float            # mm - Module de l'engrenage
    target_ratio: float      # Ratio de réduction cible (positif)
    ratio_tolerance: float = 0.1  # Tolérance sur le ratio (±10% par défaut)
    num_planets: int = 3     # Nombre de satellites
    min_teeth: int = 12      # Nombre minimum de dents (évite interférence)
    exploration_margin: float = 2.0  # Facteur d'exploration (autorise temporairement des solutions plus grandes)
    stage_multiplier: float = 1.0    # Multiplicateur n pour l'étage 2 (inspiré du CSV)
    
    @property
    def max_ring_teeth(self) -> int:
        """Nombre max de dents pour la couronne (basé sur diamètre max)"""
        return int((self.max_diameter - 2 * self.module) / self.module)
    
    @property
    def exploration_max_ring_teeth(self) -> int:
        """Nombre max de dents pour l'exploration (avec marge)"""
        return int((self.max_diameter * self.exploration_margin - 2 * self.module) / self.module)


@dataclass
class SRCPGSolution:
    """
    Une solution valide pour un SRCPG
    
    Les dents des planètes sont CALCULÉES à partir de Z_S, Z_F, Z_O:
        - Z_{P,F} = (Z_F - Z_S) / 2  (denture planète côté couronne fixe)
        - Z_{P,O} est déduit de la contrainte SRCPG "même centre de planète" (planète compound)
            avec un engrènement interne avec la couronne de sortie :
            Z_{P,O} = Z_PF * n (inspiré du CSV, avec n multiplicateur)
    """
    sun_teeth: int           # Z_S - Dents du soleil
    fixed_ring_teeth: int    # Z_F - Dents de la couronne fixe
    output_ring_teeth: int   # Z_O - Dents de la couronne de sortie
    num_planets: int         # Nombre de satellites
    module: float            # mm
    stage_multiplier: float  # n - Multiplicateur pour l'étage 2
    
    # Calculés automatiquement
    planet_teeth_fixed: int = field(init=False)
    planet_teeth_output: int = field(init=False)
    ratio: float = field(init=False)
    
    def __post_init__(self):
        """Calculer les dents des planètes et le ratio"""
        # Planète compound (double denture) : Z_{P,F} et Z_{P,O} partagent le même centre.
        # Approche inspirée du CSV : Z_{P,F}=(Z_F-Z_S)/2, Z_{P,O}=Z_{P,F}*n
        self.planet_teeth_fixed = (self.fixed_ring_teeth - self.sun_teeth) // 2
        self.planet_teeth_output = round(self.planet_teeth_fixed * self.stage_multiplier)
        self.ratio = self._calculate_ratio()
    
    def _calculate_ratio(self) -> float:
        """
        Formule de Willis: i = (1 + Z_F/Z_S) / (1 - Z_F/Z_O)
        """
        numerator = 1 + self.fixed_ring_teeth / self.sun_teeth
        denominator = 1 - self.fixed_ring_teeth / self.output_ring_teeth
        
        if abs(denominator) < 1e-10:
            return float('inf')
        return numerator / denominator
    
    def is_valid(self, min_teeth: int = 12) -> Tuple[bool, List[str]]:
        """Vérifier si cette solution est géométriquement valide"""
        errors = []

        # 0. Base SRCPG : les deux couronnes doivent être différentes
        if self.output_ring_teeth == self.fixed_ring_teeth:
            errors.append("SRCPG: Z_O doit être différent de Z_F")
        
        # 1. Vérifier que Z_{P,F} et Z_{P,O} sont entiers (parité) et compatibles coaxialement
        if (self.fixed_ring_teeth - self.sun_teeth) % 2 != 0:
            errors.append(
                f"Z_PF non entier: (Z_F - Z_S) = {self.fixed_ring_teeth - self.sun_teeth} n'est pas pair"
            )

        if (2 * self.output_ring_teeth - self.fixed_ring_teeth - self.sun_teeth) % 2 != 0:
            errors.append(
                "Z_PO non entier: (2·Z_O - Z_F - Z_S) = "
                f"{2 * self.output_ring_teeth - self.fixed_ring_teeth - self.sun_teeth} n'est pas pair"
            )

        # Recalculer de façon sûre si la parité est OK, pour éviter les effets de // sur valeurs invalides
        if not any(msg.startswith("Z_PF non entier") for msg in errors):
            self.planet_teeth_fixed = (self.fixed_ring_teeth - self.sun_teeth) // 2

        if not any(msg.startswith("Z_PO non entier") for msg in errors):
            self.planet_teeth_output = (2 * self.output_ring_teeth - self.fixed_ring_teeth - self.sun_teeth) // 2

        # Planète compound : deux dentures différentes (sinon pas de différentiel SRCPG)
        if self.planet_teeth_output == self.planet_teeth_fixed:
            errors.append("SRCPG: Z_PO doit être différent de Z_PF")

        # Dents positives
        if self.planet_teeth_fixed <= 0:
            errors.append(f"Planète (fixe): {self.planet_teeth_fixed} dents <= 0")

        if self.planet_teeth_output <= 0:
            errors.append(f"Planète (sortie): {self.planet_teeth_output} dents <= 0")
        
        # 2. Vérifier le nombre minimum de dents
        if self.sun_teeth < min_teeth:
            errors.append(f"Soleil: {self.sun_teeth} dents < {min_teeth} min")
        
        if self.planet_teeth_fixed < min_teeth:
            errors.append(f"Planète (fixe): {self.planet_teeth_fixed} dents < {min_teeth} min")
        
        if self.planet_teeth_output < min_teeth:
            errors.append(f"Planète (sortie): {self.planet_teeth_output} dents < {min_teeth} min")
        
        # 3. Condition d'assemblage pour couronne fixe
        if (self.fixed_ring_teeth + self.sun_teeth) % self.num_planets != 0:
            errors.append(f"Assemblage fixe: (Z_F + Z_S) = {self.fixed_ring_teeth + self.sun_teeth} "
                         f"non divisible par {self.num_planets}")
        
        # 4. Condition d'assemblage pour couronne sortie
        if (self.output_ring_teeth + self.sun_teeth) % self.num_planets != 0:
            errors.append(f"Assemblage sortie: (Z_O + Z_S) = {self.output_ring_teeth + self.sun_teeth} "
                         f"non divisible par {self.num_planets}")
        
        # 5. Vérifier que les planètes ne se touchent pas
        if self.num_planets > 1:
            center_distance = (self.sun_teeth + self.planet_teeth_fixed) * self.module / 2
            max_planet_radius = max(self.planet_teeth_fixed, self.planet_teeth_output) * self.module / 2
            angle_between = 2 * np.pi / self.num_planets
            min_spacing = 2 * center_distance * np.sin(angle_between / 2)
            
            if min_spacing < 2 * max_planet_radius * 1.1:
                errors.append(f"Planètes trop proches: espacement {min_spacing:.1f}mm < "
                             f"2×rayon {2*max_planet_radius:.1f}mm")
        
        return len(errors) == 0, errors
    
    @property
    def pitch_diameter_sun(self) -> float:
        return self.sun_teeth * self.module
    
    @property
    def pitch_diameter_fixed_ring(self) -> float:
        return self.fixed_ring_teeth * self.module
    
    @property
    def pitch_diameter_output_ring(self) -> float:
        return self.output_ring_teeth * self.module
    
    @property
    def overall_diameter(self) -> float:
        return max(self.pitch_diameter_fixed_ring, self.pitch_diameter_output_ring) + 2 * self.module
    
    @property
    def center_distance(self) -> float:
        return (self.sun_teeth + self.planet_teeth_fixed) * self.module / 2


class SRCPGDesigner:
    """Outil de conception SRCPG basé sur les contraintes d'encombrement"""
    
    def __init__(self, constraints: SRCPGConstraints):
        self.constraints = constraints
        self.solutions: List[SRCPGSolution] = []
    
    def search(self) -> List[SRCPGSolution]:
        """Rechercher toutes les configurations valides
        
        Stratégie d'exploration élargie (inspirée du simplexe):
        1. Explorer un espace plus large que les contraintes (marge d'exploration)
        2. Ne retenir que les solutions respectant les contraintes finales
        3. Permet de trouver des optima locaux même si l'espace faisable est discontinu
        """
        self.solutions = []
        c = self.constraints
        
        # Calculer les limites de ratio (gérer les ratios positifs et négatifs)
        if c.target_ratio > 0:
            ratio_min = c.target_ratio * (1 - c.ratio_tolerance)
            ratio_max = c.target_ratio * (1 + c.ratio_tolerance)
        else:
            ratio_min = c.target_ratio * (1 + c.ratio_tolerance)  # plus négatif
            ratio_max = c.target_ratio * (1 - c.ratio_tolerance)  # moins négatif
        
        print(f"🔍 Recherche avec ratio cible {c.target_ratio:.1f}, plage: [{ratio_min:.1f}, {ratio_max:.1f}]")
        
        # EXPLORATION ÉLARGIE : utiliser la marge pour explorer plus largement
        z_s_max = min(c.exploration_max_ring_teeth // 3, 80)  # limite performance
        z_f_max_exploration = c.exploration_max_ring_teeth
        z_o_max_exploration = c.exploration_max_ring_teeth
        
        print(f"🔍 Exploration large: Z_S=[{c.min_teeth}, {z_s_max}], Z_F/Z_O=[{c.min_teeth*2}, {z_f_max_exploration}]")
        print(f"🔍 Contraintes finales: Ø ≤ {c.max_diameter}mm")
        
        candidates = []  # Stocker tous les candidats valides géométriquement
        
        for z_s in range(c.min_teeth, z_s_max + 1):
            z_f_min = z_s + 2 * c.min_teeth
            z_f_max_eff = min(z_f_max_exploration, z_s + int(c.max_diameter * c.exploration_margin / c.module / 2))
            
            for z_f in range(z_f_min, z_f_max_eff + 1):
                if (z_f - z_s) % 2 != 0:
                    continue
                if (z_f + z_s) % c.num_planets != 0:
                    continue
                
                z_o_min = z_s + 2 * c.min_teeth
                z_o_max_eff = min(z_o_max_exploration, z_f + int(c.max_diameter * c.exploration_margin / c.module / 4))
                
                for z_o in range(z_o_min, z_o_max_eff + 1):
                    # Base SRCPG : Z_O != Z_F
                    if z_o == z_f:
                        continue

                    # Coaxialité SRCPG : Z_PO = (2·Z_O - Z_F - Z_S)/2 doit être entier
                    if (2 * z_o - z_f - z_s) % 2 != 0:
                        continue

                    if (z_o + z_s) % c.num_planets != 0:
                        continue
                    
                    sol = SRCPGSolution(
                        sun_teeth=z_s,
                        fixed_ring_teeth=z_f,
                        output_ring_teeth=z_o,
                        num_planets=c.num_planets,
                        module=c.module
                    )
                    
                    # Vérifier la validité géométrique (même pour l'exploration)
                    is_valid, _ = sol.is_valid(c.min_teeth)
                    if is_valid:
                        candidates.append(sol)
        
        # FILTRAGE FINAL : ne garder que les solutions respectant les contraintes
        for sol in candidates:
            # Vérifier le ratio (accepter positifs ET négatifs selon la cible)
            if c.target_ratio > 0:
                if not (ratio_min <= sol.ratio <= ratio_max):
                    continue
            else:
                if not (ratio_min <= sol.ratio <= ratio_max):
                    continue
            
            # Vérifier le diamètre FINAL (contrainte dure)
            if sol.overall_diameter > c.max_diameter:
                continue
            
            self.solutions.append(sol)
        
        # Trier par proximité au ratio cible (tenir compte du signe)
        self.solutions.sort(key=lambda s: abs(s.ratio - c.target_ratio))
        
        print(f"✅ {len(candidates)} candidats explorés, {len(self.solutions)} solutions finales")
        return self.solutions
    
    def print_solutions(self, max_display: int = 20):
        """Afficher les solutions trouvées"""
        if not self.solutions:
            print("❌ Aucune solution trouvée avec ces contraintes.")
            return
        
        print(f"✅ {len(self.solutions)} solutions trouvées!\n")
        print("=" * 90)
        print(f"{'#':>3} | {'Z_S':>4} | {'Z_F':>4} | {'Z_O':>4} | {'Z_PF':>4} | {'Z_PO':>4} | "
              f"{'Ratio':>10} | {'Ø max':>8} | {'Erreur':>8}")
        print("-" * 90)
        
        for i, sol in enumerate(self.solutions[:max_display]):
            # Calcul d'erreur tenant compte du signe
            error = sol.ratio - self.constraints.target_ratio
            error_pct = (error / abs(self.constraints.target_ratio)) * 100
            print(f"{i+1:>3} | {sol.sun_teeth:>4} | {sol.fixed_ring_teeth:>4} | {sol.output_ring_teeth:>4} | "
                  f"{sol.planet_teeth_fixed:>4} | {sol.planet_teeth_output:>4} | "
                  f"{sol.ratio:>10.2f} | {sol.overall_diameter:>7.1f}mm | {error_pct:>+7.2f}%")
        
        if len(self.solutions) > max_display:
            print(f"... et {len(self.solutions) - max_display} autres solutions")
        print("=" * 90)
    
    def get_best_solution(self) -> Optional[SRCPGSolution]:
        """Retourner la meilleure solution"""
        return self.solutions[0] if self.solutions else None
    
    def print_detailed_solution(self, index: int = 0):
        """Afficher les détails d'une solution"""
        if not self.solutions or index >= len(self.solutions):
            print("❌ Solution non disponible")
            return
        
        sol = self.solutions[index]
        
        print("=" * 65)
        print("ENGRENAGE PLANÉTAIRE COMPOUND À DOUBLE COURONNE (SRCPG)")
        print("=" * 65)
        print("\n📋 ARCHITECTURE:")
        print("  Soleil (entrée) → Planète (double denture) → Couronne fixe")
        print("                                            ↘ Couronne sortie")
        print(f"\n📋 DENTURES:")
        print(f"  • Z_S (soleil):           {sol.sun_teeth}")
        print(f"  • Z_F (couronne fixe):    {sol.fixed_ring_teeth}")
        print(f"  • Z_O (couronne sortie):  {sol.output_ring_teeth}")
        print(f"  • Z_PF (planète fixe):    {sol.planet_teeth_fixed}  ← (Z_F-Z_S)/2")
        print(f"  • Z_PO (planète sortie):  {sol.planet_teeth_output}  ← (2·Z_O-Z_F-Z_S)/2")
        print(f"  • Satellites:             {sol.num_planets}")
        print(f"  • Module:                 {sol.module} mm")
        print(f"\n📐 DIMENSIONS:")
        print(f"  • Ø soleil:       {sol.pitch_diameter_sun:.2f} mm")
        print(f"  • Ø cour. fixe:   {sol.pitch_diameter_fixed_ring:.2f} mm")
        print(f"  • Ø cour. sortie: {sol.pitch_diameter_output_ring:.2f} mm")
        print(f"  • Ø total:        {sol.overall_diameter:.2f} mm")
        print(f"\n⚙️  RATIO (Willis): i = {sol.ratio:.4f}")
        if sol.ratio > 0:
            print(f"  → Réduction {abs(sol.ratio):.2f}:1 (sens direct)")
        else:
            print(f"  → Réduction {abs(sol.ratio):.2f}:1 (sens inverse)")
    
    def visualize_solution(self, index: int = 0, ax=None) -> plt.Figure:
        """Visualiser une solution"""
        if not self.solutions or index >= len(self.solutions):
            return None
        
        sol = self.solutions[index]
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))
        else:
            fig = ax.get_figure()
        
        colors = {'sun': '#FF6B6B', 'fixed': '#4ECDC4', 'output': '#45B7D1', 
                  'planet': '#FFE66D', 'carrier': '#95E1D3'}
        
        ax.add_patch(Circle((0, 0), sol.pitch_diameter_fixed_ring/2, 
                           fill=False, edgecolor=colors['fixed'], linewidth=3, 
                           label=f'Couronne fixe (Z={sol.fixed_ring_teeth})'))
        ax.add_patch(Circle((0, 0), sol.pitch_diameter_output_ring/2, 
                           fill=False, edgecolor=colors['output'], linewidth=2.5, linestyle='--',
                           label=f'Couronne sortie (Z={sol.output_ring_teeth})'))
        ax.add_patch(Circle((0, 0), sol.pitch_diameter_sun/2,
                           fill=True, facecolor=colors['sun'], edgecolor='darkred', 
                           linewidth=2, alpha=0.7, label=f'Soleil (Z={sol.sun_teeth})'))
        
        for i in range(sol.num_planets):
            angle = np.radians(i * 360 / sol.num_planets)
            cx, cy = sol.center_distance * np.cos(angle), sol.center_distance * np.sin(angle)
            ax.add_patch(Circle((cx, cy), sol.planet_teeth_fixed * sol.module / 2,
                               fill=True, facecolor=colors['planet'], edgecolor='orange',
                               linewidth=1.5, alpha=0.6, 
                               label=f'Planète (Z={sol.planet_teeth_fixed}/{sol.planet_teeth_output})' if i == 0 else ''))
            ax.plot([0, cx], [0, cy], 'k--', alpha=0.3, linewidth=0.5)
        
        ax.add_patch(Circle((0, 0), sol.center_distance,
                           fill=False, edgecolor=colors['carrier'], linewidth=2, linestyle='-.'))
        
        margin = sol.overall_diameter / 2 * 0.15
        max_dim = sol.overall_diameter / 2 + margin
        ax.set_xlim(-max_dim, max_dim)
        ax.set_ylim(-max_dim, max_dim)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=8)
        ax.set_title(f'SRCPG - Ratio {sol.ratio:.1f}:1 | Ø{sol.overall_diameter:.1f}mm', fontweight='bold')
        
        return fig


def animate_srcpg_standalone(sun_teeth: int, fixed_ring_teeth: int, output_ring_teeth: int, 
                           num_planets: int = 3, module: float = 2.0,
                           num_frames: int = 120, interval: int = 50):
    """
    Fonction standalone pour dessiner et animer un SRCPG à partir de paramètres donnés.
    
    Args:
        sun_teeth: Nombre de dents du soleil (Z_S)
        fixed_ring_teeth: Nombre de dents de la couronne fixe (Z_F)
        output_ring_teeth: Nombre de dents de la couronne de sortie (Z_O)
        num_planets: Nombre de planètes
        module: Module des dents (mm)
        num_frames: Nombre de frames pour l'animation
        interval: Intervalle entre frames (ms)
    
    Returns:
        matplotlib.animation.FuncAnimation: Animation du SRCPG
    """
    from matplotlib.animation import FuncAnimation
    from matplotlib.patches import Wedge
    
    # Créer la solution SRCPG
    solution = SRCPGSolution(
        sun_teeth=sun_teeth,
        fixed_ring_teeth=fixed_ring_teeth,
        output_ring_teeth=output_ring_teeth,
        num_planets=num_planets,
        module=module
    )
    
    # Vérifier que la solution est valide
    is_valid, errors = solution.is_valid()
    if not is_valid:
        print("❌ Configuration invalide:")
        for error in errors:
            print(f"   • {error}")
        return None
    
    print("✅ Configuration valide:")
    print(f"   • Soleil: Z_S = {solution.sun_teeth} dents")
    print(f"   • Couronne fixe: Z_F = {solution.fixed_ring_teeth} dents")
    print(f"   • Couronne sortie: Z_O = {solution.output_ring_teeth} dents")
    print(f"   • Planètes: {solution.num_planets} × (Z_P = {solution.planet_teeth_fixed}/{solution.planet_teeth_output})")
    print(f"   • Ratio: {solution.ratio:.3f}:1")
    print(f"   • Diamètre total: {solution.overall_diameter:.1f} mm")
    print(f"\n🎬 Animation en cours...\n")
    
    # Créer la figure
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # Couleurs
    colors = {'sun': '#FF6B6B', 'fixed': '#4ECDC4', 'output': '#45B7D1', 
              'planet': '#FFE66D', 'carrier': '#95E1D3'}
    
    # Éléments statiques
    # Couronne fixe (toujours immobile)
    fixed_ring = Circle((0, 0), solution.pitch_diameter_fixed_ring/2, 
                       fill=False, edgecolor=colors['fixed'], linewidth=3, 
                       label=f'Couronne fixe (Z={solution.fixed_ring_teeth})')
    ax.add_patch(fixed_ring)
    
    # Cercle du porte-satellites (toujours immobile dans cette configuration)
    carrier_circle = Circle((0, 0), solution.center_distance,
                           fill=False, edgecolor=colors['carrier'], linewidth=2, linestyle='-.',
                           label='Porte-satellites')
    ax.add_patch(carrier_circle)
    
    # Éléments mobiles
    # Soleil (entrée - tourne)
    sun = Circle((0, 0), solution.pitch_diameter_sun/2,
                fill=True, facecolor=colors['sun'], edgecolor='darkred', 
                linewidth=2, alpha=0.7, label=f'Soleil (Z={solution.sun_teeth})')
    ax.add_patch(sun)
    
    # Couronne de sortie (split ring - sortie lente)
    split_angle = 30  # angle de fente en degrés
    output_ring = Wedge((0, 0), solution.pitch_diameter_output_ring/2, 
                       0, 360-split_angle, width=3, 
                       fill=False, edgecolor=colors['output'], linewidth=2.5, linestyle='--',
                       label=f'Couronne sortie (Z={solution.output_ring_teeth})')
    ax.add_patch(output_ring)
    
    # Planètes
    planets = []
    planet_lines = []  # lignes reliant soleil aux planètes
    for i in range(solution.num_planets):
        angle = np.radians(i * 360 / solution.num_planets)
        cx, cy = solution.center_distance * np.cos(angle), solution.center_distance * np.sin(angle)
        planet = Circle((cx, cy), solution.planet_teeth_fixed * solution.module / 2,
                       fill=True, facecolor=colors['planet'], edgecolor='orange',
                       linewidth=1.5, alpha=0.6, 
                       label=f'Planète (Z={solution.planet_teeth_fixed}/{solution.planet_teeth_output})' if i == 0 else '')
        ax.add_patch(planet)
        planets.append(planet)
        
        # Ligne reliant soleil à planète
        line, = ax.plot([0, cx], [0, cy], 'k--', alpha=0.3, linewidth=0.5)
        planet_lines.append(line)
    
    # Marqueurs de rotation
    sun_marker, = ax.plot([solution.pitch_diameter_sun/2 * 0.8], [0], 'ko', 
                         markersize=8, label='Position soleil')
    output_marker, = ax.plot([solution.pitch_diameter_output_ring/2 * 0.9], [0], 's', 
                            color=colors['output'], markersize=10, label='Position sortie')
    
    # Texte informatif
    info_text = ax.text(-solution.overall_diameter/2 * 0.8, -solution.overall_diameter/2 * 0.8, '',
                       fontsize=10, family='monospace', verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Formatage
    margin = solution.overall_diameter / 2 * 0.15
    max_dim = solution.overall_diameter / 2 + margin
    ax.set_xlim(-max_dim, max_dim)
    ax.set_ylim(-max_dim, max_dim)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=8)
    ax.set_xlabel('X (mm)', fontsize=10)
    ax.set_ylabel('Y (mm)', fontsize=10)
    
    def init():
        return [sun_marker, output_marker, info_text]
    
    def animate(frame):
        # Angle d'entrée (soleil) - rotation complète en num_frames
        sun_angle = frame * 360 / num_frames
        
        # Calcul des vitesses angulaires selon la mécanique des engrenages
        # ω_o = ω_s * (ratio) - pour la couronne de sortie
        output_angle = sun_angle * solution.ratio
        
        # Position des planètes (elles orbitent et tournent)
        # Vitesse orbitale des planètes: ω_p_orbital = -ω_s * Z_s / Z_p
        planet_orbital_ratio = -solution.sun_teeth / solution.planet_teeth_fixed
        planet_orbital_angle = sun_angle * planet_orbital_ratio
        
        # Vitesse de rotation propre des planètes: ω_p_spin = ω_s * (Z_s + Z_f) / Z_p
        planet_spin_ratio = (solution.sun_teeth + solution.fixed_ring_teeth) / solution.planet_teeth_fixed
        planet_spin_angle = sun_angle * planet_spin_ratio
        
        # Mettre à jour la couronne de sortie (split ring)
        output_ring.set_theta1(output_angle)
        output_ring.set_theta2(output_angle + 360 - split_angle)
        
        # Mettre à jour les planètes
        for i, planet in enumerate(planets):
            # Position orbitale
            orbital_angle = np.radians(i * 360 / solution.num_planets + planet_orbital_angle)
            cx = solution.center_distance * np.cos(orbital_angle)
            cy = solution.center_distance * np.sin(orbital_angle)
            
            # Le cercle de la planète reste centré sur sa position orbitale
            planet.set_center((cx, cy))
            
            # Mettre à jour la ligne reliant soleil à planète
            planet_lines[i].set_data([0, cx], [0, cy])
        
        # Mettre à jour les marqueurs
        sun_marker_angle = np.radians(sun_angle)
        sun_marker.set_data([solution.pitch_diameter_sun/2 * 0.8 * np.cos(sun_marker_angle)],
                           [solution.pitch_diameter_sun/2 * 0.8 * np.sin(sun_marker_angle)])
        
        output_marker_angle = np.radians(output_angle)
        output_marker.set_data([solution.pitch_diameter_output_ring/2 * 0.9 * np.cos(output_marker_angle)],
                              [solution.pitch_diameter_output_ring/2 * 0.9 * np.sin(output_marker_angle)])
        
        # Mettre à jour le titre et le texte
        ax.set_title(f'SRCPG Animation - Ratio {solution.ratio:.1f}:1\n'
                    f'Soleil: {sun_angle:.1f}° | Sortie: {output_angle:.1f}°', 
                    fontsize=14, fontweight='bold')
        
        info_text.set_text(
            f'SRCPG Animation:\n'
            f'  • Soleil (entrée): {sun_angle:.1f}°\n'
            f'  • Sortie: {output_angle:.1f}°\n'
            f'  • Ratio: {solution.ratio:.2f}:1\n'
            f'  • Frame: {frame}/{num_frames}\n'
            f'  • Z: S={solution.sun_teeth}, F={solution.fixed_ring_teeth}, O={solution.output_ring_teeth}'
        )
        
        return [sun_marker, output_marker, info_text] + planet_lines
    
    anim = FuncAnimation(fig, animate, init_func=init, frames=num_frames,
                        interval=interval, blit=False)
    
    plt.close(fig)  # Évite l'affichage statique
    return anim


# ============================================================
# EXEMPLE D'UTILISATION
# ============================================================
if __name__ == "__main__":
    print("🔬 SRCPG Designer - Exploration élargie (style simplexe)\n")
    
    # Test avec exploration élargie
    test_cases = [
        {"name": "Exploration normale", "max_diameter": 60.0, "exploration_margin": 1.0},
        {"name": "Exploration élargie x2", "max_diameter": 60.0, "exploration_margin": 2.0},
        {"name": "Exploration élargie x3", "max_diameter": 60.0, "exploration_margin": 3.0},
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"TEST {i+1}: {test['name']}")
        print(f"{'='*60}")
        
        # Définir les contraintes
        constraints = SRCPGConstraints(
            max_diameter=test["max_diameter"],  # mm
            module=0.5,                        # mm
            target_ratio=100.0,                # ratio cible
            ratio_tolerance=0.1,               # ±10%
            num_planets=3,
            min_teeth=12,
            exploration_margin=test["exploration_margin"],  # marge d'exploration
        )
        
        print(f"📋 Contraintes: Ø≤{constraints.max_diameter}mm, m={constraints.module}mm, "
              f"ratio≈{constraints.target_ratio} (±{constraints.ratio_tolerance*100:.0f}%)")
        print(f"🔍 Marge d'exploration: x{constraints.exploration_margin:.1f}")
        print("")
        
        # Rechercher les solutions
        designer = SRCPGDesigner(constraints)
        solutions = designer.search()
        
        if solutions:
            designer.print_solutions(5)  # Afficher seulement les 5 meilleures
            print(f"\n📊 Résumé: {len(solutions)} solutions, meilleure: "
                  f"ratio={solutions[0].ratio:.2f}, Ø={solutions[0].overall_diameter:.1f}mm")
        else:
            print("❌ Aucune solution trouvée")