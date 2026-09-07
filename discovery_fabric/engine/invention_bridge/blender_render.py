"""blender_render.py — the pinned Blender-side render script (R419).

Invoked ONLY headless:

    blender --background --python blender_render.py -- <spec.json>

The script receives a JSON spec:

    {
      "source_glb":    absolute path to the authoritative GLB
                       (CadQuery/OCCT geometry — the engineering authority),
      "output_dir":    where hero/section/exploded artifacts are written,
      "is_conceptual": bool — class label recorded in the render record,
      "renders":       ["hero", "section", "exploded"] subset,
      "export_glbs":   bool — also write materialized GLBs,
      "resolution":    [width, height],
      "samples":       Cycles samples (CPU)
    }

and produces, inside output_dir:

    hero.png / section.png / exploded.png     studio renders
    hero.glb / section.glb / exploded.glb     materialized presentation GLBs
    render_record.json                        hashes + provenance

AUTHORITY CONTRACT (operator directive R419, sections 5-6):
  * CadQuery/OCCT remains the engineering geometry authority. This script
    IMPORTS the authoritative GLB and may only:
      - assign materials (studio Principled BSDF over the mesh's own
        COLOR_0 vertex palette),
      - set lighting and cameras,
      - create presentation-only states (section cut, exploded offsets).
  * hero.glb preserves the imported geometry (vertex/face counts recorded
    and compared — any topology change is a typed failure, not a silent
    edit). section.glb/exploded.glb are DISCLOSED presentation variants
    (cut / translation), recorded as such in render_record.json — never
    presented as engineering geometry.
  * Deterministic: no randomness, fixed samples/resolution/lights; the
    render record carries the Blender version + build hash so renders are
    reproducible per pinned build.
  * No interactive use: this file is a server tool, never an operator
    workflow.
"""

import hashlib
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

START = time.time()

# Studio constants — neutral, calm, no debug grid, no gimmicks.
WORLD_COLOR = (0.043, 0.048, 0.054)  # near-black cool neutral
WORLD_STRENGTH = 1.0
KEY_ENERGY = 900.0
KEY_SIZE = 6.0
FILL_ENERGY = 260.0
FILL_SIZE = 9.0
RIM_ENERGY = 160.0
LENS_MM = 50.0
SENSOR_W = 36.0
CAM_AZIMUTH_DEG = 38.0
CAM_ELEVATION_DEG = 21.0
FIT_MARGIN = 1.18
ROUGHNESS = 0.62
METALLIC = 0.0


def _log(msg: str) -> None:
    print(f"[blender_render] {msg}", file=sys.stderr, flush=True)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _import_glb(path: str) -> list:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    imported = [o for o in bpy.data.objects if o not in before]
    return imported


def _mesh_objects() -> list:
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def _assign_studio_materials(meshes: list) -> None:
    """One clean Principled BSDF per mesh, driven by the mesh's own
    COLOR_0 vertex palette (the bridge's component colors)."""
    for obj in meshes:
        mesh = obj.data
        mat = bpy.data.materials.new(name=f"studio::{obj.name[:58]}")
        mat.use_nodes = True
        tree = mat.node_tree
        for node in list(tree.nodes):
            tree.nodes.remove(node)
        out = tree.nodes.new("ShaderNodeOutputMaterial")
        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        bsdf.inputs["Roughness"].default_value = ROUGHNESS
        bsdf.inputs["Metallic"].default_value = METALLIC
        color_layer = None
        if mesh.color_attributes and len(mesh.color_attributes) > 0:
            color_layer = mesh.color_attributes[0].name
        if color_layer:
            attr = tree.nodes.new("ShaderNodeAttribute")
            attr.attribute_name = color_layer
            tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            bsdf.inputs["Base Color"].default_value = (0.62, 0.44, 0.33, 1.0)
        if len(obj.data.materials) > 0:
            for i in range(len(obj.data.materials)):
                obj.data.materials[i] = mat
        else:
            obj.data.materials.append(mat)


