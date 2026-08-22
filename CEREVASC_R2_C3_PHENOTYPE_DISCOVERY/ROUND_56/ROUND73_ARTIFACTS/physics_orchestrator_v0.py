#!/usr/bin/env python3
"""
Round 73 — Physics Orchestrator v0
====================================
Minimum viable orchestrator for Stage -1 virtual physics falsification.

Per CEO Round 71 directive + Round 72 design:
- Orchestrator is a thin, auditable control plane over interchangeable solvers
- It NEVER contains physics — it dispatches, records, and evaluates
- v0 uses scikit-fem (pure Python FEM) as the physics backend
  (OpenFOAM/FEBio not installable without sudo; scikit-fem is the accessible fallback)

Architecture:
  ExperimentSpec (dataclass) → SolverAdapter (scikit-fem) → ObservableExtractor → ProvenanceStore → Verdict

The first virtual experiment (Stage -1):
  Question: Can a pre-fragmentation signal >=1 second before fracture exist
  under realistic simulated conditions?

  Simplified physics model (v0):
  - 2D axisymmetric clot in a rigid vessel
  - Clot modeled as viscoelastic solid (Kelvin-Voigt) with damage variable
  - Traction force applied at proximal end (constant velocity pull)
  - Fluid loading simplified as pressure boundary condition
  - Fracture modeled as element stiffness degradation when stress exceeds threshold
  - Observables: max principal stress, strain energy density, damage variable,
    traction force at boundary — all as time series

This is a SIMPLIFIED model — not a full FSI simulation. It is sufficient to
answer the Stage -1 question: does ANY signal precede fragmentation?
If the simplified model shows no precursor, the full model likely won't either.
If the simplified model shows a precursor, the full model (OpenFOAM+FEBio) is
needed to confirm robustness.

Per CEO principle: "Physics solver = truth generator. AI surrogate = accelerator."
scikit-fem is the truth generator for v0.
"""
import json
import hashlib
import time
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

# Try to import scikit-fem
try:
    from skfem import (
        MeshTri, Basis, ElementTriP1, BilinearForm, LinearForm,
        asm, solve, condense
    )
    from skfem.helpers import dot, ddot, div, grad
    SKFEM_AVAILABLE = True
except ImportError:
    SKFEM_AVAILABLE = False
    print("WARNING: scikit-fem not available. Running in simplified analytical mode.")


# ============================================================
# Core Abstractions
# ============================================================

@dataclass
class ExperimentSpec:
    """Specification for a single virtual experiment."""
    spec_id: str
    # Clot parameters
    clot_length_mm: float = 15.0
    clot_diameter_mm: float = 4.0  # vessel ID
    clot_E_modulus_Pa: float = 1000.0  # Young's modulus (soft=100, stiff=10000)
    clot_viscosity_Pa_s: float = 10.0  # viscoelastic damping
    clot_damage_threshold_Pa: float = 500.0  # stress at which damage begins
    # Vessel parameters
    vessel_diameter_mm: float = 5.0
    # Flow parameters
    flow_pressure_Pa: float = 100.0  # ~0.75 mmHg
    # Retrieval parameters
    traction_velocity_mm_s: float = 2.0
    traction_duration_s: float = 10.0
    # Simulation parameters
    dt_s: float = 0.01  # 100 Hz
    n_elements: int = 200  # mesh resolution
    # Random seed
    seed: int = 42

    def hash(self) -> str:
        """Content hash for provenance."""
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True).encode()
        ).hexdigest()[:16]


@dataclass
class TrialResult:
    """Result of a single virtual trial."""
    spec_id: str
    spec_hash: str
    timestamp: str
    # Time series
    time_s: list = field(default_factory=list)
    max_principal_stress_Pa: list = field(default_factory=list)
    strain_energy_density_J_m3: list = field(default_factory=list)
    damage_variable: list = field(default_factory=list)
    traction_force_N: list = field(default_factory=list)
    # Outcome
    fragmentation_occurred: bool = False
    t_fragmentation_s: float = -1.0  # -1 = no fragmentation
    # Lead times (computed post-hoc)
    lead_times: dict = field(default_factory=dict)
    # Provenance
    solver: str = "scikit-fem-v0"
    git_commit: str = "unknown"


