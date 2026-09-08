"use client";

// Interactive 3D viewer — the R435 HERO presentation.
//
// Two variants:
//   * "hero"   — the technology stage: fills the hero viewport, soft
//                ground shadows, gentle auto-rotate until the user
//                takes control, product-language status badge
//                ("Engineering model · generation 2"). This is the
//                product surface the user came for.
//   * "inline" — the compact embedded form used in deep sections.
//
// Honesty is structural, unchanged: the badge wording derives from the
// same epistemic facts the record carries — engineering geometry is a
// deterministic CAD result; provider reconstructions are reconstructions
// and stay labeled (never physical truth — Art. XXXVIII); conceptual
// architectures never claim engineering dimensions. The full machine
// vocabulary stays in the tooltip/deep layer, off the primary surface.
//
// Controls: rotate / zoom / pan / reset / wireframe / clip-plane /
// fullscreen. The data-model-viewer attribute is the machine-checked
// single-viewer contract (R432 section 14 — exactly ONE per technology
// page).

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { ContactShadows, OrbitControls, useGLTF } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { Box3, Plane, Sphere, Vector3 } from "three";

// The render clip-plane: normal -Z, constant 0 → hides z > 0 half of
// the model in the VIEW. A viewing aid only — honestly labeled, never a
// section drawing.
const CLIP_PLANE = new Plane(new Vector3(0, 0, -1), 0);

// the measured model layout — drives the model-aware camera framing
// and the ground-contact shadow placement (R435: the artifact must
// COMMAND the hero and read as GROUNDED, whatever its proportions)
export type ModelLayout = {
  bottom: number;
  center: [number, number, number];
  radius: number;
};

function FittedModel({
  url,
  onLayout,
}: {
  url: string;
  onLayout?: (b: ModelLayout) => void;
}) {
  const { scene } = useGLTF(url);
  const cloned = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    // scale-to-fit: normalize any model into the ~5-unit view volume
    const box = new Box3().setFromObject(cloned);
    const size = new Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    cloned.scale.setScalar(5 / maxDim);
    const box2 = new Box3().setFromObject(cloned);
    const center = new Vector3();
    box2.getCenter(center);
    cloned.position.sub(center);
    // measure the FINAL layout (bottom for the contact shadow, bounding
    // sphere for the camera framing)
    const box3 = new Box3().setFromObject(cloned);
    const sphere = box3.getBoundingSphere(new Sphere());
    onLayout?.({
      bottom: box3.min.y,
      center: [sphere.center.x, sphere.center.y, sphere.center.z],
      radius: sphere.radius || 2.5,
    });
  }, [cloned, onLayout]);

  return <primitive object={cloned} />;
}

// model-aware camera rig: once the layout is measured, frame the
// bounding sphere with a gentle three-quarter studio angle — the
// artifact fills the hero frame instead of floating small inside it,
// and the orbit target sits at the model's own center.
function CameraRig({ layout }: { layout: ModelLayout | null }) {
  const camera = useThree((s) => s.camera);
  const controls = useThree(
    (s) => s.controls
  ) as OrbitControlsImpl | null;
  useEffect(() => {
    if (!layout || !controls) return;
    const [cx, cy, cz] = layout.center;
    controls.target.set(cx, cy, cz);
    // fit the bounding sphere in the vertical fov with a small margin
    const fovRad = ((camera as { fov?: number }).fov ?? 35) * (Math.PI / 180);
    const dist = (layout.radius * 1.06) / Math.sin(fovRad / 2);
    // gentle three-quarter studio angle, slightly above center
    const dir = new Vector3(0.62, 0.36, 1).normalize();
    camera.position.set(
      cx + dir.x * dist,
      cy + dir.y * dist,
      cz + dir.z * dist
    );
    controls.update();
  }, [layout, camera, controls]);
  return null;
}

