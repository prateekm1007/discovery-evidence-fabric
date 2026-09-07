"use client";

// Interactive 3D viewer — R389 Phase 5 baseline, R395 first-class upgrade.
// Controls: rotate / zoom / pan / RESET / wireframe / render clip-plane /
// fullscreen. Honesty badges are structural: engineering geometry is
// COMPUTATIONAL_RESULT; provider reconstructions are RECONSTRUCTED and
// visibly labeled (never physical truth — Art. XXXVIII).

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Center, OrbitControls, useGLTF } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { Box3, Plane, Vector3 } from "three";

// The render clip-plane: normal -Z, constant 0 → hides z > 0 half of the
// model in the VIEW. A viewing aid only — honestly labeled, never a
// section drawing.
const CLIP_PLANE = new Plane(new Vector3(0, 0, -1), 0);

function FittedModel({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  const cloned = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    // scale-to-fit: normalize any model into the ~4-unit view volume
    const box = new Box3().setFromObject(cloned);
    const size = new Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const scale = 4 / maxDim;
    cloned.scale.setScalar(scale);
    const box2 = new Box3().setFromObject(cloned);
    const center = new Vector3();
    box2.getCenter(center);
    cloned.position.sub(center);
  }, [cloned]);

  return <primitive object={cloned} />;
}

// R419 section 12: component highlighting — when the user picks a
// component (from the artifact pane or the essay), the named node
// stays full-opacity and every other mesh dims. Pure presentation:
// nothing about the geometry changes (the authority stays the GLB).
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
}: {
  url: string;
  label: string;
  reconstructed?: boolean;
  note?: string;
  height?: number;
  compact?: boolean;
  highlight?: string | null;
}) {
  const [wire, setWire] = useState(false);
  const [clip, setClip] = useState(false);
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

  return (
    <div
      className="viewer"
      ref={wrap}
      style={compact ? { maxWidth: 480 } : undefined}
    >
      <div className="canvas-wrap" style={{ height }}>
        <Canvas
          camera={{ position: [6, 4.5, 8], fov: 40 }}
          gl={{ localClippingEnabled: true }}
        >
          <ambientLight intensity={0.6} />
          <directionalLight position={[6, 9, 7]} intensity={1.15} />
          <directionalLight position={[-7, -4, -5]} intensity={0.4} />
          <Suspense fallback={null}>
            <Center>
              <FittedModel url={url} />
            </Center>
            <WireToggle url={url} wire={wire} clip={clip} />
            <ComponentHighlight url={url} highlight={highlight} />
          </Suspense>
          <OrbitControls
            makeDefault
            ref={controls}
            enablePan
            enableZoom
            minDistance={2}
            maxDistance={40}
          />
        </Canvas>
        <div className="canvas-hud">
          <button type="button" onClick={resetView} title="reset view">
            reset
          </button>
          <button type="button" onClick={toggleFullscreen} title="fullscreen">
            fullscreen
          </button>
        </div>
      </div>
      <div className="tag">
        {reconstructed ? (
          <>
            <span className="recon">RECONSTRUCTED</span> · spatial hypothesis,
            not a measurement
          </>
        ) : (
          <>COMPUTATIONAL_RESULT · deterministic CAD</>
        )}
        {" · "}
        {label}
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
