You are building the SIMULATION ENGINE REGISTRY and PHYSICS ORCHESTRATOR DESIGN for the CTO. This is Round 72 — a strategic pivot from "stop coding" to "build the simulation substrate that allows AI to test physical hypotheses before paying for wet-lab experiments."

CEO ROUND 71 AUDIT — STRATEGIC PIVOT:
"The coder has declared the computational loop finished and handed the problem to a wet lab. That contradicts the requirement that this be an end-to-end AI discovery loop. The correct architecture is NOT: AI -> reasoning -> wet lab -> stop. It should be: AI hypothesis -> prior art -> multiphysics simulation -> adversarial virtual experiments -> AI prediction -> cheapest physical validation -> data assimilation -> calibrated simulation -> virtual optimization -> evidence package -> invention decision."

CEO DIRECTIVE: "Do not spend $5-10k on the wet lab yet. First build a zero/low-cost virtual physics gate."

KEY REFERENCE — InSteps (closest existing end-to-end thrombectomy simulation):
- InSteps B.V. (insteps.com) — "world's first high-fidelity In-Silico Thrombectomy Digital Twin Platform"
- 4 core modules: (1) AI-generated synthetic vessel + thrombus anatomy, (2) FEM thrombectomy simulation, (3) Generative AI neural network emulator (geometric deep learning), (4) clinical/virtual-trial outcome model
- Based on 4,500 real-world patients
- EUR 450K funding secured (July 2026)
- Originated from INSIST H2020 EU project (cordis.europa.eu/project/id/777072)
- INSIST platform simulates: stent deployment, clot interaction, retrieval, fragmentation, embolization, recanalization prediction

KEY SCIENTIFIC REFERENCES:
1. 2021 FEA-SPH thrombectomy model (PMC8672072): "Realistic computer modelling of stent retriever thrombectomy: a hybrid FEA-SPH approach." Demonstrated coupling FEA + SPH to model stent retriever thrombectomy including fragmentation. Published Dec 2021.
2. 2026 CFD-Peridynamics paper (Karmakar et al., ScienceDirect S0045782526003221): "Fluid-Thrombus Interactions Through a Coupled CFD-Peridynamics Framework." Models cohesive/adhesive thrombus fracture under fluid-induced forces. Published 2026.

CEO SIMULATION STACK:
| Layer | Engine | Role |
|-------|--------|------|
| Virtual population / clinical | InSteps | Best existing end-to-end thrombectomy platform |
| Patient-specific vascular | SimVascular | Imaging -> geometry -> vascular simulation |
| Hemodynamics / CFD | OpenFOAM | Open-source CFD, multiphase, dynamic mesh |
| Device/clot mechanics | LS-DYNA | Nonlinear transient mechanics + FSI |
| Biomechanics alternative | FEBio | Open-source nonlinear biomechanics + FSI |
| General multiphysics | COMSOL | FSI / blood / device multiphysics |
| High-end structural | Abaqus/Explicit | Nonlinear transient device/clot mechanics |
| Fragmentation | CFD + Peridynamics | Cutting-edge fracture/adhesion simulation |
| Established thrombectomy | FEA + SPH | Already demonstrated for retrieval + fragmentation |
| AI surrogate | NVIDIA Modulus | Physics-informed surrogate / acceleration |

CEO DESIGN PRINCIPLE: "Do not build another simulator. Your advantage should be the ORCHESTRATOR, not a new CFD solver. Use existing engines as interchangeable physics backends."

SECTION 1: SIMULATION ENGINE REGISTRY
For EACH of the 10 engines, produce: engine name, physics coverage, fracture capability, FSI capability, patient-specific geometry, GPU acceleration, automation API, license, parallelization, validation evidence, AI coupling, accessibility (can we install in Ubuntu?), relevance to our fragmentation hypothesis (HIGH/MEDIUM/LOW).

SECTION 2: ACCESSIBILITY ASSESSMENT
For each engine: can we install in this Linux environment? open-source or commercial? cost? minimum viable installation for Stage -1?

SECTION 3: PHYSICS ORCHESTRATOR ARCHITECTURE
Design the orchestrator: AI says "Test this mechanism under 10,000 virtual conditions." Orchestrator: chooses solver, runs experiment, extracts observables, stores provenance, returns falsification evidence. What is minimum viable orchestrator? How does it interface with engines? How does it store provenance?

SECTION 4: STAGE -1 VIRTUAL PHYSICS FALSIFICATION DESIGN
First virtual experiment: Can a pre-fragmentation signal >=1s before fracture exist under realistic simulated conditions? What engines? What parameters to vary? What observables? How many virtual experiments? Kill condition? Relationship to Stage-0 wet-lab protocol (which remains frozen)?

SECTION 5: RELATIONSHIP TO INSTEPS
Partner/license/integrate with InSteps? Or build minimal open-source alternative? Trade-off? Minimum viable stack?

SECTION 6: THE TRUE END-TO-END LOOP
Map CEO 15-step loop to concrete next actions. Steps 1-3 done. Steps 4-8 are the simulation phase — what are concrete next actions?

CONSTRAINTS:
- Be honest about what is feasible in this environment (Linux, Python, no commercial licenses).
- Do NOT propose building a new CFD solver. The orchestrator is the advantage.
- Prioritize open-source: SimVascular, OpenFOAM, FEBio.
- Per CEO: "Physics solver = truth generator. AI surrogate = accelerator. Never reverse those."
- Mark UNKNOWN where you cannot verify.

Target ~2500-3500 words.
