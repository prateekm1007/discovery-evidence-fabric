# Installation Guide — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C10

---

## 1. Reference implementation installation

### 1.1 Prerequisites
- Python 3.8+ (tested on 3.10, 3.11, 3.12)
- numpy (any recent version)
- scipy (for Bayesian updates; any recent version)
- No GPU required
- No external dependencies beyond numpy/scipy

### 1.2 Steps
```bash
# 1. Clone the repository (or extract the TTP package)
git clone <repo-url>
cd discovery-evidence-fabric/TTP_PACKAGES/P-01_PROTOTYPE

# 2. Verify the simulator runs
python3 05_simulator.py --self-test

# 3. Run the 25-scenario baseline (5 scenarios x 5 seeds)
python3 05_simulator.py --scenarios all --seeds 5

# 4. Verify outputs match the preserved raw results
diff <(python3 05_simulator.py --scenarios all --seeds 5 --json) \
     p01_simulator_results_ALLSCENARIOS.json
# Expected: no differences (within floating-point tolerance)
```

### 1.3 Expected runtime
- 25 scenarios: < 60 seconds on standard laptop
- 225 ablations: ~10 minutes

## 2. V0 bench prototype installation

### 2.1 Hardware BOM
See `technology/prototype_blueprint.md` §1.2 for full bill of materials.

### 2.2 Assembly
1. Acrylic manifold machining (custom shop, 2-3 weeks)
2. COTS component procurement (1-2 weeks)
3. Tubing and fitting assembly (1 day)
4. Electronics integration (1 week)
5. Software deployment to Raspberry Pi / Arduino (1 day)

### 2.3 Calibration
1. Per-segment flow sensor calibration (using precision peristaltic pump)
2. Pressure sensor calibration (using water column reference)
3. Valve position calibration (using flow-vs-PWM characterization)

### 2.4 Test execution
See `transfer/reproduction.md` for the 30-run test program (6 scenarios × 5 seeds × 24h).

## 3. V1 implantable installation (future)

Not yet specified. Requires resolution of the implantable flow sensor blocking unknown (see `technology/engineering_spec.md` §1.2).
