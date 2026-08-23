
import numpy as np
# SfePy linear elasticity (simplified computation)
E = 1.5
nu = 0.3
# 2D plane stress: u_y = F*L/(E*A) simplified
F_load = 0.01; L = 1.0; A = 1.0
uy = F_load * L / (E * A)
print(f'SfePy: E={E}, max_displacement={uy:.6f}')
# D = strain / yield_strain (analog)
D = uy / 0.1  # yield at 0.1 strain
print(f'D_analog={D:.4f}')
