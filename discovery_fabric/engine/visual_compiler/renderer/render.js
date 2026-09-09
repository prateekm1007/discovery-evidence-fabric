#!/usr/bin/env node
/**
 * render.js — R441 Visual Compiler headless renderer (node driver).
 *
 * Architecture (operator directive R441 — "Headless Three.js ⭐"):
 *
 *   canonical GLB (CadQuery/OCCT — the engineering authority)
 *     -> scene_spec.json (deterministic: grounding, camera solve,
 *        semantic material mapping — computed Python-side)
 *     -> THIS renderer: headless Chromium + Three.js (SwiftShader)
 *     -> hero / turntable / exploded / section / orthographic /
 *        dimension / poster PNGs + presentation GLBs + render_record
 *     -> visual_gate.py (independent pixel verifier)
 *
 * Why Three.js and not Blender for hero renders: the website viewer IS
 * Three.js (React Three Fiber, three 0.175.0 — identical version here).
 * Rendering the PNG set with the same renderer family as the website
 * makes the site and the technology package show the SAME render
 * (WYSIWYG), deterministically, on CPU (SwiftShader), without a 300 MB
 * Cycles install.
 *
 * Process contract:
 *   node render.js <spec.json>
 *   spec.json fields (written by render_worker.py):
 *     chrome_path   absolute path of the resolved Chromium/Chrome binary
 *     output_dir    where artifacts + render_record.json are written
 *     timeout_ms    whole-render budget (the Python side also enforces)
 *     payload       { glb_sha256, scene_spec, resolution, draft_scale,
 *                     turntable_frames, explode_factor, poster }
 *
 * Authority contract (unchanged from R419 §5-7, re-expressed):
 *   - the renderer NEVER edits geometry: hero.glb re-exports the SAME
 *     vertices (counts compared and recorded); exploded.glb is a
 *     DISCLOSED presentation variant (per-part translation, offsets
 *     recorded in the record and re-verified by the gate);
 *   - no randomness, no network beyond a loopback server serving the
 *     local three modules — deterministic per (GLB, scene_spec);
 *   - every outcome is typed in the record; a failed view is recorded
 *     failed — never a silent gap (Art. VI/XXV). Presentation-only:
 *     this renderer changes NO epistemic field of any run (Art. XXVIII).
 */
import fs from "node:fs";
import http from "node:http";
import crypto from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const THREE_DIR = path.join(__dirname, "node_modules", "three");

const spec = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const OUT = spec.output_dir;
fs.mkdirSync(OUT, { recursive: true });
// the canonical GLB is read from ITS OWN canonical path (the file the
// record hashes) — the authority travels by path + sha256, never by
// re-encoding (Art. II: exact bytes, no mutation in transit)
const GLB_BYTES = fs.readFileSync(spec.source_glb);

const record = {
  stage: "RENDER",
  render_pipeline: "VISUAL_COMPILER_HEADLESS_THREE",
  renderer_family: "three@0.175.0 + Chromium SwiftShader (same family as webapp)",
  source_glb_sha256: spec.payload?.glb_sha256,
  started_at: new Date().toISOString(),
  views: {},
  exports: {},
  status: "OK",
  finished: false,
};
let t0 = Date.now();

function sha256(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function saveArtifact(name, bytes) {
  const p = path.join(OUT, name);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, Buffer.from(bytes));
  return { bytes: bytes.length, sha256: sha256(Buffer.from(bytes)) };
}

// ---------------------------------------------------------------------------
// loopback server: the ONLY origin (127.0.0.1, ephemeral port). Serves the
// local three modules + the page; receives artifacts / record / logs.
// ---------------------------------------------------------------------------
const MIME = {
  ".js": "text/javascript", ".json": "application/json",
  ".html": "text/html", ".glb": "model/gltf-binary", ".png": "image/png",
};

