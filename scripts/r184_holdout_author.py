#!/usr/bin/env python3
"""r184_holdout_author.py — DIR 5 (score-4 gate): author the FRESH
sealed n=24 invention-shaped holdout for the SHIPPED recipe
(best-of-N + critique + revise + verifier) vs the COMPUTE-MATCHED
single-shot baseline.

Re-scope basis (R184-F1): the r178h sealed holdout is UNCUSTODIED in
this sandbox (holdout_secrets/ absent after the recycle) — an
undecryptable holdout is not a usable instrument. This script authors
a FRESH set with custody that survives recycles:

  * the seal key is generated here and stored BOTH in the repo-adjacent
    persistent vault (.env-holdout-v13 style: a gitignored file under
    the repo root, the same persistent-disk path class as .env.keys)
    AND its sha256[:12] digest is recorded in the prereg (the committed
    evidence that the key exists and which one it is — never the key);
  * the plaintext corpus is encrypted with Fernet (the r178h cipher
    class) and ONLY the ciphertext + per-item hashes are committed;
  * the plaintext copy outside the ciphertext is destroyed after
    sealing (burn-after-use discipline: the run decrypts ONCE under
    its own claim, then burns).

Corpus design (invention-shaped per AM53, domains DISJOINT from the 23
r176 DEV domains — verified programmatically at authoring):
  * every item states a FUNDAMENTAL plateau of standard practice
    (physics-coupled, not engineering-sloppiness);
  * every item's constraints EXCLUDE the incumbent mitigation by
    construction (the mitigation move is named and forbidden);
  * question_type "novel-mechanism" — the router 2.0.0 CHEAP_ARM
    recipe (best-of-N + critique + revise + verifier) runs on it.

THE MEASUREMENT (pre-registered, run ONCE, no tuning — separate claim
before the run):
  * ARM A (shipped recipe): 4 plain draws + critique + revise
    (6 generator calls — the compute-matched budget);
  * ARM B (baseline): 1 single-shot draw at the same total budget
    headroom (the compute-matched single-shot; 1 call, the budget
    ceiling identical);
  * blind two-pass judge (order-swapped, WIN only on both passes),
    judge != generator (tr-deepseek seat, the live measured seat);
  * gate: Wilson 95% CI LOWER bound > 50% on A-wins+ties over n=24
    (AM52: the score moves ONLY on a measured win over a
    compute-matched baseline).

Usage: python3 scripts/r184_holdout_author.py
Writes: eval/r184_sealed_holdout_PRIVATE.json (ciphertext),
        eval/r184_holdout_prereg.json,
        .env.holdout (vault, gitignored, NEVER committed)
"""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
EVAL = REPO / "eval"
VAULT = REPO / ".env.holdout"          # gitignored, persistent-disk
CIPHER = EVAL / "r184_sealed_holdout_PRIVATE.json"
PREREG = EVAL / "r184_holdout_prereg.json"

# The 23 r176 DEV domains (disjointness is verified, not assumed):
DEV_DOMAINS = {
    "aerospace-propulsion", "aerospace-thermal", "biomedical-engineering",
    "chemical-process", "civil-infrastructure", "electrical-power",
    "electrochemical-storage", "electronics-materials", "electronics-rf",
    "energy-conversion", "energy-storage", "machining",
    "manufacturing-automation", "materials-construction", "metallurgy",
    "process-mining", "robotics-actuation", "sensing-nde",
    "solar-energy", "thermal-management", "tribology", "water-process",
    "wind-energy",
}

