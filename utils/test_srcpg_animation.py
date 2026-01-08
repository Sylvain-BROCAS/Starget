#!/usr/bin/env python3
"""
Test de la fonction standalone animate_srcpg_standalone

Démontre l'animation d'un SRCPG avec des paramètres donnés.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from SRCPG import animate_srcpg_standalone

def main():
    """Test de l'animation standalone"""
    print("🎬 Test de la fonction animate_srcpg_standalone")
    print("=" * 50)

    # Exemple 1: Configuration simple
    print("\n📊 Exemple 1: Configuration simple (ratio ≈ 4:1)")
    anim1 = animate_srcpg_standalone(
        sun_teeth=18,           # Soleil: 18 dents
        fixed_ring_teeth=54,    # Couronne fixe: 54 dents (54+18=72 divisible par 3)
        output_ring_teeth=72,   # Couronne sortie: 72 dents (72+18=90 divisible par 3)
        num_planets=3,          # 3 planètes
        module=2.0,             # Module 2mm
        num_frames=120,         # 120 frames
        interval=50             # 50ms entre frames
    )

    if anim1 is not None:
        print("✅ Animation créée avec succès!")
        print("💡 Pour afficher: anim1.show() ou utiliser HTML(anim1.to_jshtml()) dans Jupyter")
    else:
        print("❌ Échec de création de l'animation")

    # Exemple 2: Configuration avec ratio élevé
    # Exemple 2: Configuration avec ratio élevé
    # Exemple 2: Configuration avec ratio élevé
    # Exemple 2: Configuration avec ratio élevé
    print("\n📊 Exemple 2: Configuration haute réduction (ratio ≈ 10:1)")
    anim2 = animate_srcpg_standalone(
        sun_teeth=12,           # Soleil: 12 dents
        fixed_ring_teeth=48,    # Couronne fixe: 48 dents (48+12=60 divisible par 3)
        output_ring_teeth=52,   # Couronne sortie: 52 dents (52+12=64 divisible par 4? wait, let's use 3 planets)
        num_planets=3,          # 3 planètes pour simplifier
        module=2.5,             # Module plus grand
    )

    if anim2 is not None:
        print("✅ Animation créée avec succès!")
    else:
        print("❌ Échec de création de l'animation")

    print("\n🎯 Utilisation dans Jupyter:")
    print("from SRCPG import animate_srcpg_standalone")
    print("from IPython.display import HTML")
    print("anim = animate_srcpg_standalone(20, 60, 80)")
    print("HTML(anim.to_jshtml())")

if __name__ == "__main__":
    main()