#!/usr/bin/env python3
"""R80 sanity: compute the gri30 equilibrium legs BEFORE baking test
expectations (accuracy rule: all physics verified in code, never assumed)."""
import cantera as ct


def xf(T, P, X, species, mech="gri30.yaml"):
    gas = ct.Solution(mech)
    gas.TPX = T, P, X
    gas.equilibrate("TP")
    return gas.X[gas.species_index(species)]


ATM = 101325.0

print("L1 oxidant-excess (CO2/CO ratio vs excess O2 — dilution-free):")
stoich = xf(1200, ATM, {"CO": 0.02, "O2": 0.012, "N2": 1.0}, "CO2") / \
    max(xf(1200, ATM, {"CO": 0.02, "O2": 0.012, "N2": 1.0}, "CO"), 1e-30)
excess = xf(1200, ATM, {"CO": 0.02, "O2": 0.10, "N2": 1.0}, "CO2") / \
    max(xf(1200, ATM, {"CO": 0.02, "O2": 0.10, "N2": 1.0}, "CO"), 1e-30)
print(f"  stoich O2: CO2/CO={stoich:.3f} | excess O2: CO2/CO={excess:.3f} | "
      f"dir={'up' if excess > stoich else 'down'}")

print("L2 T-up endothermic forward (SMR, rich mix, wide T):")
low = xf(900, ATM, {"CH4": 0.10, "H2O": 0.10, "N2": 1.0}, "CO")
high = xf(1600, ATM, {"CH4": 0.10, "H2O": 0.10, "N2": 1.0}, "CO")
print(f"  900K: CO={low:.6e} | 1600K: CO={high:.6e} | "
      f"rel change={(high - low) / low * 100:.1f}% | "
      f"dir={'up' if high > low else 'down'}")

print("L3 T-up exothermic dissociation (CO2 decomposes at high T):")
l3a = xf(1500, ATM, {"CO": 0.01, "O2": 0.006, "N2": 1.0}, "CO")
l3b = xf(2300, ATM, {"CO": 0.01, "O2": 0.006, "N2": 1.0}, "CO")
print(f"  1500K: CO={l3a:.6e} | 2300K: CO={l3b:.6e} | "
      f"dir={'up' if l3b > l3a else 'down'}")

print("L3b same mix CO2:")
l3a2 = xf(1500, ATM, {"CO": 0.01, "O2": 0.006, "N2": 1.0}, "CO2")
l3b2 = xf(2300, ATM, {"CO": 0.01, "O2": 0.006, "N2": 1.0}, "CO2")
print(f"  1500K: CO2={l3a2:.6e} | 2300K: CO2={l3b2:.6e} | "
      f"dir={'up' if l3b2 > l3a2 else 'down'}")

print("L4 flat check (H2 at fixed T, N2 dilution irrelevant to H2?):")
a = xf(1200, ATM, {"H2": 0.01, "O2": 0.005, "N2": 1.0}, "H2O")
b = xf(1200, ATM, {"H2": 0.01, "O2": 0.005, "N2": 1.0}, "H2O")
print(f"  identical inputs -> identical? {a:.8e} vs {b:.8e} "
      f"(determinism: {a == b})")