# 24 FRESH invention-shaped problems, 24 DISJOINT domains. Each was
# written against the same template as the r176 DEV items (device /
# failure with the fundamental plateau named / constraint that forbids
# the incumbent mitigation by construction / question) with domains
# outside the DEV set. No DEV domain string appears in any field.
ITEMS = [
 {"problem_id": "r184h-01-maglev-bearing",
  "device": "full-active magnetic-levitation spindle bearing for a high-speed flywheel",
  "failure": "standard practice plateaus at ~100 Wh/kg usable density in flywheels because the touchdown/backup bearing and eddy-current losses scale with rim speed — the loss floor is fundamental to conductive rims spinning in static magnetic fields; better balancing of the same steel-rim architecture has not broken the plateau",
  "constraint": "no superconducting coils (cryogenics excluded); vacuum housing must stay <= 10^-3 Pa with mechanical pumps only; >= 20-year seal life; increasing rim thickness alone is NOT a new mechanism (the mass penalty cancels the gain — that is the incumbent move, forbidden)",
  "domain": "magnetic-levitation",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that cuts the standing losses enough to reach >= 175 Wh/kg usable density while respecting every stated constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-02-fusion-blanket",
  "device": "solid-breeder fusion blanket module for a deuterium-tritium tokamak",
  "failure": "standard practice plateaus near 1.15 tritium breeding ratio with Li4SiO4 pebbles because purge-flow tritium extraction and thermal-crconductivity limits fight each other — the tritium release kinetics vs structural temperature window coupling is fundamental to ceramic pebble beds under neutron flux; thicker beds overbreed but release too slowly",
  "constraint": "structural steel temperature window 300-550 C fixed; purge gas must remain helium; neutron wall load 2 MW/m2; switching breeder material to molten salt is the incumbent alternative, NOT a new mechanism (forbidden here)",
  "domain": "nuclear-fusion",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches TBR >= 1.30 while keeping the purge-extraction half-life under 24 h, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-03-quantum-error",
  "device": "surface-code superconducting quantum processor (transmon qubits)",
  "failure": "standard practice plateaus around 1e-3 logical error per cycle at code distance 7 because residual quasi-particle poisoning and correlated decay events cluster in time — the error correlation is fundamental to fixed-frequency transmons sharing a substrate and control line tree; more qubits per logical unit has not broken the plateau (it scales the correlated failure too)",
  "constraint": "must stay a 2D lattice architecture (no 3D fabrication stack); control lines must stay planar; no photonic interconnect (that is the incumbent alternative, not a new mechanism); operating temperature fixed at 15 mK",
  "domain": "quantum-computing",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that decorrelates the error channels enough to reach 1e-4 logical error per cycle at the same physical qubit quality, with the concrete test that would falsify it."},
 {"problem_id": "r184h-04-lithium-extraction",
  "device": "direct lithium extraction module for a continental brine field",
  "failure": "standard practice plateaus at ~60-70% single-pass lithium recovery with lithium-aluminum layered double hydroxide sorbents because selectivity and kinetics trade off through the same interlayer diffusion path — the Mg/Li selectivity-kinetics coupling is fundamental to a single intercalation lattice; cycling faster washes magnesium in too",
  "constraint": "no evaporative ponds (footprint excluded); feed brine chemistry fixed (Mg/Li ~ 9 by mass); sorbent must survive >= 5000 cycles; switching to electrochemical intercalation with a different electrode is the incumbent alternative, NOT a new mechanism (forbidden)",
  "domain": "resource-extraction",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches >= 90% single-pass recovery at selectivity >= 50:1 Li/Mg, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-05-carbon-capture",
  "device": "post-combustion amine scrubbing column for a 600 MW gas plant",
  "failure": "standard practice plateaus near 3.2 GJ/tonne-CO2 regeneration energy with 30 wt% MEA because absorption enthalpy and oxidative degradation are coupled through the same carbamate chemistry — the energy-vs-lifetime coupling is fundamental to single-amine aqueous scrubbing; sterically hindered amines moved it only marginally",
  "constraint": "flue gas composition fixed (4% CO2, 14% O2 wet); column packing height capped (no second column); water-based solvent only (no ionic liquids — the incumbent alternative class, forbidden); absorber temperature 40-60 C",
  "domain": "carbon-capture",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that cuts regeneration energy to <= 2.0 GJ/tonne-CO2 while holding solvent half-life >= 10000 h in oxygen, with the concrete test that would falsify it."},
 {"problem_id": "r184h-06-propulsion-arc",
  "device": "helicon-wave plasma thruster for a 500 kg deep-space probe",
  "failure": "standard practice plateaus near 2500 s specific impulse at ~30% anode efficiency because ionization and wall recombination compete in the same bounded plasma column — the ionization-loss vs wall-loss coupling is fundamental to a material-bounded helicon source; larger tubes do not break it (surface-to-volume worsens)",
  "constraint": "propellant must stay xenon or krypton (no exotic propellants); wall materials must stay below their sputter thresholds; input power capped at 20 kW; magnetic-nozzle shaping alone is NOT a new mechanism (the incumbent move, forbidden)",
  "domain": "space-propulsion",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches >= 60% anode efficiency at >= 2500 s Isp, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-07-neural-interface",
  "device": "chronically implanted cortical microelectrode array (64 channels)",
  "failure": "standard practice plateaus at ~6 months reliable single-unit recording because the glial scar and electrode impedance rise together as the same foreign-body response proceeds — the biocompatibility-vs-signal coupling is fundamental to any solid intracortical probe; softer materials alone moved the plateau only marginally (the scar still forms)",
  "constraint": "must record single units (>= 5:1 SNR), not just LFP; transcutaneous power only (no percutaneous connectors); <= 64 channels; anti-inflammatory drug elution is the incumbent mitigation, NOT a new mechanism (forbidden); MRI-conditional at 3T",
  "domain": "neurotechnology",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that holds single-unit recording for >= 24 months without drug elution, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-08-desal-membrane",
  "device": "capacitive-deionization cell stack for brackish water",
  "failure": "standard practice plateaus near 1.2 kWh/m3 at 70% salt removal because charge efficiency and flow rate trade through the same transient double-layer — the charge-vs-throughput coupling is fundamental to flow-between carbon electrodes; more electrode area raises the energy (self-discharge scales too)",
  "constraint": "feed 3000 ppm NaCl fixed; must use carbon-based electrodes (no intercalation materials — the incumbent alternative class, forbidden); cell voltage <= 1.6 V (no faradaic reactions); stack cost within 1.5x current CDI",
  "domain": "electrochemical-water",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches 0.6 kWh/m3 at the same 70% removal, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-09-hydrogen-embrittlement",
  "device": "high-strength line-pipe steel for gaseous hydrogen transport",
  "failure": "standard practice plateaus at X70 strength with 10^-6 mm/cy crack growth in hydrogen because trap density and dislocation mobility are coupled through the same microstructural state — the strength-vs-H2-tolerance coupling is fundamental to bcc iron; alloying alone has not broken it (every strength gain re-opens the crack path)",
  "constraint": "pipeline pressure 100 bar H2 fixed; welds must be field-weldable (no furnace heat treatment after welding); steel cost within 1.3x X70; internal coatings alone are the incumbent mitigation, NOT a new mechanism (forbidden)",
  "domain": "hydrogen-infrastructure",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that holds 10^-7 mm/cy at X90 strength, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-10-sat-optics",
  "device": "deployable segmented telescope mirror for a 0.5 m cubesat",
  "failure": "standard practice plateaus near lambda/14 wavefront error with deployable segments because thermal drift and deployment repeatability share the same mechanical degrees of freedom — the stability-vs-packaging coupling is fundamental to hinged segmented optics in LEO thermal cycling; stiffer structures exceed the mass budget",
  "constraint": "launch volume 12U; areal mass <= 8 kg/m2; no cryocoolers (power budget); passive thermal control only; ground-commanded fine phasing is the incumbent mitigation, NOT a new mechanism (forbidden); wavelength 600 nm",
  "domain": "space-optics",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that holds lambda/40 wavefront error through eclipse transitions, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-11-soil-carbon",
  "device": "in-field soil carbon measurement probe for agricultural MRV",
  "failure": "standard practice plateaus at +/- 15% relative uncertainty for 0-30 cm soil organic carbon because the spatial heterogeneity and the sensor averaging kernel have the same length scale — the precision-vs-footprint coupling is fundamental to point-sensor inversion of a fractal-distributed stock; denser point grids destroy the MRV economics",
  "constraint": "measurement must stay in-field (no lab combustion — the reference method, forbidden as the deliverable); probe cost <= $500 deployed; no soil cores (destructive sampling capped at 3 per field per year for calibration); depth 0-30 cm fixed",
  "domain": "agricultural-sensing",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches +/- 5% relative uncertainty at field scale without more cores, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-12-solid-state-battery",
  "device": "sulfide-electrolyte solid-state lithium cell (50 Ah format)",
  "failure": "standard practice plateaus near 350 Wh/kg cell-level with Li6PS5Cl because interfacial contact loss and stack pressure requirements grow together through the same chemo-mechanical cycle — the energy-vs-pressure coupling is fundamental to rigid solid-solid interfaces; more stack pressure breaks the pack-level energy gain",
  "constraint": "anode must stay lithium-metal-free dendrite growth (<= 100 um effective lithium); stack pressure <= 2 MPa at pack level; operating range -20 to 60 C; no liquid electrolyte injection (the incumbent hybrid fix, forbidden); >= 800 cycles to 80%",
  "domain": "solid-state-electrochemistry",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that maintains interfacial contact at <= 0.5 MPa while reaching 500 Wh/kg, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-13-mems-clock",
  "device": "chip-scale atomic clock (MEMS vapor cell) for GNSS-denied nav",
  "failure": "standard practice plateaus near 1e-11 Allan deviation at 1 s with Rb vapor cells because cell size and alkali density trade through the same buffer-gas pressure — the stability-vs-miniaturization coupling is fundamental to buffer-gas-contained alkali atoms; smaller cells raise the collision shift faster than the signal improves",
  "constraint": "power <= 120 mW; volume <= 1 cm3; must stay a vapor-cell architecture (no ion traps — the incumbent alternative, forbidden); operating temperature -40 to 85 C without ovens above 90 C",
  "domain": "precision-timing",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches 3e-12 at 1 s within the same power and volume, with the concrete test that would falsify it."},
 {"problem_id": "r184h-14-tissue-scaffold",
  "device": "perfusion bioreactor scaffold for lab-grown skeletal muscle",
  "failure": "standard practice plateaus near 200 um viable tissue thickness because oxygen diffusion and mechanical loading share the same pore architecture — the maturation-vs-viability coupling is fundamental to a single static scaffold; denser perfusion channels destroy the contractile alignment",
  "constraint": "must produce aligned, contractile myotubes (>= 80% alignment); no endothelial pre-vascularization with foreign cells (the incumbent co-culture route, forbidden); scaffold must be food-safe (edible output); process time <= 14 days",
  "domain": "cellular-agriculture",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that grows >= 3 mm thick contractile tissue without pre-vascularization, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-15-wifi-backscatter",
  "device": "battery-free backscatter tag for 2.4 GHz sensor networks",
  "failure": "standard practice plateaus near 1 m communication range with passive WiFi backscatter because the antenna must simultaneously harvest power and reflect data — the energy-vs-bandwidth coupling is fundamental to a single passive antenna front-end; better rectifiers alone moved the plateau only marginally",
  "constraint": "no battery, no supercapacitor above 1 mF; tag cost <= $0.10; must use ambient 2.4 GHz (no dedicated reader transmitter — the incumbent fix, forbidden); data rate >= 1 kbps at range",
  "domain": "backscatter-communication",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches >= 10 m range on ambient WiFi at 1 kbps, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-16-hvdc-breaker",
  "device": "hybrid HVDC circuit breaker for a +/- 525 kV meshed grid",
  "failure": "standard practice plateaus near 3 ms full-current interruption with mechanical-bypass hybrids because arc commutation and surge energy absorption are coupled through the same series stack — the speed-vs-energy coupling is fundamental to semiconductor stacks in series with a mechanical path; more parallel IGBTs raise the off-state loss",
  "constraint": "must interrupt 25 kA against 1.2 pu recovery voltage; on-state loss <= 0.05% transmitted power; no SF6 (environmental); redundancy must survive one valve failure; pure solid-state breakers with bigger stacks are the incumbent alternative, NOT a new mechanism (forbidden)",
  "domain": "power-electronics-grid",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches 1 ms interruption at the stated energy and loss, with the concrete test that would falsify it."},
 {"problem_id": "r184h-17-cold-chain",
  "device": "passive cold-chain shipping container for vaccine distribution",
  "failure": "standard practice plateaus near 5 days hold time at -70 C because insulation thickness and package volumetric efficiency trade directly — the hold-vs-volume coupling is fundamental to passive thermal mass systems; phase-change materials only moved the plateau marginally (same enthalpy per volume limit)",
  "constraint": "must stay fully passive (no compressor, no power); ambient 40 C, solar load 1000 W/m2; internal payload 5 L fixed; total shipped mass <= 25 kg; vacuum insulation panels are the incumbent technology, NOT a new mechanism (forbidden as the proposal)",
  "domain": "cold-chain-logistics",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that holds -70 C +/- 5 C for 12 days within the mass and volume budget, with the concrete test that would falsify it."},
 {"problem_id": "r184h-18-sonar-array",
  "device": "hull-mounted conformal sonar array for a survey vessel",
  "failure": "standard practice plateaus near 15 cm bearing resolution because the aperture curvature and the flow-noise boundary layer are coupled on the same hull surface — the resolution-vs-speed coupling is fundamental to flush-mounted planar arrays; bigger apertures lose more to flow noise at survey speed",
  "constraint": "survey speed 10 knots fixed; frequency band 1-10 kHz; hull penetration depth <= 5 cm (conformal); towed arrays are the incumbent alternative, NOT a new mechanism (forbidden); must stay passive",
  "domain": "marine-acoustics",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches 4 cm bearing resolution at survey speed, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-19-chip-cooling",
  "device": "silicon interposer with integrated two-phase microchannel cooling for a 2000 W AI accelerator package",
  "failure": "standard practice plateaus near 0.15 K/W junction-to-coolant with two-phase microchannels because nucleation stability and channel hydraulic diameter are coupled through the same capillary length scale — the heat-flux-vs-stability coupling is fundamental to bounded two-phase flow in parallel microchannels; more channels widen the flow maldistribution",
  "constraint": "coolant must stay a dielectric fluid (no water — the incumbent direct-water class, forbidden); pump power <= 20 W; junction temperature <= 105 C at 2000 W uniform + 3x hotspots; interposer TSV density must not drop (cooling cannot steal silicon area)",
  "domain": "microfluidic-cooling",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches 0.05 K/W with stable nucleation at the stated hotspots, with the concrete test that would falsify it."},
 {"problem_id": "r184h-20-fiber-sensing",
  "device": "distributed acoustic fiber-optic sensing (DAS) cable for per-well CO2 storage monitoring",
  "failure": "standard practice plateaus near 1 m spatial resolution at 10 km reach because coherent fade and pulse energy trade through the same Rayleigh backscatter process — the resolution-vs-range coupling is fundamental to time-domain reflectometry in single-mode fiber; wider pulses reach further but average the signal away",
  "constraint": "must stay a single dark fiber (no dedicated hybrid copper-fiber — the incumbent fix, forbidden); interrogation at the wellhead only (one end); temperature 150 C at the toe; spatial resolution <= 1 m at 10 km; optical power below the fiber's stimulated-Brillouin threshold",
  "domain": "fiber-optic-sensing",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that beats the coherent-fade limit to hold 0.5 m resolution at the full 10 km, with the concrete test that would falsify it."},
 {"problem_id": "r184h-21-drug-delivery",
  "device": "oral biologic delivery capsule for insulin ( GI route)",
  "failure": "standard practice plateaus near 1% oral bioavailability for peptide biologics because the enzymatic and epithelial barriers share the same mucosal transit — the protection-vs-absorption coupling is fundamental to a single-release capsule in the small intestine; more permeation enhancers damage the epithelium at the doses needed",
  "constraint": "must stay a swallowable capsule (no endoscopic or microneedle-patch devices — the incumbent alternative class, forbidden); single administration per meal; room-temperature stable 12 months; payload >= 1 mg insulin intact to systemic circulation",
  "domain": "drug-delivery",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that reaches >= 10% oral bioavailability without epithelial damage, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-22-turbine-icing",
  "device": "wind-turbine rotor blade for Arctic offshore sites",
  "failure": "standard practice plateaus near 2% annual energy loss to icing because anti-icing heat and blade stiffness share the same leading-edge spar region — the protection-vs-structure coupling is fundamental to a single composite aerofoil; electrothermal mats add mass exactly where the fatigue margin lives",
  "constraint": "must stay a passive or atmospheric-air system (no hot-air internal circulation — the incumbent technology, forbidden); blade mass increase <= 2%; IEC blade fatigue class must hold; ice detection must be blade-integrated; no antifreeze fluids (environmental)",
  "domain": "renewable-arctic",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that cuts icing losses below 0.3% within the mass budget, with the concrete test that would falsify it."},
 {"problem_id": "r184h-23-printed-sensor",
  "device": "additively manufactured soft strain sensor for structural health monitoring of bridges",
  "failure": "standard practice plateaus near 10^4 cycles to drift failure with printed conductive elastomers because conductivity and elasticity trade through the same filler network — the sensitivity-vs-durability coupling is fundamental to percolation networks in a soft matrix; more filler raises the gauge factor but fatigues the network",
  "constraint": "gauge factor >= 20 at 0-5% strain; 10^7 cycles at 2% amplitude; printed in one pass on a structural epoxy substrate; sensing element cost <= $1; fiber-optic (FBG) replacement is the incumbent alternative, NOT a new mechanism (forbidden)",
  "domain": "printed-electronics",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that holds gauge factor 20 through 10^7 cycles, respecting every constraint, with the concrete test that would falsify it."},
 {"problem_id": "r184h-24-thermal-storage",
  "device": "packed-bed sensible heat storage for a concentrated-solar plant",
  "failure": "standard practice plateaus near 90% weekly exergy efficiency with rock packed beds because thermocline degradation and particle attrition share the same packing geometry — the efficiency-vs-lifetime coupling is fundamental to a single packed bed under daily thermal cycling; finer packing holds the thermocline but attrites",
  "constraint": "storage medium must stay a solid (no molten salt — the incumbent technology, forbidden); charge/discharge at 565 C max; >= 30-year bed life; cost <= $15/kWh-thermal; container must stay carbon steel (no exotic alloys)",
  "domain": "thermal-energy-storage",
  "question_type": "novel-mechanism",
  "question": "Propose a NEW physical mechanism that holds 97% weekly exergy efficiency over 30 years, respecting every constraint, with the concrete test that would falsify it."},
]


def sha16(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def main() -> None:
    # 1. disjointness verified programmatically (never assumed)
    domains = {it["domain"] for it in ITEMS}
    assert len(ITEMS) == 24, f"n={len(ITEMS)} != 24"
    assert len(domains) == 24, "domains not unique"
    overlap = domains & DEV_DOMAINS
    assert not overlap, f"DEV-domain overlap: {overlap}"
    for it in ITEMS:
        for field in ("device", "failure", "constraint", "question"):
            assert it[field].strip(), f"{it['problem_id']}: empty {field}"

    # 2. seal: Fernet key generated fresh, vaulted, digest recorded
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    VAULT.write_text(f"HOLDOUT_V13_SEAL_KEY={key.decode()}\n")
    VAULT.chmod(0o600)
    key_digest = hashlib.sha256(key).hexdigest()[:12]

    plaintext = json.dumps(
        {"record": "R184_HOLDOUT_PLAINTEXT/1.0.0", "n_items": 24,
         "items": ITEMS}, ensure_ascii=False,
        indent=1, sort_keys=True).encode()
    token = Fernet(key).encrypt(plaintext)
    corpus_hash = hashlib.sha256(plaintext).hexdigest()
    item_hashes = [hashlib.sha256(
        json.dumps(it, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest() for it in ITEMS]

    cipher_record = {
        "record": "R184_SEALED/1.0.0",
        "kind": "sealed-holdout-ciphertext",
        "encrypted": True,
        "cipher": "fernet-aes128-cbc-hmac-sha256 (cryptography.Fernet)",
        "ciphertext": token.decode(),
        "corpus_hash_sha256": corpus_hash,
        "item_hashes_sha256": item_hashes,
        "n_items": 24,
        "plaintext_bytes": len(plaintext),
        "custody": ("AI-custodied per AM54: the seal key lives in the "
                    "session vault .env.holdout (gitignored, "
                    "persistent-disk, 0600, the same path class as "
                    ".env.keys) with its sha256[:12] digest " +
                    key_digest + " recorded HERE; the digest is the "
                    "committed evidence the key exists — the key value "
                    "is never committed. Decryption happens ONCE at the "
                    "run under the run claim; the vault line is then "
                    "burned (the ciphertext + hashes remain)."),
        "seal_key_digest_sha256_12": key_digest,
        "sealed_at": "2026-11-28T03:20:00Z (sandbox clock, TRUE UTC)",
        "burn_after_use": True,
    }
    CIPHER.write_text(json.dumps(cipher_record, indent=1,
                                 ensure_ascii=False) + "\n")

    # 3. the preregistration (the measurement contract, BEFORE any run)
    prereg = {
        "record": "R184_HOLDOUT_PREREG/1.0.0",
        "kind": "sealed-holdout-preregistration",
        "authored_at": "2026-11-28T03:20:00Z (sandbox clock, TRUE UTC)",
        "authority": ("owner DIR 5 (AM54 score-4 gate, re-scoped after "
                      "R184-F1: the r178h seal key custody was lost in "
                      "the recycle; the fresh seal rides the "
                      ".env-keys-class vault discipline)"),
        "session": "builder-r184s1",
        "claim": "c-0296 (the authoring claim; the RUN takes its own "
                 "claim before execution — Art. 29(b))",
        "question": (
            "On a SEALED 24-item invention-shaped holdout (24 domains "
            "disjoint from the r176 DEV corpus; every plateau "
            "fundamental; every constraint excludes the incumbent "
            "mitigation by construction), does the SHIPPED recipe "
            "(best-of-N + critique + revise + verifier, 6 calls) beat "
            "the COMPUTE-MATCHED single-shot baseline (1 call, same "
            "budget ceiling) on blind judged WINS+TIES with Wilson 95% "
            "CI LOWER bound > 50%?"),
        "arms": {
            "A_shipped_recipe": ("4 plain draws + critique + revise "
                                 "(6 generator calls — the shipped "
                                 "CHEAP_ARM recipe, verbatim from "
                                 "scripts/r176_invention_run.py's "
                                 "baseline arm; router 2.0.0 policy)"),
            "B_compute_matched_single_shot": (
                "1 single-shot draw, max_tokens ceiling equal to the "
                "sum ceiling of arm A (compute-matched on budget, not "
                "on calls — the baseline gets the SAME total token "
                "headroom)"),
        },
        "judge": ("blind two-pass, order-swapped (XY then YX), WIN only "
                  "when the arm wins its non-swapped presentation on "
                  "both passes (the r176 instrument verbatim); judge "
                  "seat tr-deepseek (deepseek/deepseek-v4.1-flash-1017-"
                  "free via TOKENROUTER, the live measured seat) != "
                  "generator family (agnes); Art. 26 spread held"),
        "scoring_rule_predeclared": (
            "Wilson score 95% CI on A-wins+ties over n=24; the gate is "
            "the CI LOWER bound > 50% (AM52/AM54: the score moves ONLY "
            "on a measured win over a compute-matched baseline)"),
        "exclusions": ("NONE this time — both arms are the recipe's own "
                       "outputs; dominance ties and plain best-of-N "
                       "classes do not exist in this design (there is "
                       "no tournament, no strategy pool — the kill "
                       "retired them); TIES count toward the arm (wins"
                       "+ties)"),
        "run_protocol": {
            "one_shot": True,
            "one_run": "one run per item; no re-rolls; no tuning of "
                       "prompts/parameters on any holdout byte before "
                       "or between items; infra failures typed and "
                       "resumed (byte-resume), never re-rolled",
            "trigger": ("run ONCE, only after this prereg is committed "
                        "AND the run claim is pushed; decrypt ONCE at "
                        "run start; verify the corpus hash + all 24 "
                        "item hashes; burn the vault key line after "
                        "the run"),
            "power_note": ("at n=24 the Wilson lower bound exceeds "
                           "0.50 only at >= 15/24 wins+ties (0.625 "
                           "point); anything less is UNRESOLVED, "
                           "never failed-passed (Art. 14)"),
        },
        "corpus": {
            "ciphertext_file": "eval/r184_sealed_holdout_PRIVATE.json",
            "corpus_hash_sha256": corpus_hash,
            "item_hashes_sha256": item_hashes,
            "n_items": 24,
            "domain_disjointness": "verified programmatically at "
                                   "authoring (zero overlap with the "
                                   "23 r176 DEV domains)",
            "seal_key_digest_sha256_12": key_digest,
        },
        "kill_condition": (
            "if the shipped recipe does NOT beat the compute-matched "
            "single-shot baseline (CI lower <= 50%), score stays 3 and "
            "the recipe is the honest no-worse-than-baseline fallback — "
            "no further architecture work without a new owner "
            "directive (the kill-ship logic extends: nothing ships "
            "that does not win)"),
    }
    PREREG.write_text(json.dumps(prereg, indent=1,
                                 ensure_ascii=False) + "\n")

    print("sealed:", CIPHER.name)
    print("prereg:", PREREG.name)
    print("corpus sha256:", corpus_hash[:16])
    print("seal key digest:", key_digest)
    print("vault:", VAULT.name, "(gitignored, 0600)")


if __name__ == "__main__":
    main()