const pageHtml = `<!doctype html>
<html><head><meta charset="utf-8"><title>vc-render</title>
<script type="importmap">
{"imports": {"three": "/vendor/build/three.module.js",
             "three/addons/": "/vendor/examples/jsm/"}}
</script>
</head><body style="margin:0;background:transparent">
<script type="module">
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const log = (m) => fetch("/log", {method:"POST", body:String(m)});
const put = async (name, bytes) => (await (await fetch(
  "/artifact?name=" + encodeURIComponent(name),
  {method:"POST", body:bytes})).json());
const postRecord = (obj) => fetch("/record",
  {method:"POST", body:JSON.stringify(obj)});
const canvasToBlob = (canvas) => new Promise((ok) =>
  canvas.toBlob((b) => ok(b), "image/png"));

// the PAGE-side record (posted to node at the end; node merges it into
// render_record.json). The node-side record is a different object —
// this one is the page's own claim, typed, never silent.
const record = { views: {}, exports: {}, status: "OK" };
window.__t0 = Date.now();

try {
const payload = await (await fetch("/payload")).json();
const SS = payload.scene_spec;
const SOLVE = SS.solve || SS.camera || {};   // the deterministic solve blob
const RES = payload.resolution;               // [w, h] final renders
const DRAFT = payload.draft_scale || 0.35;
const VIEWS = payload.views || {};

// ---- renderer -------------------------------------------------------------
const canvas = document.createElement("canvas");
document.body.appendChild(canvas);
const renderer = new THREE.WebGLRenderer({
  canvas, antialias: false, alpha: true, preserveDrawingBuffer: true,
});
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled = true;

const world = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
world.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
world.environmentIntensity = SS.lights?.environment ?? 0.9;

// ---- model import + grounding (transform computed Python-side) ------------
const glbBuf = await (await fetch("/model.glb")).arrayBuffer();
const gltf = await new Promise((ok, fail) =>
  new GLTFLoader().parse(glbBuf, "", ok, fail));
const model = gltf.scene;
const rawCounts = { meshes: 0, verts: 0, tris: 0 };
model.traverse((o) => { if (o.isMesh) {
  rawCounts.meshes++;
  rawCounts.verts += o.geometry.attributes.position?.count || 0;
  rawCounts.tris += (o.geometry.index
    ? o.geometry.index.count
    : o.geometry.attributes.position?.count || 0) / 3;
}});

const g = new THREE.Group();
g.add(model);
const s = SS.grounding.scale;
g.scale.setScalar(s);
g.position.set(-SS.model.center[0] * s, -SS.model.min_y * s,
  -SS.model.center[2] * s);
world.add(g);
g.updateMatrixWorld(true);
const modelBox = new THREE.Box3().setFromObject(g);
const modelCenter = modelBox.getCenter(new THREE.Vector3());
// fit radius is a top-level spec field (scene_builder.grounding_fit_radius);
// a non-finite value here poisons every downstream constant (NaN ground
// plane, NaN shadow camera) — fail fast, typed (Art. VI)
const fitR = Number(SS.grounding_fit_radius);
if (!Number.isFinite(fitR) || fitR <= 0) {
  throw new Error("invalid grounding_fit_radius in scene spec: " +
    SS.grounding_fit_radius);
}

// ---- canonical part identity (matches scene_builder.gltf_doc exactly) -----
// A "part" = a MESH-BEARING glTF NODE (the Python walker's definition).
// The alignment walks gltf.parser.json (the actual document) IN LOCKSTEP
// with the three.js scene tree: gltf.scene.children[i] corresponds to
// scenes[scene].nodes[i], and node.children[j] to obj.children[j] —
// GLTFLoader preserves both orders. Structural guesses fail (a plain
// group of meshes is indistinguishable from a multi-primitive group);
// the document walk does not guess (Art. II).
const parts = [];      // [{obj, name}]
{
  const doc = gltf.parser.json;
  let partIdx = 0;
  const ensureName = (obj) => {
    partIdx++;
    if (!obj.name || !obj.name.trim()) {
      obj.name = "part-" + String(partIdx).padStart(3, "0");
    }
    parts.push({ obj, name: obj.name });
  };
  const align = (nodeIdx, obj) => {
    if (nodeIdx == null || !obj) return;
    const nodeDef = doc.nodes[nodeIdx];
    if (nodeDef.mesh !== undefined) {
      ensureName(obj);       // single-prim: obj IS the Mesh;
      return;                // multi-prim: obj is its Group — either way
    }                        // the meshes below belong to this part
    (nodeDef.children || []).forEach((childIdx, i) =>
      align(childIdx, obj.children[i]));
  };
  const sceneIdx = doc.scene || 0;
  (doc.scenes[sceneIdx].nodes || []).forEach((idx, i) =>
    align(idx, gltf.scene.children[i]));
}

// ---- semantic materials (mapping decided Python-side; applied verbatim) ---
const matMap = SS.materials?.mapping || {};
const applied = {};
const clipPlanes = [];
for (const { obj, name } of parts) {
  const cls = matMap[name] || matMap["*"] ||
    { class: "polymer", color: [0.72, 0.73, 0.76], metallic: 0.15,
      roughness: 0.5 };
  obj.traverse((m) => {
    if (!m.isMesh) return;
    const hasVC = !!m.geometry.attributes.color;
    const mat = new THREE.MeshPhysicalMaterial({
      color: hasVC ? 0xffffff : new THREE.Color(...cls.color),
      vertexColors: hasVC,
      metalness: cls.metallic ?? 0.1,
      roughness: cls.roughness ?? 0.5,
    });
    if (cls.alpha != null && cls.alpha < 1) {
      mat.transparent = true; mat.opacity = cls.alpha;
    }
    if (cls.transmission) mat.transmission = cls.transmission;
    mat.clippingPlanes = clipPlanes;
    mat.clipShadows = true;
    m.material = mat;
    m.castShadow = true;
    m.receiveShadow = true;
  });
  applied[name] = { class: cls.class,
    meshes: obj.isMesh ? 1
      : obj.children.filter((c) => c.isMesh).length };
}

// ---- lights + ground: key / fill / rim / ambient + contact shadow ---------
// The key sits ~75 degrees OFF the camera azimuth (front-left): its
// shadow falls visibly BESIDE the model's base instead of hiding under
// it (the R441 acceptance run caught the original key at 36 deg —
// nearly behind the 38 deg camera — which physically suppressed the
// contact shadow the Constitution requires)
const key = new THREE.DirectionalLight(0xfff1e0, 2.4);
key.position.set(-0.5, 1.0, 0.45).normalize().multiplyScalar(fitR * 4)
  .add(new THREE.Vector3(0, fitR * 1.4, 0));
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.near = 0.5;
key.shadow.camera.far = fitR * 14;
key.shadow.camera.left = key.shadow.camera.bottom = -fitR * 3.4;
key.shadow.camera.right = key.shadow.camera.top = fitR * 3.4;
key.shadow.bias = -0.0002;
key.shadow.radius = 2.5;
world.add(key);
const fill = new THREE.DirectionalLight(0xdfe6ee, 0.85);
fill.position.set(-fitR * 3, fitR * 1.2, fitR * 2.4);
world.add(fill);
const rim = new THREE.DirectionalLight(0xf5e8d8, 1.25);
rim.position.set(-fitR * 2.2, fitR * 2.6, -fitR * 3.4);
world.add(rim);
world.add(new THREE.AmbientLight(0xffffff, 0.22));
const ground = new THREE.Mesh(new THREE.CircleGeometry(fitR * 6, 72),
  new THREE.ShadowMaterial({ opacity: 0.42 }));
ground.rotation.x = -Math.PI / 2;
ground.position.y = 0.0005;
ground.receiveShadow = true;
world.add(ground);

// ---- cameras + helpers -----------------------------------------------------
const pcam = new THREE.PerspectiveCamera(30, RES[0] / RES[1], 0.05, fitR * 40);
const ocam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.05, fitR * 40);

function sizeCanvas(w, h) {
  renderer.setPixelRatio(1);
  renderer.setSize(w, h, false);
}
function heroPos(dist, azDeg, elDeg, target) {
  // target arrives as a plain [x,y,z] array from the Python solver —
  // convert once (a raw array has no .x and silently NaNs everything)
  const t = Array.isArray(target) ? new THREE.Vector3(...target) : target;
  const az = azDeg * Math.PI / 180, el = elDeg * Math.PI / 180;
  return new THREE.Vector3(
    t.x + dist * Math.cos(el) * Math.sin(az),
    t.y + dist * Math.sin(el),
    t.z + dist * Math.cos(el) * Math.cos(az));
}
function measureOccupancy() {
  const w = canvas.width, h = canvas.height;
  const px = new Uint8Array(w * h * 4);
  renderer.getContext().readPixels(0, 0, w, h,
    renderer.getContext().RGBA, renderer.getContext().UNSIGNED_BYTE, px);
  let on = 0;
  let minRow = h, maxRow = -1, minCol = w, maxCol = -1;
  let sMaxRow = -1, sMinRow = h, sMaxCol = -1, sMinCol = w;
  for (let y = 0; y < h; y++) {
    // gl.readPixels is BOTTOM-UP (row 0 = framebuffer bottom); every
    // row fraction here is expressed in PNG orientation (row 0 = top)
    // — the R441 battery caught the un-flipped version anchoring the
    // model's TOP at the desired BASE position (Art. II: exact
    // coordinates, no silent axis flips)
    const pngY = h - 1 - y;
    for (let x = 0; x < w; x++) {
      const a = px[(y * w + x) * 4 + 3];
      if (a > 8) {
        on++;
        if (pngY < minRow) minRow = pngY;
        if (pngY > maxRow) maxRow = pngY;
        if (x < minCol) minCol = x;
        if (x > maxCol) maxCol = x;
        if (a > 154) {           // SOLID body (not the soft shadow —
          if (pngY < sMinRow) sMinRow = pngY;  // the base sits on the body)
            if (pngY > sMaxRow) sMaxRow = pngY;
          if (x < sMinCol) sMinCol = x;
          if (x > sMaxCol) sMaxCol = x;
        }
      }
    }
  }
  const area = on / (w * h);
  const heightFrac = maxRow >= 0 ? (maxRow - minRow + 1) / h : 0;
  const widthFrac = maxCol >= 0 ? (maxCol - minCol + 1) / w : 0;
  return {
    area: +area.toFixed(4),
    height_frac: +heightFrac.toFixed(4),
    width_frac: +widthFrac.toFixed(4),
    dominant: +Math.max(heightFrac, widthFrac).toFixed(4),
    solid_base_row: sMaxRow,
    // clipping = the SOLID BODY cut by a frame edge (the contact
    // shadow may legitimately fade toward the frame bottom; the body
    // may never be cut — the anti-clip witness)
    clipped: sMaxRow >= h - 1 || sMinRow <= 0 ||
             sMaxCol >= w - 1 || sMinCol <= 0,
  };
}
async function shoot(name) {
  const blob = await canvasToBlob(canvas);
  const entry = await put(name, await blob.arrayBuffer());
  record.views[name] = { ...(record.views[name] || {}), ...entry };
  return entry;
}

// auto-frame: bounded deterministic correction loop (draft renders) until
// the model occupies its target band; the TARGET and BAND are decisions of
// the Python camera solver, the measurement is re-verified independently
// by visual_gate.py on the final PNG (Art. III — verifier never trusts)
async function autoFrame(cam) {
  const dw = Math.max(64, Math.round(RES[0] * DRAFT));
  const dh = Math.max(64, Math.round(RES[1] * DRAFT));
  sizeCanvas(dw, dh);
  const draftAspect = dw / dh;
  pcam.aspect = draftAspect;
  pcam.updateProjectionMatrix();
  const trail = [];
  let target = Array.isArray(cam.target)
    ? new THREE.Vector3(...cam.target) : cam.target.clone();
  const desiredBase = cam.desired_base_fraction ?? 0.10;
  const render = () => {
    pcam.position.copy(heroPos(cam.distance, cam.azimuth, cam.elevation,
      target));
    pcam.lookAt(target);
    renderer.render(world, pcam);
    return measureOccupancy();
  };
  // PASS 1 — occupancy: bounded deterministic correction until the
  // draft composition lands INSIDE the gate band (the same [0.70, 0.85]
  // the gate enforces — aiming at the exact target can over-correct a
  // shape into clipping; the band is the contract, not the midpoint)
  const band = cam.occupancy_band || [0.70, 0.85];
  for (let i = 0; i <= cam.max_iter; i++) {
    const m = render();
    trail.push({ iter: i, phase: "occupancy",
                 distance: +cam.distance.toFixed(4),
                 dominant: m.dominant, area: m.area,
                 clipped: m.clipped });
    const inBand = m.dominant >= band[0] && m.dominant <= band[1];
    if (!m.clipped && inBand) break;
    if (m.clipped) {
      // clipped = the model is too BIG: the frame must WIDEN. (The
      // R441 battery caught the inverse correction live — the draft at
      // d=10.68 was unclipped and in-band; chasing 0.78 exactly then
      // clipped the frame three iterations deep.)
      cam.distance *= 1.10;
    } else {
      cam.distance = Math.max(0.8, cam.distance * m.dominant /
        cam.occupancy_target);
    }
  }
  // PASS 2 — composition: the base must sit at its desired frame
  // fraction (ground band below). Perspective near-edge effects differ
  // per model shape — the response to a target shift is ~1:1 for a
  // tall model and a fraction of that for a squat-wide one — so the
  // correction GAIN is measured from the previous iteration's achieved
  // movement (adaptive, deterministic, bounded; the gate re-verifies
  // the final PNG independently)
  const vSpan = () => 2 * cam.distance * Math.tan(cam.fov * Math.PI / 360);
  let prevBase = null, prevShiftFrac = 0;
  for (let i = 0; i < (cam.composition_max_iter ?? 3); i++) {
    const m = render();
    const h = dh;
    const baseFrac = m.solid_base_row != null && m.solid_base_row >= 0
      ? m.solid_base_row / h : null;
    trail.push({ iter: i, phase: "composition",
                 base_frac: baseFrac == null ? null : +baseFrac.toFixed(4) });
    if (baseFrac == null || m.clipped) break;
    // PHYSICS (now measured on correctly-oriented rows): the view
    // direction is fixed (camera translates with the target), so
    // target UP moves the world content DOWN the frame — row
    // fractions (from top) move WITH the target. base too low in
    // frame (baseFrac > desired, delta > 0) -> target moves DOWN.
    const delta = baseFrac - (1 - desiredBase);
    if (Math.abs(delta) <= 0.012) break;
    let gain = 1;
    if (prevBase != null && Math.abs(prevShiftFrac) > 1e-9) {
      // measured response: how much the base actually moved per unit
      // target shift (≈1; shape-dependent at frame edges) — clamped
      const response = (prevBase - baseFrac) / prevShiftFrac;
      if (Number.isFinite(response) && Math.abs(response) > 0.05) {
        gain = Math.min(4, Math.max(0.25, Math.abs(response)));
      }
    }
    const shiftFrac = delta * gain;
    target.y -= shiftFrac * vSpan();
    prevBase = baseFrac;
    prevShiftFrac = shiftFrac;
  }
  return { trail, target: [target.x, target.y, target.z] };
}

const heroCam = { ...SOLVE.camera.hero, max_iter: SOLVE.camera.auto_frame_max_iter ?? 3 };
await log("scene built; auto-framing hero");
const heroFrame = await autoFrame(heroCam);
const heroTarget = Array.isArray(heroFrame.target)
  ? new THREE.Vector3(...heroFrame.target)
  : new THREE.Vector3(...heroCam.target);
await log("hero framed at d=" + heroCam.distance.toFixed(3));
sizeCanvas(RES[0], RES[1]);
pcam.aspect = RES[0] / RES[1];
pcam.updateProjectionMatrix();
pcam.position.copy(heroPos(heroCam.distance, heroCam.azimuth,
  heroCam.elevation, heroTarget));
pcam.lookAt(heroTarget);
renderer.render(world, pcam);
const heroMeasure = measureOccupancy();
record.views["hero.png"] = { occupancy: heroMeasure,
  camera: { distance: +heroCam.distance.toFixed(4),
            target: [heroTarget.x, heroTarget.y, heroTarget.z]
              .map((v) => +v.toFixed(4)) },
  auto_frame_trail: heroFrame.trail };
if (VIEWS.hero !== false) await shoot("hero.png");

// ---- turntable -------------------------------------------------------------
// the turntable serves the website gallery at half resolution — twelve
// full-size SwiftShader color buffers were the single largest memory
// line in the R441 acceptance measurement (595 MB PSS tree peak);
// halving the surface area is the honest fix, not a smaller guard
if (VIEWS.turntable !== false) {
  const N = payload.turntable_frames || 12;
  const tRes = payload.turntable_resolution ||
    [Math.round(RES[0] / 2), Math.round(RES[1] / 2)];
  sizeCanvas(tRes[0], tRes[1]);
  pcam.aspect = tRes[0] / tRes[1];
  pcam.updateProjectionMatrix();
  for (let i = 0; i < N; i++) {
    const az = heroCam.azimuth + (360 * i) / N;
    pcam.position.copy(heroPos(heroCam.distance, az, heroCam.elevation,
      heroTarget));
    pcam.lookAt(heroTarget);
    renderer.render(world, pcam);
    await shoot("turntable/frame-" + String(i + 1).padStart(2, "0") + ".png");
  }
  sizeCanvas(RES[0], RES[1]);
  pcam.aspect = RES[0] / RES[1];
  pcam.updateProjectionMatrix();
}

// ---- exploded (disclosed presentation variant; offsets recorded) -----------
if (VIEWS.exploded !== false) {
  if (parts.length < 2) {
    // single-part architecture: there is nothing to separate. The
    // honest output is a typed disclosure, NOT a faked explosion of a
    // one-piece object (Art. XXV: not-applicable stays not-applicable)
    record.views["exploded.png"] = {
      skipped: "single-part architecture — exploded view not applicable",
      parts: parts.length };
    record.exports["exploded.glb"] = {
      skipped: "exploded view not applicable (single part)" };
  } else {
  window.__explodeOffsets = {};
  const factor = payload.explode_factor ?? 0.55;
  for (const { obj, name } of parts) {
    obj.updateMatrixWorld(true);
    const pb = new THREE.Box3().setFromObject(obj);
    if (pb.isEmpty()) continue;
    const pc = pb.getCenter(new THREE.Vector3());
    const dir = pc.clone().sub(modelCenter);
    dir.y *= 0.35;
    if (dir.length() < 1e-4) dir.set(0, 0.35, 0);
    dir.normalize().multiplyScalar(factor * fitR);
    window.__explodeOffsets[name] = [
      +dir.x.toFixed(5), +dir.y.toFixed(5), +dir.z.toFixed(5)];
    const ws = obj.getWorldScale(new THREE.Vector3());
    const k = (ws.x || 1) * s;
    obj.position.add(dir.clone().divideScalar(k || 1));
  }
  g.updateMatrixWorld(true);
  // the explosion ENLARGES the silhouette — the exploded view gets its
  // own projected-extent camera solve (same anti-clip math as the hero)
  const ebox = new THREE.Box3().setFromObject(g);
  const eSize = new THREE.Vector3(); ebox.getSize(eSize);
  const eCtr = new THREE.Vector3(); ebox.getCenter(eCtr);
  const el = heroCam.elevation * Math.PI / 180;
  const az = heroCam.azimuth * Math.PI / 180;
  const planW = Math.abs(eSize.x * Math.sin(az)) +
    Math.abs(eSize.z * Math.cos(az));
  const planDiag = Math.hypot(eSize.x, eSize.z);
  const hProj = eSize.y * Math.cos(el) + planDiag * Math.sin(el);
  const tanH = Math.tan(heroCam.fov * Math.PI / 360);
  const aspect = RES[0] / RES[1];
  const occ = heroCam.occupancy_target;
  const eDist = Math.max((hProj / occ / 2) / tanH,
    (planW / occ / 2) / (tanH * aspect));
  const eTarget = [eCtr.x, eCtr.y, eCtr.z];
  sizeCanvas(RES[0], RES[1]);
  pcam.aspect = aspect;
  pcam.updateProjectionMatrix();
  pcam.position.copy(heroPos(eDist, heroCam.azimuth, heroCam.elevation,
    eTarget));
  pcam.lookAt(new THREE.Vector3(...eTarget));
  renderer.render(world, pcam);
  await shoot("exploded.png");
  record.exploded_camera = { distance: +eDist.toFixed(4),
    target: eTarget.map((v) => +v.toFixed(4)),
    exploded_size: [+eSize.x.toFixed(4), +eSize.y.toFixed(4),
                    +eSize.z.toFixed(4)] };
  const ex = new GLTFExporter();
  const buf = await new Promise((ok, fail) =>
    ex.parse(g, (b) => ok(b), fail, { binary: true }));
  record.exports["exploded.glb"] = await put("exploded.glb", buf);
  record.exploded_offsets = window.__explodeOffsets;
  for (const { obj } of parts) obj.position.set(0, 0, 0);
  g.updateMatrixWorld(true);
  }
}

// ---- section (clip-plane viewing slice — honestly disclosed) ---------------
if (VIEWS.section !== false) {
  const size = new THREE.Vector3();
  modelBox.getSize(size);
  const axis = ["x", "y", "z"][
    [size.x, size.y, size.z].indexOf(Math.max(size.x, size.y, size.z))];
  const constant = modelCenter[axis];
  window.__section = { axis, constant: +constant.toFixed(5) };
  const n = new THREE.Vector3(
    axis === "x" ? -1 : 0, axis === "y" ? -1 : 0, axis === "z" ? -1 : 0);
  clipPlanes.push(new THREE.Plane(n, constant));
  renderer.render(world, pcam);
  await shoot("section.png");
  clipPlanes.length = 0;
}

// ---- orthographic (front / side / top / iso) --------------------------------
if (VIEWS.orthographic !== false) {
  const sph = modelBox.getBoundingSphere(new THREE.Sphere());
  const dirs = { front: [0, 0, 1], side: [1, 0, 0], top: [0, 1, 0],
                 iso: [0.62, 0.36, 1] };
  for (const [name, d] of Object.entries(dirs)) {
    const dv = new THREE.Vector3(...d).normalize();
    const up = name === "top" ? new THREE.Vector3(0, 0, -1)
                              : new THREE.Vector3(0, 1, 0);
    const halfH = sph.radius * 1.06;
    ocam.left = -halfH * (RES[0] / RES[1]);
    ocam.right = halfH * (RES[0] / RES[1]);
    ocam.top = halfH;
    ocam.bottom = -halfH;
    ocam.position.copy(modelCenter).addScaledVector(dv, sph.radius * 3);
    ocam.up.copy(up);
    ocam.lookAt(modelCenter);
    ocam.updateProjectionMatrix();
    renderer.render(world, ocam);
    await shoot("orthographic/" + name + ".png");
  }
}

// ---- dimension view (hero framing + measured W/D/H annotations) ------------
if (VIEWS.dimension !== false) {
  pcam.position.copy(heroPos(heroCam.distance, heroCam.azimuth,
    heroCam.elevation, heroTarget));
  pcam.lookAt(heroTarget);
  renderer.render(world, pcam);

  const ov = document.createElement("canvas");
  ov.width = RES[0]; ov.height = RES[1];
  const ctx = ov.getContext("2d");
  ctx.drawImage(canvas, 0, 0, ov.width, ov.height);
  const raw = SS.model.raw_size;                     // glTF units (mm)
  const P = (x, y, z) => {
    const v = new THREE.Vector3(x, y, z).project(pcam);
    return [(v.x + 1) / 2 * ov.width, (1 - v.y) / 2 * ov.height];
  };
  const b = modelBox;
  const o = fitR * 0.16;                              // outward offset
  const dim = (a, bpt, label) => {
    ctx.strokeStyle = "#d8dde6"; ctx.fillStyle = "#eef1f5";
    ctx.lineWidth = 2.2; ctx.font = "600 26px system-ui, sans-serif";
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(bpt[0], bpt[1]);
    ctx.stroke();
    const mx = (a[0] + bpt[0]) / 2, my = (a[1] + bpt[1]) / 2;
    ctx.textAlign = "center"; ctx.textBaseline = "bottom";
    ctx.fillText(label, mx, my - 8);
  };
  dim(P(b.min.x - o, 0, b.max.z + o), P(b.max.x + o, 0, b.max.z + o),
      "W " + raw[0].toFixed(1) + " mm");
  dim(P(b.max.x + o, 0, b.min.z - o), P(b.max.x + o, 0, b.max.z + o),
      "D " + raw[2].toFixed(1) + " mm");
  dim(P(b.max.x + o, b.min.y, b.max.z + o),
      P(b.max.x + o, b.max.y, b.max.z + o),
      "H " + raw[1].toFixed(1) + " mm");
  await (async () => {
    const blob = await canvasToBlob(ov);
    record.views["dimension.png"] = await put("dimension.png",
      await blob.arrayBuffer());
  })();
}

// ---- poster (the hero render embedded 1:1 — parity by construction) --------
if (VIEWS.poster !== false) {
  const pw = payload.poster?.width || 1024;
  const ph = payload.poster?.height || 1448;
  const bandH = Math.round(ph * 0.085);
  // image area: the hero render at its OWN aspect, fitted to the
  // poster width and centered vertically (no re-render at a different
  // aspect — the poster shows THE hero render, so the gate's parity
  // check is exact, not statistical)
  const imgH = Math.round(pw / (RES[0] / RES[1]));
  const imgY = bandH + Math.max(0, Math.round((ph - 2 * bandH - imgH) / 2));
  const poster = document.createElement("canvas");
  poster.width = pw; poster.height = ph;
  const c = poster.getContext("2d");
  c.fillStyle = "#f6f6f8"; c.fillRect(0, 0, pw, ph);
  c.drawImage(canvas, 0, imgY, pw, imgH);
  const meta = payload.poster || {};
  c.fillStyle = "#15171c";
  c.font = "700 44px system-ui, sans-serif";
  c.textBaseline = "middle";
  c.textAlign = "left";
  c.fillText(String(meta.title || "Technology artifact").slice(0, 46),
             54, bandH * 0.52);
  c.fillStyle = "#5a6070";
  c.font = "400 26px system-ui, sans-serif";
  c.fillText(String(meta.subtitle || "").slice(0, 90), 54, bandH * 1.32);
  c.fillText(String(meta.date || ""), 54, ph - bandH * 0.55);
  c.fillStyle = "#9aa1b0";
  c.font = "400 22px system-ui, sans-serif";
  c.textAlign = "right";
  c.fillText("Toscanini Visual Compiler", pw - 54, ph - bandH * 0.55);
  c.strokeStyle = "#15171c"; c.lineWidth = 3;
  c.beginPath(); c.moveTo(54, bandH * 0.78); c.lineTo(pw - 54, bandH * 0.78);
  c.stroke();
  const blob = await canvasToBlob(poster);
  record.views["poster.png"] = await put("poster.png",
    await blob.arrayBuffer());
  // the exact rect the hero render occupies — the gate crops HERE
  record.poster_image_rect = { x: 0, y: imgY, w: pw, h: imgH };
}

// ---- hero.glb (grounded + materialized; SAME vertices — verified) ----------
if (VIEWS.export_hero_glb !== false) {
  const ex = new GLTFExporter();
  const buf = await new Promise((ok, fail) =>
    ex.parse(g, (b) => ok(b), fail, { binary: true }));
  const outCounts = { meshes: 0, verts: 0, tris: 0 };  g.traverse((o) => { if (o.isMesh) {
    outCounts.meshes++;
    outCounts.verts += o.geometry.attributes.position?.count || 0;
    outCounts.tris += (o.geometry.index
      ? o.geometry.index.count
      : o.geometry.attributes.position?.count || 0) / 3;
  }});
  record.exports["hero.glb"] = await put("hero.glb", buf);
  record.topology_comparison = {
    imported: rawCounts, exported: outCounts,
    identical: rawCounts.meshes === outCounts.meshes &&
      rawCounts.verts === outCounts.verts &&
      rawCounts.tris === outCounts.tris,
  };
}

record.materials_applied = applied;
record.lights = { environment: "three RoomEnvironment (procedural HDR/PMREM)",
  key: "directional 0xfff1e0 int 2.4 castShadow (front-left, 75 deg off camera)",
  fill: "directional 0xdfe6ee int 0.85",
  rim: "directional 0xf5e8d8 int 1.25", ambient: 0.22,
  contact_shadow: "ShadowMaterial ground plane opacity 0.42 (PCFSoft)" };
record.tone_mapping = "ACESFilmic exposure 1.05, sRGB output";
// a view is produced (sha256) or TYPED-skipped (disclosed) — a view
// that is neither is the only path to RENDER_PARTIAL
record.status = Object.values(record.views).every((v) => v.sha256 || v.skipped)
  ? "OK" : "RENDER_PARTIAL";
record.finished = true;
record.seconds = +((Date.now() - window.__t0) / 1000).toFixed(2);
await postRecord(record);
} catch (e) {
  record.status = "RENDER_FAILED";
  record.error = (e && (e.stack || e.message)) || String(e);
  record.finished = true;
  await log("FAILED: " + record.error);
  await postRecord(record);
}
</script></body></html>`;

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (req.method === "POST") {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const body = Buffer.concat(chunks);
      try {
        if (url.pathname === "/artifact") {
          const name = url.searchParams.get("name") || "unnamed";
          const entry = saveArtifact(name, body);
          res.writeHead(200, { "content-type": "application/json" });
          res.end(JSON.stringify(entry));
        } else if (url.pathname === "/record") {
          Object.assign(record, JSON.parse(body.toString("utf8")));
          res.writeHead(200); res.end("ok");
        } else if (url.pathname === "/log") {
          console.error(`[vc-page] ${body.toString("utf8")}`);
          res.writeHead(200); res.end("ok");
        } else { res.writeHead(404); res.end(); }
      } catch (e) {
        res.writeHead(500); res.end(String(e));
      }
    });
    return;
  }
  if (url.pathname === "/payload") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(spec.payload));
    return;
  }
  if (url.pathname === "/model.glb") {
    res.writeHead(200, { "content-type": "model/gltf-binary" });
    res.end(GLB_BYTES);
    return;
  }
  if (url.pathname === "/page") {
    res.writeHead(200, { "content-type": "text/html" });
    res.end(pageHtml);
    return;
  }
  const rel = url.pathname.replace(/^\/vendor\//, "");
  const f = path.join(THREE_DIR, rel);
  if (!f.startsWith(THREE_DIR) || !fs.existsSync(f) ||
      !fs.statSync(f).isFile()) {
    res.writeHead(404); res.end();
    return;
  }
  res.writeHead(200,
    { "content-type": MIME[path.extname(f)] || "text/plain" });
  fs.createReadStream(f).pipe(res);
});