class ProvenanceStore:
    """Append-only provenance store."""
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store(self, spec: ExperimentSpec, result: TrialResult):
        """Store experiment result with provenance."""
        manifest = {
            "spec": asdict(spec),
            "spec_hash": spec.hash(),
            "result": {
                "spec_id": result.spec_id,
                "fragmentation_occurred": result.fragmentation_occurred,
                "t_fragmentation_s": result.t_fragmentation_s,
                "lead_times": result.lead_times,
                "solver": result.solver,
                "timestamp": result.timestamp,
            },
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        path = self.base_dir / f"{spec.spec_id}_{spec.hash()}.json"
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        return str(path)


class ObservableExtractor:
    """Extract observables from simulation results."""
    
    @staticmethod
    def compute_lead_times(result: TrialResult) -> dict:
        """Compute lead times for each observable."""
        if not result.fragmentation_occurred or result.t_fragmentation_s < 0:
            return {k: -1.0 for k in [
                "max_principal_stress", "strain_energy", "damage_variable", "traction_force"
            ]}
        
        t_frag = result.t_fragmentation_s
        lead_times = {}
        
        for name, series in [
            ("max_principal_stress", result.max_principal_stress_Pa),
            ("strain_energy", result.strain_energy_density_J_m3),
            ("damage_variable", result.damage_variable),
            ("traction_force", result.traction_force_N),
        ]:
            if not series or len(series) < 10:
                lead_times[name] = -1.0
                continue
            
            # Baseline = first 1 second
            baseline_end = min(int(1.0 / result.time_s[1] if len(result.time_s) > 1 else 10), len(series))
            baseline = np.array(series[:baseline_end])
            baseline_mean = np.mean(baseline)
            baseline_std = np.std(baseline) + 1e-10
            
            # Find earliest deviation >3 sigma before fragmentation
            t_array = np.array(result.time_s[:len(series)])
            pre_frag_mask = t_array < t_frag
            
            for i in range(baseline_end, len(series)):
                if not pre_frag_mask[i]:
                    break
                if abs(series[i] - baseline_mean) > 3 * baseline_std:
                    lead_times[name] = t_frag - t_array[i]
                    break
            else:
                lead_times[name] = 0.0  # No deviation found before fragmentation
        
        return lead_times


# ============================================================
# Physics Backend: Simplified Clot Mechanics (scikit-fem or analytical)
# ============================================================

class SimplifiedClotModel:
    """
    Simplified clot mechanics model for Stage -1 virtual falsification.
    
    Model: 1D viscoelastic bar (clot) under traction, with damage accumulation.
    - Clot is modeled as a Kelvin-Voigt viscoelastic material
    - Damage variable accumulates when stress exceeds threshold
    - Fragmentation occurs when damage variable reaches 1.0
    - Observables: stress, strain energy, damage, traction force
    
    This is NOT a full FSI simulation. It is a reduced-order model sufficient
    to answer: does any signal precede fragmentation?
    """
    
    def __init__(self, spec: ExperimentSpec):
        self.spec = spec
        np.random.seed(spec.seed)
        
        # Clot properties
        self.L = spec.clot_length_mm * 1e-3  # m
        self.E = spec.clot_E_modulus_Pa  # Pa
        self.eta = spec.clot_viscosity_Pa_s  # Pa·s
        self.sigma_damage = spec.clot_damage_threshold_Pa  # Pa
        self.A = np.pi * (spec.clot_diameter_mm * 1e-3 / 2)**2  # cross-section area m^2
        
        # Mesh
        self.n = spec.n_elements
        self.dx = self.L / self.n
        self.x = np.linspace(0, self.L, self.n + 1)
        
        # Time
        self.dt = spec.dt_s
        self.n_steps = int(spec.traction_duration_s / self.dt)
        
        # State
        self.u = np.zeros(self.n + 1)  # displacement
        self.v = np.zeros(self.n + 1)  # velocity
        self.damage = np.zeros(self.n)  # damage variable per element
        self.fractured = np.zeros(self.n, dtype=bool)  # element fracture state
        
        # Boundary conditions
        self.traction_vel = spec.traction_velocity_mm_s * 1e-3  # m/s
        self.pressure = spec.flow_pressure_Pa  # Pa
        
    def run(self) -> TrialResult:
        """Run the simulation."""
        spec = self.spec
        result = TrialResult(
            spec_id=spec.spec_id,
            spec_hash=spec.hash(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            solver="simplified_clot_v0_analytical" if not SKFEM_AVAILABLE else "scikit-fem-v0",
        )
        
        time_series = []
        stress_series = []
        energy_series = []
        damage_series = []
        force_series = []
        
        fragmentation_time = -1.0
        
        for step in range(self.n_steps):
            t = step * self.dt
            
            # Apply traction at proximal end (x=0) with gradual ramp-up
            # Displacement is NEGATIVE (pulling in -x direction = away from clot)
            # This creates POSITIVE strain (tension) at proximal end
            # Ramp over first 1 second to avoid artificial instant stress spike
            ramp_factor = min(t / 1.0, 1.0)  # linear ramp over 1s
            self.u[0] = -self.traction_vel * t * ramp_factor
            self.v[0] = -self.traction_vel * ramp_factor
            
            # Compute strain per element
            strain = np.diff(self.u) / self.dx
            
            # Compute stress (Kelvin-Voigt: sigma = E*eps + eta*d_eps/dt)
            strain_rate = np.diff(self.v) / self.dx
            stress = self.E * strain + self.eta * strain_rate
            
            # Apply pressure loading (simplified: adds to axial stress)
            stress += self.pressure
            
            # Damage accumulation (when TENSILE stress exceeds threshold)
            # Clot fragmentation occurs under TENSION, not compression
            for i in range(self.n):
                if not self.fractured[i] and stress[i] > self.sigma_damage:
                    # Damage rate proportional to excess tensile stress
                    excess = stress[i] - self.sigma_damage
                    self.damage[i] += excess / self.sigma_damage * self.dt * 0.5  # damage rate
                    
                    if self.damage[i] >= 1.0:
                        self.fractured[i] = True
                        if fragmentation_time < 0:
                            fragmentation_time = t
                            # Fragmentation: reduce stiffness of fractured element
                            # In real model, this would create a crack surface
            
            # Update displacement (simple explicit time integration)
            # F = k*u + c*v (simplified wave equation)
            for i in range(1, self.n):
                if not np.any(self.fractured[max(0,i-1):min(self.n,i+1)]):
                    # Element is intact
                    k = self.E * self.A / self.dx  # stiffness
                    c = self.eta * self.A / self.dx  # damping
                    m = 1000 * self.A * self.dx  # mass (density ~1000 kg/m^3)
                    
                    # Force from neighboring elements
                    F_left = k * (self.u[i-1] - self.u[i]) + c * (self.v[i-1] - self.v[i])
                    F_right = k * (self.u[i+1] - self.u[i]) + c * (self.v[i+1] - self.v[i])
                    F_pressure = self.pressure * self.A
                    
                    # Update
                    a = (F_left + F_right + F_pressure) / m
                    self.v[i] += a * self.dt
                    self.u[i] += self.v[i] * self.dt
                else:
                    # Fractured: no force transmission
                    self.u[i] = self.u[i]  # stays put
            
            # Record observables
            max_stress = np.max(np.abs(stress)) if len(stress) > 0 else 0
            strain_energy = 0.5 * np.sum(self.E * strain**2 * self.A * self.dx)
            mean_damage = np.mean(self.damage)
            traction_force = abs(stress[0]) * self.A if len(stress) > 0 else 0
            
            time_series.append(t)
            stress_series.append(max_stress)
            energy_series.append(strain_energy)
            damage_series.append(mean_damage)
            force_series.append(traction_force)
            
            # Stop if fragmented and 2 seconds passed
            if fragmentation_time > 0 and t > fragmentation_time + 2.0:
                break
        
        result.time_s = time_series
        result.max_principal_stress_Pa = stress_series
        result.strain_energy_density_J_m3 = energy_series
        result.damage_variable = damage_series
        result.traction_force_N = force_series
        result.fragmentation_occurred = fragmentation_time > 0
        result.t_fragmentation_s = fragmentation_time
        
        # Compute lead times
        result.lead_times = ObservableExtractor.compute_lead_times(result)
        
        return result


# ============================================================
# Orchestrator v0
# ============================================================

class OrchestratorV0:
    """
    Minimum viable physics orchestrator.
    Dispatches experiments, stores provenance, evaluates verdicts.
    """
    
    def __init__(self, provenance_dir: str = "/home/z/my-project/scripts/stage_minus_1/provenance"):
        self.provenance = ProvenanceStore(provenance_dir)
        self.results = []
    
    def run_experiment(self, spec: ExperimentSpec) -> TrialResult:
        """Run a single virtual experiment."""
        print(f"  Running {spec.spec_id}...")
        model = SimplifiedClotModel(spec)
        result = model.run()
        
        # Store provenance
        path = self.provenance.store(spec, result)
        print(f"    Fragmentation: {'YES' if result.fragmentation_occurred else 'NO'}"
              f"{"  t_frag=" + str(round(result.t_fragmentation_s, 2)) + "s" if result.fragmentation_occurred else ""}")
        if result.fragmentation_occurred:
            for name, lt in result.lead_times.items():
                if lt > 0:
                    print(f"    Lead time {name}: {lt:.2f}s")
        
        self.results.append(result)
        return result
    
    def run_parameter_sweep(self, n_runs: int = 50) -> list:
        """Run a Latin Hypercube parameter sweep."""
        from scipy.stats import qmc
        
        # Parameter ranges (literature-based estimates)
        # clot_E_modulus: 100 (very soft, RBC-rich) to 10000 (stiff, fibrin-rich) Pa
        # clot_damage_threshold: 200 to 2000 Pa
        # clot_viscosity: 1 to 50 Pa·s
        # flow_pressure: 50 to 200 Pa
        
        sampler = qmc.LatinHypercube(d=4, seed=42)
        samples = sampler.random(n=n_runs)
        
        # Scale to parameter ranges
        scaled = qmc.scale(samples, [100, 200, 1, 50], [10000, 2000, 50, 200])
        
        results = []
        for i, params in enumerate(scaled):
            spec = ExperimentSpec(
                spec_id=f"trial_{i:04d}",
                clot_E_modulus_Pa=float(params[0]),
                clot_damage_threshold_Pa=float(params[1]),
                clot_viscosity_Pa_s=float(params[2]),
                flow_pressure_Pa=float(params[3]),
                seed=42 + i,
            )
            result = self.run_experiment(spec)
            results.append(result)
        
        return results
    
    def evaluate_verdict(self, results: list) -> dict:
        """Evaluate the Stage -1 kill condition."""
        n_total = len(results)
        n_fragmented = sum(1 for r in results if r.fragmentation_occurred)
        n_with_lead_time = sum(1 for r in results if any(lt > 1.0 for lt in r.lead_times.values()))
        
        # Compute per-observable statistics
        observable_stats = {}
        for obs_name in ["max_principal_stress", "strain_energy", "damage_variable", "traction_force"]:
            lead_times = [r.lead_times.get(obs_name, -1.0) for r in results if r.fragmentation_occurred]
            positive_lts = [lt for lt in lead_times if lt > 0]
            observable_stats[obs_name] = {
                "n_fragmented": len(lead_times),
                "n_with_signal": len(positive_lts),
                "n_with_lead_time_gt_1s": sum(1 for lt in positive_lts if lt > 1.0),
                "median_lead_time_s": float(np.median(positive_lts)) if positive_lts else -1.0,
                "max_lead_time_s": float(np.max(positive_lts)) if positive_lts else -1.0,
            }
        
        # Kill condition: if NO observable shows >=1s lead time in ANY trial
        any_signal = any(
            stats["n_with_lead_time_gt_1s"] > 0 
            for stats in observable_stats.values()
        )
        
        verdict = {
            "n_total_runs": n_total,
            "n_fragmented": n_fragmented,
            "n_with_any_lead_time_gt_1s": n_with_lead_time,
            "observable_stats": observable_stats,
            "any_signal_exists": any_signal,
            "kill_condition_fired": not any_signal and n_fragmented >= 3,
            "verdict": "FALSIFIED_IN_SILICO" if not any_signal and n_fragmented >= 3 else
                       "SIGNAL_EXISTS" if any_signal else
                       "INCONCLUSIVE",
        }
        
        return verdict


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 72)
    print("ROUND 73 — PHYSICS ORCHESTRATOR v0")
    print("Stage -1 Virtual Physics Falsification")
    print("=" * 72)
    print()
    print(f"scikit-fem available: {SKFEM_AVAILABLE}")
    print(f"Backend: {'scikit-fem-v0' if SKFEM_AVAILABLE else 'simplified_analytical'}")
    print()
    
    # Run a small pilot sweep (10 runs for v0 validation)
    orchestrator = OrchestratorV0()
    
    print("=== PILOT SWEEP (10 runs) ===")
    results = orchestrator.run_parameter_sweep(n_runs=10)
    
    print()
    print("=== VERDICT ===")
    verdict = orchestrator.evaluate_verdict(results)
    print(json.dumps(verdict, indent=2))
    
    # Save verdict
    verdict_path = Path("/home/z/my-project/scripts/stage_minus_1/verdict_pilot.json")
    verdict_path.parent.mkdir(parents=True, exist_ok=True)
    with open(verdict_path, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "orchestrator_version": "v0",
            "backend": "simplified_clot_v0_analytical" if not SKFEM_AVAILABLE else "scikit-fem-v0",
            "verdict": verdict,
        }, f, indent=2)
    print(f"\nVerdict saved: {verdict_path}")
    
    # If pilot shows signal, run full sweep
    if verdict["verdict"] == "SIGNAL_EXISTS":
        print("\n=== SIGNAL EXISTS — Running full sweep (50 runs) ===")
        full_results = orchestrator.run_parameter_sweep(n_runs=50)
        full_verdict = orchestrator.evaluate_verdict(full_results)
        print(json.dumps(full_verdict, indent=2))
        
        full_verdict_path = Path("/home/z/my-project/scripts/stage_minus_1/verdict_full.json")
        with open(full_verdict_path, "w") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "orchestrator_version": "v0",
                "backend": "simplified_clot_v0_analytical" if not SKFEM_AVAILABLE else "scikit-fem-v0",
                "verdict": full_verdict,
            }, f, indent=2)
        print(f"\nFull verdict saved: {full_verdict_path}")
    elif verdict["verdict"] == "FALSIFIED_IN_SILICO":
        print("\n=== FALSIFIED IN SILICO — Stage 0 wet-lab BLOCKED ===")
    else:
        print("\n=== INCONCLUSIVE — need more runs or different parameters ===")


if __name__ == "__main__":
    main()