def _world_bbox(meshes: list):
    """(center, size, radius) of the evaluated world-space assembly."""
    lo = Vector((1e30, 1e30, 1e30))
    hi = Vector((-1e30, -1e30, -1e30))
    for obj in meshes:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for a in range(3):
                lo[a] = min(lo[a], world[a])
                hi[a] = max(hi[a], world[a])
    center = (lo + hi) * 0.5
    size = hi - lo
    radius = 0.5 * size.length
    return center, size, max(radius, 1e-6)


def _add_floor(center, size) -> object:
    bpy.ops.mesh.primitive_plane_add(size=1, location=(center.x, center.y, 0.0))
    floor = bpy.context.active_object
    floor.name = "__floor"
    floor.scale = (max(size.x, size.y) * 3.5, max(size.x, size.y) * 3.5, 1.0)
    floor.is_shadow_catcher = True
    mat = bpy.data.materials.new(name="__floor_mat")
    mat.use_nodes = True
    floor.data.materials.append(mat)
    return floor


def _add_lights(center, radius: float) -> list:
    lights = []
    key = bpy.data.lights.new(name="__key", type="AREA")
    key.energy = KEY_ENERGY
    key.size = KEY_SIZE
    k = bpy.data.objects.new("__key_obj", key)
    bpy.context.collection.objects.link(k)
    k.location = (center.x + radius * 1.6, center.y - radius * 1.9, radius * 2.6)
    k.rotation_euler = (math.radians(52), 0, math.radians(34))
    lights.append(k)

    fill = bpy.data.lights.new(name="__fill", type="AREA")
    fill.energy = FILL_ENERGY
    fill.size = FILL_SIZE
    f = bpy.data.objects.new("__fill_obj", fill)
    bpy.context.collection.objects.link(f)
    f.location = (center.x - radius * 2.2, center.y - radius * 0.8, radius * 1.4)
    f.rotation_euler = (math.radians(66), 0, math.radians(-48))
    lights.append(f)

    rim = bpy.data.lights.new(name="__rim", type="AREA")
    rim.energy = RIM_ENERGY
    rim.size = FILL_SIZE
    r = bpy.data.objects.new("__rim_obj", rim)
    bpy.context.collection.objects.link(r)
    r.location = (center.x - radius * 0.4, center.y + radius * 2.2, radius * 1.9)
    r.rotation_euler = (math.radians(60), 0, math.radians(196))
    lights.append(r)
    return lights


