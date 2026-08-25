# svFSI Installation — Hard Blocker Documentation

**Date:** 2026-08-25 (R314)
**Authority:** CEO R314 §P0; Article XXIII; Article XXV

## What was attempted (R312 + R314)

### Pathway 1: Precompiled .deb (R312)
- Downloaded SimVascular-2023-05-Ubuntu-20.deb (538MB)
- Cannot install: no root access
- Partial extraction via `dpkg-deb -x` failed (gzip truncation)
- svFSI binary not found in extracted portion

### Pathway 2: Docker (R312 + R314)
- Docker not installed in environment
- Attempted manual Docker layer extraction via registry API
- Successfully pulled 12 of 18 layers from `simvascular/solver:latest`
- **svFSI/svMultiPhysics binary is in layers 16-17 (483.8MB + 531.3MB)**
- These layers are too large to download and extract within session resource limits
- Conda environment structure confirmed but binary not reachable

### Pathway 3: Source build (R312)
- No cmake, no mpicc, no PETSc dev packages
- Full toolchain installation not feasible in session

### Pathway 4: pip install (R314)
- `svfsi`, `svMultiPhysics`, `simvascular` — none available on PyPI

## The exact missing dependency

**svFSI/svMultiPhysics binary** (compiled executable, ~100-500MB)

The binary exists in:
- `simvascular/solver:latest` Docker image (amd64), layers 16-17
- SimVascular 2023-05 .deb package (requires root to install)
- Source build (requires cmake + MPI + PETSc + Trilinos + HYPRE)

## What the CEO can do to unblock

### Option A: Install Docker
```bash
apt install docker.io
docker pull simvascular/solver:latest
docker run simvascular/solver:latest svFSI --help
```

### Option B: Provide root access
```bash
sudo dpkg -i SimVascular-2023-05-Ubuntu-20.deb
# svFSI binary at /usr/local/sv/simvascular/2023-05-31/bin/
```

### Option C: Install build toolchain
```bash
apt install cmake mpicc libpetsc-dev libtrilinos-dev libhypre-dev
git clone https://github.com/SimVascular/svFSI
cd svFSI && mkdir build && cd build
cmake .. && make
```

### Option D: Run svFSI externally
CEO runs the official pipe3D_RCR test case on their own machine and provides:
- Input file: `svFSI.inp` (already downloaded from svFSI-Tests repo)
- Mesh files: `mesh-complete/` (from svFSI-Tests repo)
- Output: `result-*.vtu` files + outlet pressure measurements

## What I will do in R314 without svFSI

Per CEO R314 §P0: "Use a simplified physical analogue if necessary."

I will:
1. Use the **official svFSI pipe3D_RCR test case parameters** (density 1.06, viscosity 0.04, RCR BC)
2. Build a **1D equivalent** of the 3D pipe flow with the SAME physics parameters
3. Compare my 1D model's pressure drop to the **published pipe3D_RCR expected output** (from svFSI-Tests README)
4. If my 1D model with svFSI parameters agrees with the published 3D result, the physics is validated
5. If not, the disagreement is real and documented

This is NOT actual svFSI execution. It is a **parameter-matched published-reference cross-check**.
Label: `PUBLISHED_REFERENCE_CROSS_CHECK — svFSI EXECUTION BLOCKED (environment constraint)`

## Honest label for P-01

Per Article XXVIII (no silent semantic promotion) and Article XXVI (no self-certification):

P-01 verification state:
- `INDEPENDENTLY_REIMPLEMENTED` (scipy ode vs solve_ivp, same author)
- `PUBLISHED_REFERENCE_CROSS_CHECK` (FDA nozzle benchmark, 80% disagreement in R312, improved to 72% in R313)
- `svFSI_EXECUTION_BLOCKED` (hard environment constraint, documented above)

**NOT `MODEL_VERIFIED`. NOT `TECHNOLOGY_TRANSFER_READY`.**

The CEO's R314 §P0 directive is acknowledged. The hard blocker is documented with exact missing dependency. R314 proceeds with the parameter-matched cross-check as the best available alternative.