// Component highlighting — the named node stays full-opacity and every
// other mesh dims. Pure presentation: nothing about the geometry
// changes (the authority stays the GLB).
function ComponentHighlight({
  url,
  highlight,
}: {
  url: string;
  highlight: string | null;
}) {
  const { scene } = useGLTF(url);
  useEffect(() => {
    scene.traverse((obj) => {
      const mesh = obj as unknown as {
        material?: unknown;
        name?: string;
      };
      if (!mesh || !mesh.material) return;
      const mats = Array.isArray(mesh.material)
        ? (mesh.material as unknown[])
        : [mesh.material];
      const name = (mesh.name ?? "").toLowerCase();
      const hit =
        highlight != null &&
        (name.includes(highlight.toLowerCase()) ||
         highlight.toLowerCase().includes(name));
      mats.forEach((m) => {
        const mat = m as {
          opacity?: number;
          transparent?: boolean;
          emissiveIntensity?: number;
        };
        if (!mat) return;
        if (highlight == null) {
          mat.opacity = 1;
          mat.transparent = false;
          mat.emissiveIntensity = 0;
        } else if (hit) {
          mat.opacity = 1;
          mat.transparent = false;
          mat.emissiveIntensity = 0.35;
        } else {
          mat.opacity = 0.12;
          mat.transparent = true;
          mat.emissiveIntensity = 0;
        }
      });
    });
  }, [scene, highlight]);
  return null;
}

function WireToggle({
  url,
  wire,
  clip,
}: {
  url: string;
  wire: boolean;
  clip: boolean;
}) {
  const { scene } = useGLTF(url);
  useEffect(() => {
    scene.traverse((obj) => {
      const mesh = obj as unknown as Record<string, unknown>;
      if (mesh && "material" in mesh && mesh.material) {
        const mats = Array.isArray(mesh.material)
          ? (mesh.material as unknown[])
          : [mesh.material];
        mats.forEach((m) => {
          const mat = m as {
            wireframe?: boolean;
            clippingPlanes?: Plane[];
            clipShadows?: boolean;
          };
          if (!mat) return;
          if ("wireframe" in mat) mat.wireframe = wire;
          // Render clip-plane on the model materials (renderer has
          // localClippingEnabled: true on the Canvas).
          mat.clippingPlanes = clip ? [CLIP_PLANE] : [];
          mat.clipShadows = clip;
        });
      }
    });
  }, [scene, wire, clip]);
  return null;
}