def _add_camera(center, radius: float) -> object:
    cam_data = bpy.data.cameras.new(name="__cam")
    cam_data.lens = LENS_MM
    cam_data.sensor_width = SENSOR_W
    cam = bpy.data.objects.new(name="__cam", object_data=cam_data)
    bpy.context.collection.objects.link(cam)

    fov_v = 2.0 * math.atan(SENSOR_W * 0.5 / LENS_MM)  # sensor fit AUTO/HORIZONTAL
    dist = (radius / max(math.sin(fov_v / 2.0), 1e-6)) * FIT_MARGIN
    az = math.radians(CAM_AZIMUTH_DEG)
    el = math.radians(CAM_ELEVATION_DEG)
    direction = Vector((
        math.cos(el) * math.sin(az),
        -math.cos(el) * math.cos(az),
        math.sin(el)))
    cam.location = center + direction * dist

    target = bpy.data.objects.new(name="__cam_target", object_data=None)
    bpy.context.collection.objects.link(target)
    target.location = center
    con = cam.constraints.new(type="TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    bpy.context.scene.camera = cam
    return cam


def _set_cam_distance(cam, center, radius: float) -> None:
    fov_v = 2.0 * math.atan(SENSOR_W * 0.5 / LENS_MM)
    dist = (radius / max(math.sin(fov_v / 2.0), 1e-6)) * FIT_MARGIN
    az = math.radians(CAM_AZIMUTH_DEG)
    el = math.radians(CAM_ELEVATION_DEG)
    direction = Vector((
        math.cos(el) * math.sin(az),
        -math.cos(el) * math.cos(az),
        math.sin(el)))
    cam.location = center + direction * dist


def _configure_render(scene, width: int, height: int, samples: int) -> None:
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    try:
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.02
    except Exception:  # noqa: BLE001 — older builds
        pass
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"

    world = bpy.data.worlds.new(name="__world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*WORLD_COLOR, 1.0)
    bg.inputs[1].default_value = WORLD_STRENGTH


def _count_topology(meshes: list):
    verts = sum(len(o.data.vertices) for o in meshes)
    faces = sum(len(o.data.polygons) for o in meshes)
    return {"vertex_count": int(verts), "face_count": int(faces),
            "object_count": len(meshes)}


# --- presentation states ----------------------------------------------------


def _enter_section_state(meshes, center, size):
    """Boolean cut through the assembly (visualization-only, disclosed).

    The cut removes the CAMERA-NEAR half along the dominant horizontal
    camera axis, using an axis-aligned cardinal plane through the
    assembly center. (An axis-aligned cutter box on a cardinal plane is
    exact: a diagonally-offset cube would swallow the whole model — the
    R419 measured defect that blanked the first section renders.)
    """
    az = math.radians(CAM_AZIMUTH_DEG)
    cam_dir_h = (math.sin(az), -math.cos(az))
    axis = 1 if abs(cam_dir_h[1]) > abs(cam_dir_h[0]) else 0
    big = max(size.x, size.y, size.z) * 4.0 + 20.0
    # non-cut axes: full assembly span plus margin
    lo = center - size * 0.75
    hi = center + size * 0.75
    # cut axis: cover EXACTLY the camera-near half-space — the far face
    # of the cutter stops AT the plane through center (extending past it
    # would remove the far half too — the measured blank-section defect)
    comp = cam_dir_h[1] if axis == 1 else cam_dir_h[0]
    if comp > 0:
        lo[axis] = center[axis]
        hi[axis] = center[axis] + big
    else:
        hi[axis] = center[axis]
        lo[axis] = center[axis] - big
    dims = hi - lo
    loc = (lo + hi) * 0.5
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    cutter = bpy.context.active_object
    cutter.name = "__section_cutter"
    cutter.scale = (max(dims.x, 1.0), max(dims.y, 1.0), max(dims.z, 1.0))
    cutter.display_type = "BOUNDS"
    cutters = [cutter]
    for obj in meshes:
        mod = obj.modifiers.new(name="section_cut", type="BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cutter
    return cutters, None


def _apply_section_cut(meshes) -> None:
    for obj in meshes:
        if "section_cut" not in {m.name for m in obj.modifiers}:
            continue
        try:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.modifier_apply(modifier="section_cut")
        finally:
            obj.select_set(False)


def _enter_exploded_state(meshes, center, factor: float = 0.9):
    """Translate each component away from the assembly centroid.

    Substrate/large base objects move least; small components fan outward.
    Presentation-only: per-component geometry is untouched; translations
    are recorded in the render record.
    """
    moves = []
    objs = sorted(
        meshes,
        key=lambda o: -sum(abs(v) for v in (o.matrix_world.translation - center)))
    world_lo, world_hi = None, None
    for obj in meshes:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            if world_lo is None:
                world_lo, world_hi = world.copy(), world.copy()
            else:
                for a in range(3):
                    world_lo[a] = min(world_lo[a], world[a])
                    world_hi[a] = max(world_hi[a], world[a])
    diag = (world_hi - world_lo).length
    for rank, obj in enumerate(objs):
        origin = obj.matrix_world.translation
        away = origin - center
        away.z = abs(away.z) * 0.35 + diag * 0.06
        if away.length < 1e-6:
            away = Vector((0.0, 0.0, diag * 0.25))
        away = away.normalized()
        distance = diag * factor * (0.22 + 0.16 * (rank / max(1, len(objs) - 1)))
        delta = away * distance
        obj.location = obj.location + delta
        moves.append({"object": obj.name, "delta": [round(v, 4) for v in delta]})
    return moves


def _export_glb(path: str, meshes) -> bool:
    """Export the given mesh objects (and nothing else) as a GLB."""
    non_mesh = [o for o in bpy.context.scene.objects if o not in meshes]
    hidden = []
    for o in non_mesh:
        was = o.hide_viewport
        o.hide_viewport = True
        o.hide_render = True
        hidden.append((o, was))
    try:
        bpy.ops.export_scene.gltf(
            filepath=path,
            export_format="GLB",
            export_apply=True,
            export_vertex_color="MATERIAL",
            export_yup=True,
            use_selection=False,
            use_visible=False,
            export_extras=False,
        )
        return os.path.exists(path) and os.path.getsize(path) > 0
    finally:
        for o, was in hidden:
            o.hide_viewport = was
            o.hide_render = False


def _restore_explosion(meshes, moves) -> None:
    by_name = {m["object"]: m["delta"] for m in moves}
    for obj in meshes:
        delta = by_name.get(obj.name)
        if delta:
            obj.location = obj.location - Vector(delta)


def _render_png(scene, path: str) -> None:
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        _log("FAIL: no spec path given")
        return 2
    spec = json.loads(open(argv[0]).read())
    out_dir = spec["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    renders = set(spec.get("renders") or ["hero", "section", "exploded"])
    width, height = spec.get("resolution") or [1152, 768]
    samples = int(spec.get("samples") or 48)

    record = {
        "render_pipeline": "BLENDER_HEADLESS",
        "blender_version": bpy.app.version_string,
        "blender_build_hash": bpy.app.build_hash.decode(errors="replace")
        if isinstance(bpy.app.build_hash, (bytes, bytearray)) else str(bpy.app.build_hash),
        "engine": "CYCLES_CPU",
        "samples": samples,
        "resolution": [width, height],
        "source_glb_sha256": _sha256_file(spec["source_glb"]),
        "is_conceptual": bool(spec.get("is_conceptual")),
        "renders": {},
        "exports": {},
        "status": "OK",
    }

    _clear_scene()
    _import_glb(spec["source_glb"])
    meshes = _mesh_objects()
    if not meshes:
        record["status"] = "FAILED_NO_MESHES"
        _log("FAIL: no meshes imported")
        _write_record(record, out_dir)
        return 3
    imported_topology = _count_topology(meshes)
    record["source_topology"] = imported_topology

    _assign_studio_materials(meshes)
    _log("meshes after import: " + ", ".join(
        f"{o.name[:24]}({len(o.data.vertices)}v)" for o in meshes[:4]) + f" ...{len(meshes)} total")
    center, size, radius = _world_bbox(meshes)
    _add_floor(center, size)
    _add_lights(center, radius)
    cam = _add_camera(center, radius)
    scene = bpy.context.scene
    _configure_render(scene, width, height, samples)

    # --- HERO ---------------------------------------------------------------
    if "hero" in renders:
        t0 = time.time()
        hero_png = os.path.join(out_dir, "hero.png")
        _render_png(scene, hero_png)
        record["renders"]["hero.png"] = {
            "path": hero_png, "sha256": _sha256_file(hero_png),
            "seconds": round(time.time() - t0, 2)}
        _log(f"hero.png done in {time.time() - t0:.1f}s")
        if spec.get("export_glbs"):
            hero_glb = os.path.join(out_dir, "hero.glb")
            if _export_glb(hero_glb, meshes):
                record["exports"]["hero.glb"] = {
                    "path": hero_glb, "sha256": _sha256_file(hero_glb),
                    "topology": _count_topology(meshes),
                    "variant": "MATERIALIZED",
                    "geometry_preserved": (
                        _count_topology(meshes) == imported_topology)}
            else:
                record["exports"]["hero.glb"] = {"variant": "EXPORT_FAILED"}
        _log("meshes after hero export: " + ", ".join(
            f"{o.name[:24]}({len(o.data.vertices)}v)" for o in meshes[:4]))
    # --- SECTION ------------------------------------------------------------
    if "section" in renders:
        t0 = time.time()
        try:
            cutters, _ = _enter_section_state(meshes, center, size)
            _apply_section_cut(meshes)
            _log("meshes after section apply: " + ", ".join(
                f"{o.name[:24]}({len(o.data.vertices)}v)" for o in meshes[:6]))
            for c in cutters:
                c.hide_viewport = True
                c.hide_render = True
            section_png = os.path.join(out_dir, "section.png")
            _render_png(scene, section_png)
            record["renders"]["section.png"] = {
                "path": section_png, "sha256": _sha256_file(section_png),
                "seconds": round(time.time() - t0, 2),
                "variant": "PRESENTATION_CUT",
                "note": ("visualization section — a presentation cut, not "
                         "engineering geometry; the authoritative model is "
                         "unchanged (operator directive R419 §6)"),
            }
            if spec.get("export_glbs"):
                section_glb = os.path.join(out_dir, "section.glb")
                if _export_glb(section_glb, meshes):
                    record["exports"]["section.glb"] = {
                        "path": section_glb, "sha256": _sha256_file(section_glb),
                        "variant": "PRESENTATION_CUT",
                        "topology": _count_topology(meshes)}
            for c in cutters:
                bpy.data.objects.remove(c, do_unlink=True)
        except Exception as exc:  # noqa: BLE001 — typed record, never silent
            record["renders"]["section.png"] = {
                "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
            _log(f"section render failed: {exc}")

    # --- EXPLODED -----------------------------------------------------------
    if "exploded" in renders:
        t0 = time.time()
        try:
            moves = _enter_exploded_state(meshes, center)
            _, _, radius_ex = _world_bbox(meshes)
            _set_cam_distance(cam, center, radius_ex)
            exploded_png = os.path.join(out_dir, "exploded.png")
            _render_png(scene, exploded_png)
            record["renders"]["exploded.png"] = {
                "path": exploded_png, "sha256": _sha256_file(exploded_png),
                "seconds": round(time.time() - t0, 2),
                "variant": "PRESENTATION_EXPLODED",
                "component_moves": moves,
            }
            if spec.get("export_glbs"):
                exploded_glb = os.path.join(out_dir, "exploded.glb")
                if _export_glb(exploded_glb, meshes):
                    record["exports"]["exploded.glb"] = {
                        "path": exploded_glb, "sha256": _sha256_file(exploded_glb),
                        "variant": "PRESENTATION_EXPLODED",
                        "topology": _count_topology(meshes)}
            _restore_explosion(meshes, moves)
            _set_cam_distance(cam, center, radius)
        except Exception as exc:  # noqa: BLE001 — typed record, never silent
            record["renders"]["exploded.png"] = {
                "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
            _log(f"exploded render failed: {exc}")

    record["total_seconds"] = round(time.time() - START, 2)
    _write_record(record, out_dir)
    _log(f"done in {record['total_seconds']}s -> {out_dir}")
    return 0


def _write_record(record: dict, out_dir: str) -> None:
    path = os.path.join(out_dir, "render_record.json")
    with open(path, "w") as f:
        json.dump(record, f, indent=2)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 — Blender swallows script
        # exceptions and exits 0; force a TYPED crash record + nonzero
        # exit so the engine-side orchestrator cannot mistake a crash
        # for success.
        try:
            spec_path = [a for a in sys.argv[sys.argv.index("--") + 1:]]
            out_dir = json.loads(open(spec_path[0]).read())["output_dir"]
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "render_record.json"), "w") as f:
                json.dump({
                    "render_pipeline": "BLENDER_HEADLESS",
                    "status": "CRASHED",
                    "error": f"{type(exc).__name__}: {exc}",
                }, f, indent=2)
        except Exception:  # noqa: BLE001 — last resort
            pass
        _log(f"CRASHED: {type(exc).__name__}: {exc}")
        sys.exit(4)
