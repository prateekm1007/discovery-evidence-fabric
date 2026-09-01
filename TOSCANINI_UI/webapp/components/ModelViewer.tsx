"use client";

// Interactive 3D viewer (R389 Phase 5): rotate / zoom / pan, wireframe
// toggle, and the honesty badges — engineering geometry is
// COMPUTATIONAL_RESULT; provider reconstructions are RECONSTRUCTED and
// visibly labeled (never physical truth — Art. XXXVIII).

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Center, OrbitControls, useGLTF } from "@react-three/drei";
import { Box3, Vector3 } from "three";

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

function WireToggle({ url, wire }: { url: string; wire: boolean }) {
  const { scene } = useGLTF(url);
  useEffect(() => {
    scene.traverse((obj) => {
      const mesh = obj as unknown as Record<string, unknown>;
      if (mesh && "material" in mesh && mesh.material) {
        const mats = Array.isArray(mesh.material)
          ? (mesh.material as unknown[])
          : [mesh.material];
        mats.forEach((m) => {
          const mat = m as { wireframe?: boolean };
          if (mat && "wireframe" in mat) mat.wireframe = wire;
        });
      }
    });
  }, [scene, wire]);
  return null;
}

export default function ModelViewer({
  url,
  label,
  reconstructed = false,
  note,
  height = 460,
}: {
  url: string;
  label: string;
  reconstructed?: boolean;
  note?: string;
  height?: number;
}) {
  const [wire, setWire] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  return (
    <div className="viewer" ref={wrap}>
      <div className="canvas-wrap" style={{ height }}>
        <Canvas camera={{ position: [6, 4.5, 8], fov: 40 }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[6, 9, 7]} intensity={1.15} />
          <directionalLight position={[-7, -4, -5]} intensity={0.4} />
          <Suspense fallback={null}>
            <Center>
              <FittedModel url={url} />
            </Center>
            <WireToggle url={url} wire={wire} />
          </Suspense>
          <OrbitControls
            makeDefault
            enablePan
            enableZoom
            minDistance={2}
            maxDistance={40}
          />
          <gridHelper args={[24, 24, "#3a3835", "#26241f"]} />
        </Canvas>
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
      </div>
      {note && <div className="footnote">{note}</div>}
    </div>
  );
}