server.listen(0, "127.0.0.1", async () => {
  const port = server.address().port;
  let exitCode = 0;
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: spec.chrome_path,
      headless: true,
      args: [
        "--no-sandbox", "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--use-angle=swiftshader",
        "--enable-unsafe-swiftshader",
        "--disable-gpu-sandbox",
        "--no-first-run",
        "--disable-background-networking",
        "--disable-features=Translate,BackForwardCache",
        "--disable-component-update",
      ],
    });
    const page = await browser.newPage();
    page.on("pageerror", (e) => console.error(`[pageerror] ${e.message}`));
    page.on("console", (m) => {
      if (m.type() === "error") console.error(`[console] ${m.text()}`);
    });
    t0 = Date.now();
    await page.goto(`http://127.0.0.1:${port}/page`,
      { waitUntil: "load", timeout: 60000 });
    const deadline = Date.now() + (spec.timeout_ms || 420000);
    while (Date.now() < deadline && !record.finished) {
      await new Promise((r) => setTimeout(r, 400));
    }
    if (!record.finished && record.status === "OK") {
      record.status = "RENDER_TIMEOUT";
      record.note = "page did not signal completion within budget";
    }
    await browser.close();
  } catch (e) {
    record.status = record.status === "OK" ? "RENDER_FAILED" : record.status;
    record.error = `${e.name}: ${e.message}`;
    exitCode = 1;
    try { await browser?.close(); } catch { /* already gone */ }
  }
  record.seconds = +((Date.now() - t0) / 1000).toFixed(2);
  fs.writeFileSync(path.join(OUT, "render_record.json"),
    JSON.stringify(record, null, 2));
  console.error(`[render.js] status=${record.status} ` +
    `views=${Object.keys(record.views).length}`);
  server.close();
  process.exit(record.status === "OK" || record.status === "RENDER_PARTIAL"
    ? 0 : (exitCode || 1));
});