export default function ModelViewer({
  url,
  label,
  reconstructed = false,
  note,
  height = 460,
  compact = false,
  highlight = null,
  variant = "inline",
  modelKind,
  genLabel,
}: {
  url: string;
  label: string;
  reconstructed?: boolean;
  note?: string;
  height?: number | string;
  compact?: boolean;
  highlight?: string | null;
  variant?: "hero" | "inline";
  /** what kind of model this is — drives the product-language badge */
  modelKind?: "engineering" | "conceptual" | "reconstruction";
  /** e.g. "generation 2" — the generation identity, when known */
  genLabel?: string;
}) {
  const [wire, setWire] = useState(false);
  const [clip, setClip] = useState(false);
  // gentle presentation rotation until the user takes control
  const [auto, setAuto] = useState(variant === "hero");
  // the measured model layout (hero: drives framing + ground shadow)
  const [layout, setLayout] = useState<ModelLayout | null>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const controls = useRef<OrbitControlsImpl | null>(null);

  function resetView() {
    controls.current?.reset();
  }

  function toggleFullscreen() {
    const el = wrap.current;
    if (!el) return;
    if (document.fullscreenElement === el) {
      void document.exitFullscreen();
    } else {
      void el.requestFullscreen?.();
    }
  }

  // the product-language badge: what kind of model is on stage. The
  // full epistemic wording rides the title tooltip (deep layer), never
  // the primary surface.
  const kind =
    modelKind ??
    (reconstructed ? "reconstruction" : label.toLowerCase().includes("conceptual") ? "conceptual" : "engineering");
  const badge =
    kind === "reconstruction"
      ? "Spatial reconstruction"
      : kind === "conceptual"
        ? "Conceptual design"
        : "Engineering model";
  const badgeTitle =
    kind === "reconstruction"
      ? "provider reconstruction — a spatial hypothesis, not a measurement"
      : kind === "conceptual"
        ? "conceptual architecture visualization — engineering dimensions are not claimed"
        : "deterministic CAD build from the canonical engineering geometry — a computational result, not a physical validation";

  const hero = variant === "hero";

  return (
    <div
      className={`viewer${hero ? " hero" : ""}`}
      ref={wrap}
      /* the DOM acceptance test counts primary technology model viewers
         with this attribute — exactly ONE per technology page. Two
         viewers that happen to display the same GLB are still a
         violation; the count is a machine-checked product invariant. */
      data-model-viewer={label}
      style={compact && !hero ? { maxWidth: 480 } : undefined}
    >
      <div
        className="canvas-wrap"
        style={{ height: hero ? "100%" : height }}
      >
        <Canvas
          camera={hero ? { position: [9, 6, 12], fov: 30 } : { position: [6, 4.5, 8], fov: 40 }}
          gl={{ localClippingEnabled: true, antialias: true }}
          dpr={[1, 2]}
        >
          {/* calm three-point studio lighting (warm key, cool fill,
              warm rim + low bounce) — enough contrast to read as a
              photographed object, not a flat primitive */}
          <ambientLight intensity={hero ? 0.55 : 0.6} />
          <directionalLight position={[7, 10, 6]} intensity={hero ? 1.6 : 1.15} />
          <directionalLight position={[-8, 2, -6]} intensity={0.5} color="#dfe6ee" />
          {hero && <directionalLight position={[-5, 6, -7]} intensity={0.7} color="#f5e8d8" />}
          {hero && <directionalLight position={[0, -6, 2]} intensity={0.25} color="#f0e9df" />}
          <Suspense fallback={null}>
            <FittedModel url={url} onLayout={hero ? setLayout : undefined} />
            <WireToggle url={url} wire={wire} clip={clip} />
            <ComponentHighlight url={url} highlight={highlight} />
          </Suspense>
          {/* the model-aware framing + the ground-contact shadow — both
              measured from the model's OWN bounding box, so any
              proportions read as grounded and commanding */}
          {hero && <CameraRig layout={layout} />}
          {hero && layout && (
            <ContactShadows
              position={[layout.center[0], layout.bottom - 0.02, layout.center[2]]}
              opacity={0.5}
              scale={Math.max(layout.radius * 3.2, 8)}
              blur={2.1}
              far={layout.radius * 2}
              resolution={1024}
              color="#3a332b"
            />
          )}
          <OrbitControls
            makeDefault
            ref={controls}
            enablePan
            enableZoom
            minDistance={2.4}
            maxDistance={26}
            autoRotate={auto}
            autoRotateSpeed={0.85}
            onStart={() => setAuto(false)}
          />
        </Canvas>
        <div className={`canvas-hud${hero ? " hero-hud" : ""}`}>
          {auto && hero && (
            <span className="hud-live" title="drag to take control">
              exploring
            </span>
          )}
          <button type="button" onClick={resetView} title="reset view">
            reset
          </button>
          <button type="button" onClick={toggleFullscreen} title="fullscreen">
            fullscreen
          </button>
        </div>
      </div>
      <div className="tag" title={badgeTitle}>
        {reconstructed ? (
          <>
            <span className="recon">reconstruction</span> · spatial hypothesis,
            not a measurement
          </>
        ) : (
          <>
            {badge}
            {genLabel ? ` · ${genLabel}` : ""}
          </>
        )}
        {!hero && label ? (
          <>
            {" · "}
            {label}
          </>
        ) : null}
      </div>
      <div className="controls">
        <button onClick={() => setWire(!wire)} type="button">
          {wire ? "shaded" : "wireframe"}
        </button>
        <button onClick={() => setClip(!clip)} type="button">
          {clip ? "solid view" : "clip view"}
        </button>
        {clip && (
          <span className="cliplabel" style={{ fontSize: 11.5 }}>
            render clipping — a viewing slice, not a section drawing
          </span>
        )}
      </div>
      {note && <div className="footnote">{note}</div>}
    </div>
  );
}
