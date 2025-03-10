import numpy as np
import matplotlib.pyplot as plt
import mplcursors

m = 0.4 # [mm] 1st stage module
min_r = 100 # Min target ratio
max_r = 130 # Max target ratio
min_p = 3 # Min planet number | INT VALUE
max_p = 5 # Max planet number | INT VALUE
min_Dr1 = 35 # [mm] Min ring 1 diameter | INT VALUE
max_Dr1 = 65 # [mm] Max ring 1 diameter | INT VALUE


Z_s1_rng = [17, 100] # Sun 1 teeth count range | INT VALUES
n =1 # Scaling factor - Let it at 1
diam_step = 1 # [mm] Diameter steps in designs exploration | INT VALUE
Dp1 = 25.4 / m # [mm] Diametral pitch 1

feasible_designs = []
for Dr1 in range(min_Dr1, max_Dr1, diam_step):
    Zr1 = Dr1 / m # [INT] Ring 1 teeth count
    if int(Zr1) != Zr1: continue # teeth count must be INT
    
    for P in range(min_p, max_p+1):
        for Zs1 in range(Z_s1_rng[0], Z_s1_rng[1]+1):
            Zp1 = (Zr1 - Zs1) / 2 # [INT] Planet 1 teeth count
            Zp2 = n*Zp1 # [INT] Planet 2 teeth count | Use n as a scaling factor
            Zr2 = n*Zr1+ P # [INT] Ring 2 teeth count
            Dr2 = Zr2 * m # [mm] Ring 2 diameter
            Zs2 = Zr2 - 2*Zp2 # [INT] Sun 2 teeth count
            Dp2 = Dp1 * (Zr2 - Zp2) / (Zr1 - Zp1) # [mm] Diametral pitch 2
            R = (1 + Zr1 / Zs1) * n*Zr1 / (Zr2 - n*Zr1)
            try :
                # Teeth count must be integers and positive
                assert(Zp1 == int(Zp1))
                assert(Zp1 > 0)
                assert(Zp2 == int(Zp2))
                assert(Zp2 > 0)
                assert(Zr2 == int(Zr2))
                assert(Zr2 > 0)
                assert(Zs2 == int(Zs2))
                assert(Zs2 > 0)
                # Ring and sun teeth count must be divisible by planet number
                assert(Zs1 % P == 0)
                assert(Zr1 % P == 0)
                assert(Zs2 % P == 0)
                assert(Zr2 % P == 0)
            except:
                continue

            if (min_Dr1 <= Dr1 <= max_Dr1) and (min_Dr1 <= Dr2 <= max_Dr1) and (min_r <= R <= max_r):
                feasible_designs.append({
                        "planets_nb": P,
                        "tc_sun1": Zs1,
                        "tc_planet1": Zp1,
                        "tc_ring1": Zr1,
                        "diam_ring1": Dr1,
                        "diam_pitch1": Dp1,
                        "tc_sun2": Zs2,
                        "tc_planet2": Zp2,
                        "tc_ring2": Zr2,
                        "diam_ring2": Dr2,
                        "diam_pitch2": Dp2,
                        "ratio": R
                    })
                
print(f">>> Design exploration ended, resulting in {len(feasible_designs)} designs !")

if len(feasible_designs) > 0:

    # Get feasible designs data
    ratios = [design["ratio"] for design in feasible_designs]
    max_diameters = [max(design["diam_ring1"], design["diam_ring2"]) for design in feasible_designs]
    planet_numbers = [design["planets_nb"] for design in feasible_designs]

    # Plot setup
    unique_planet_numbers = sorted(set(planet_numbers)) # Get unique planet numbers to build legend
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_planet_numbers)))
    color_map = {p: colors[i] for i, p in enumerate(unique_planet_numbers)}
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlabel('Ratio de réduction', fontsize=12)
    ax.set_ylabel('Diamètre maximal (mm)', fontsize=12)
    ax.set_title('Designs faisables: Ratio vs Diamètre maximal', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)

    # Create one scatter plot by design and show it on the same figure
    scatter_plots = {}
    for p in unique_planet_numbers:
        indices = [i for i, pn in enumerate(planet_numbers) if pn == p]
        
        p_ratios = [ratios[i] for i in indices]
        p_max_diameters = [max_diameters[i] for i in indices]
        
        scatter = ax.scatter(p_ratios, p_max_diameters, 
                            color=color_map[p], 
                            label=f'{p} planètes',
                            alpha=0.7, 
                            s=50)
        
        scatter_plots[p] = scatter

    # Add legend
    ax.legend(title="Nombre de planètes", fontsize=10)

    # Add popups to display each designs parameters when hovered
    def format_annotation(sel):
        index = sel.index
        design = feasible_designs[index]
        text = (
            f"Planètes: {design['planets_nb']}\n"
            f"Ratio: {design['ratio']:.2f}\n"
            f"Sun1: {design['tc_sun1']}, Planet1: {design['tc_planet1']}, Ring1: {design['tc_ring1']}\n"
            f"Sun2: {design['tc_sun2']}, Planet2: {design['tc_planet2']}, Ring2: {design['tc_ring2']}\n"
            f"Diam Ring1: {design['diam_ring1']:.1f} mm, Diam Ring2: {design['diam_ring2']:.1f} mm\n"
            f"Diametral Pitch 1: {design["diam_pitch1"]} mm, Diametral Pitch 2: {design["diam_pitch2"]} mm"
        )
        sel.annotation.set_text(text)

    # Add interactivity to cursors
    cursor = mplcursors.cursor(hover=True)
    cursor.connect("add", format_annotation)


    plt.tight_layout()
    plt.show()