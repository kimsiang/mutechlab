"""Principle act of the 90 s cut (58 s, local time 0–58): clean dark explainer scenes.

  0–12   S1 cosmic-ray shower over the city skyline, muons reach the ground
 12–26   S2 three rock columns: thin / thick / thick-with-cavity, muons through each, detector below
 26–40   S3 telescope under a hill with a hidden cavity; muons arrive from many directions
 40–54   S4 three telescopes around the hill; rays cross; voxels inside light up where density is low
 54–58   S5 pull back (title card in post)

python3 scene2.py --step 5 --res 1280 720 --samples 12 --out render_p
"""
import sys, os, math, random, argparse
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as S
from scene import mat, noisy, box, cyl, sphere, key, linear_keys, smooth_keys, boolean, f
from timeline90 import FPS, P_SHOWER, P_ATTEN, P_TELE, P_TOMO, P_OUTRO, P_END

random.seed(11)
D = bpy.data
NAVY = (0.004, 0.047, 0.098, 1); CYAN = (0.0, 0.66, 0.96, 1); EBLUE = (0.13, 0.32, 1.0, 1)
ORANGE = (1.0, 0.45, 0.08, 1); GOLD = (1.0, 0.8, 0.3, 1)

def rod(name, a, b, r, m, t0, t1, fade=2, life=None):
    """Emissive rod from a to b that 'grows' from a at frame t0 and fades at t1 (frames)."""
    a, b = Vector(a), Vector(b); d = b - a; L = d.length
    o = cyl(name, r, L, (a + b) / 2, m, rot=d.to_track_quat('Z', 'Y').to_euler(), verts=6)
    key(o, 1, scale=(0, 0, 0)); key(o, t0, scale=(0, 0, 0)); key(o, t0 + fade, scale=(1, 1, 1))
    key(o, t1, scale=(1, 1, 1)); key(o, t1 + fade, scale=(0, 0, 0)); linear_keys(o)
    return o

def shot_offsets():
    """Each shot lives in its own region of the world so one camera cut per shot suffices."""
    return {"S1": (0, 0, 0), "S2": (300, 0, 0), "S3": (600, 0, 0), "S4": (900, 0, 0)}

def build():
    S.clear(); sc = bpy.context.scene
    sc.frame_start = 1; sc.frame_end = f(P_END); sc.render.fps = FPS
    w = D.worlds.new("W"); sc.world = w; w.use_nodes = True
    bgn = w.node_tree.nodes["Background"]; bgn.inputs["Color"].default_value = (0.002, 0.02, 0.045, 1); bgn.inputs["Strength"].default_value = 1.0

    m_muon = mat("muon", CYAN, 0.3, emit=CYAN, emit_str=18)
    m_muon_dim = mat("muon_dim", CYAN, 0.3, emit=CYAN, emit_str=5)
    m_pion = mat("pion", ORANGE, 0.3, emit=ORANGE, emit_str=14)
    m_proton = mat("proton", GOLD, 0.3, emit=GOLD, emit_str=30)
    m_ground = noisy(mat("ground2", (0.05, 0.07, 0.10, 1), 0.9), scale=0.2, detail=6, bump=0.2)
    m_sil = mat("sil", (0.02, 0.035, 0.06, 1), 0.8)
    m_rock = noisy(mat("rock2", (0.30, 0.26, 0.22, 1), 0.9), scale=0.6, detail=10, bump=0.8, dark=0.5, light=1.3)
    m_rock_t = noisy(mat("rock_t", (0.30, 0.26, 0.22, 1), 0.9, alpha=0.4), scale=0.6, detail=10, bump=0.8, dark=0.5, light=1.3)
    m_void = mat("void2", CYAN, 0.3, emit=CYAN, emit_str=3, alpha=0.5)
    m_scint = mat("scint2", (0.1, 0.35, 0.9, 1), 0.2, emit=(0.2, 0.5, 1.0, 1), emit_str=1.5)
    m_alu = mat("alu2", (0.75, 0.77, 0.8, 1), 0.4, 0.9)
    m_grid = mat("grid", (0.2, 0.4, 0.6, 1), 0.5, alpha=0.18)
    m_vox = mat("vox", CYAN, 0.3, emit=CYAN, emit_str=0.0, alpha=0.9)
    m_ray = mat("ray", EBLUE, 0.3, emit=(0.3, 0.5, 1.0, 1), emit_str=3)

    # key light for the physical props; emissives light themselves
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 100)); sun = bpy.context.object
    sun.data.energy = 2.0; sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(30))
    off = shot_offsets()

    # ------------------------------------------------------------------ S1 shower (0–12)
    ox, oy, oz = off["S1"]
    box("g1", (400, 400, 1), (ox, oy + 100, oz - 0.5), m_ground)
    for k in range(40):
        x = random.uniform(-120, 120); h = random.uniform(6, 40); wd = random.uniform(5, 12)
        box(f"sil{k}", (wd, wd, h), (ox + x, oy + random.uniform(90, 160), oz + h / 2), m_sil)
    HIT = Vector((ox, oy + 90, oz + 60))
    t_hit = f(P_SHOWER + 2.0)
    pr = sphere("proton", 0.9, (ox - 40, oy + 90, oz + 150), m_proton)
    key(pr, 1, loc=(ox - 40, oy + 90, oz + 150)); key(pr, f(P_SHOWER + 0.3), loc=(ox - 40, oy + 90, oz + 150))
    key(pr, t_hit, loc=HIT); key(pr, t_hit, scale=(1, 1, 1)); key(pr, t_hit + 3, scale=(0, 0, 0)); linear_keys(pr)
    rod("ptrail", (ox - 40, oy + 90, oz + 150), HIT, 0.25, m_proton, f(P_SHOWER + 0.3), t_hit + 6, fade=int(1.7 * FPS))
    # shower: pions (short orange) then muons (long cyan, to the ground)
    for k in range(26):
        th = random.uniform(0, math.radians(28)); ph = random.uniform(0, 2 * math.pi)
        d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), -math.cos(th)))
        L = random.uniform(6, 14)
        rod(f"pi{k}", HIT, HIT + d * L, 0.18, m_pion, t_hit + random.randint(0, 6), t_hit + 14 + random.randint(0, 8), fade=4)
    for k in range(60):
        th = random.uniform(0, math.radians(30)); ph = random.uniform(0, 2 * math.pi)
        d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), -math.cos(th)))
        start = HIT + d * random.uniform(4, 12)
        L = (start.z - oz) / max(0.3, -d.z)
        t0 = t_hit + 6 + random.randint(0, int(5.0 * FPS))
        rod(f"mu{k}", start, start + d * L, 0.14, m_muon, t0, t0 + random.randint(30, 80), fade=6)
    # steady rain in the last seconds: thin cyan rods across the skyline
    for k in range(90):
        x = random.uniform(-110, 110); y = random.uniform(40, 170); th = random.uniform(0, math.radians(25)); ph = random.uniform(0, 2 * math.pi)
        d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), -math.cos(th)))
        top = Vector((ox + x, oy + y, oz + 70)); L = 70 / -d.z
        t0 = f(P_SHOWER + 6.5) + random.randint(0, int(5 * FPS))
        rod(f"rain{k}", top, top + d * L, 0.08, m_muon_dim, t0, t0 + random.randint(12, 30), fade=3)

    # ------------------------------------------------------------------ S2 attenuation (12–26)
    ox, oy, oz = off["S2"]
    box("g2", (200, 200, 1), (ox, oy + 20, oz - 3.5), m_ground)
    cols = [(-14, 5.0, False, 0.80), (0, 12.0, False, 0.35), (14, 12.0, True, 0.55)]
    for i, (x, h, has_void, trans) in enumerate(cols):
        blk = box(f"blk{i}", (8, 8, h), (ox + x, oy, oz + h / 2), m_rock_t)
        if has_void:
            v = sphere(f"void{i}", 2.6, (ox + x, oy, oz + h * 0.55), m_void)
            vm = v.modifiers.new("wire", 'WIREFRAME'); vm.thickness = 0.06; vm.use_replace = False
        box(f"det{i}", (8.6, 8.6, 0.25), (ox + x, oy, oz - 1.6), m_alu)
        box(f"sci{i}", (8.0, 8.0, 0.3), (ox + x, oy, oz - 1.3), m_scint)
        # muons: appear 1.5–11 s of the shot, one every ~0.45 s per column
        n = 22
        for k in range(n):
            t0 = f(P_ATTEN + 1.5 + k * 0.42 + random.uniform(0, 0.2))
            px = ox + x + random.uniform(-3.2, 3.2); py = oy + random.uniform(-3.2, 3.2)
            top = Vector((px, py, oz + 24));
            survive = random.random() < trans
            if survive:
                rod(f"m{i}_{k}", top, (px, py, oz - 2.2), 0.12, m_muon, t0, t0 + 30, fade=3)
            else:
                stop_z = oz + random.uniform(0.3, h - 0.3)
                rod(f"m{i}_{k}", top, (px, py, stop_z), 0.12, m_muon, t0, t0 + 30, fade=3)
                # small absorption flash
                fl = sphere(f"fl{i}_{k}", 0.35, (px, py, stop_z), m_pion)
                key(fl, 1, scale=(0, 0, 0)); key(fl, t0 + 3, scale=(0, 0, 0)); key(fl, t0 + 5, scale=(1, 1, 1)); key(fl, t0 + 30, scale=(1, 1, 1)); key(fl, t0 + 34, scale=(0, 0, 0)); linear_keys(fl)

    # ------------------------------------------------------------------ S3 telescope under a hill (26–40)
    ox, oy, oz = off["S3"]
    box("g3", (200, 200, 1), (ox, oy + 20, oz - 0.5), m_ground)
    hill = sphere("hill", 1.0, (ox, oy + 6, oz), m_rock, scale=(22, 16, 11))
    cutter = box("cut3", (200, 60, 60), (ox, oy - 30 + 0.0, oz))
    boolean(hill, cutter)     # cut at y=0 so we look into the cross-section
    VOID3 = (ox + 5, oy + 2, oz + 5.0)
    vv = sphere("void3", 2.8, VOID3, m_void); vm = vv.modifiers.new("wire", 'WIREFRAME'); vm.thickness = 0.06; vm.use_replace = False
    TEL = Vector((ox - 3, oy + 1.5, oz + 1.4))
    cham_cut = box("cham_cut", (7, 7, 4.2), (TEL.x, TEL.y + 1.5, TEL.z + 0.9)); boolean(hill, cham_cut)
    box("cham_back", (7, 0.3, 4.2), (TEL.x, TEL.y + 5.0, TEL.z + 0.9), m_sil)
    for j in (0, 1):
        box(f"tp{j}", (4, 4, 0.12), (TEL.x, TEL.y, TEL.z - 0.6 + j * 1.2), m_alu)
        box(f"ts{j}", (3.6, 3.6, 0.2), (TEL.x, TEL.y, TEL.z - 0.5 + j * 1.2), m_scint)
    for k in range(110):
        th = random.uniform(0, math.radians(45)); ph = random.uniform(-math.pi * 0.9, math.pi * 0.9)
        d = Vector((math.sin(th) * math.cos(ph), abs(math.sin(th) * math.sin(ph)) * 0.6, math.cos(th)))  # keep in front half-space
        hit = TEL + Vector((random.uniform(-1.5, 1.5), random.uniform(-1.5, 1.5), 0.6))
        top = hit + d * 40
        # muons whose path crosses the cavity are "survivors": brighter
        pv = Vector(VOID3) - hit; along = pv.dot(d.normalized()); perp = (pv - d.normalized() * along).length
        through_void = 0 < along < 40 and perp < 2.8
        t0 = f(P_TELE + 1.0) + random.randint(0, int(10 * FPS))
        rod(f"t3_{k}", top, hit, 0.11, m_muon if through_void or random.random() < 0.45 else m_muon_dim, t0, t0 + 28, fade=3)

    # ------------------------------------------------------------------ S4 tomography (40–54)
    ox, oy, oz = off["S4"]
    box("g4", (200, 200, 1), (ox, oy + 20, oz - 0.5), m_ground)
    hill4 = sphere("hill4", 1.0, (ox, oy + 6, oz), m_rock_t, scale=(22, 16, 11))
    VOID4 = Vector((ox + 5, oy + 2, oz + 5.0))
    tels = [Vector((ox - 16, oy + 2, oz - 4)), Vector((ox + 2, oy + 2, oz - 6)), Vector((ox + 20, oy + 2, oz - 3))]
    for i, T in enumerate(tels):
        box(f"c4_{i}", (4, 4, 2.5), (T.x, T.y, T.z), m_sil)
        box(f"s4_{i}", (3.2, 3.2, 0.2), (T.x, T.y, T.z + 1.0), m_scint)
        t_on = f(P_TOMO + 1.0 + i * 2.5)
        for k in range(8):
            d = (VOID4 - T).normalized()
            jitter = Vector((random.uniform(-0.25, 0.25), random.uniform(-0.1, 0.1), random.uniform(-0.25, 0.25)))
            dd = (d + jitter).normalized()
            rod(f"ray{i}_{k}", T + Vector((0, 0, 1.2)), T + dd * 40, 0.045, m_ray, t_on + k * 3, f(P_END), fade=4)
    # voxel grid inside the hill; voxels within the void light up as each new viewpoint is added
    vox = []
    for ix in range(-9, 10):
        for iz in range(0, 10):
            px = ox + ix * 1.6; pz = oz + 0.8 + iz * 1.0; py = oy + 2
            # inside the (cut) hill?
            if ((px - ox) / 22) ** 2 + ((pz - oz) / 11) ** 2 > 0.80: continue
            inside = (Vector((px, py, pz)) - VOID4).length < 2.8
            c = box(f"vx{ix}_{iz}", (1.3, 0.6, 0.8), (px, py, pz), m_vox if inside else m_grid)
            vox.append((c, inside, px, pz))
    # m_vox emission ramps in three steps (one per telescope), from 0 → 1.5 → 4 → 10
    ie = m_vox.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    for i, val in enumerate((0.0, 1.5, 4.0, 10.0)):
        ie.default_value = val; ie.keyframe_insert("default_value", frame=f(P_TOMO + 0.5 + i * 2.5))
    # faint 'misfit' voxels along single rays: brief flicker when the 1st viewpoint only is on
    fe = m_grid.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    fe.default_value = 0.05; fe.keyframe_insert("default_value", frame=f(P_TOMO))
    fe.default_value = 0.3; fe.keyframe_insert("default_value", frame=f(P_TOMO + 3.0))
    fe.default_value = 0.05; fe.keyframe_insert("default_value", frame=f(P_TOMO + 9.0))
    m_grid.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = CYAN

    # ------------------------------------------------------------------ camera: hard cuts between shots
    bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
    cam.data.lens = 32; cam.data.sensor_width = 36
    tgt = D.objects.new("tgt2", None); sc.collection.objects.link(tgt)
    c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    o1, o2, o3, o4 = off["S1"], off["S2"], off["S3"], off["S4"]
    shots = [
        # (t_start, t_end, cam_a, tgt_a, cam_b, tgt_b)
        (P_SHOWER, P_ATTEN, (o1[0] - 70, -60, 45), (o1[0], 90, 45), (o1[0] - 40, -30, 30), (o1[0], 90, 30)),
        (P_ATTEN, P_TELE, (o2[0] - 6, -44, 9), (o2[0], 0, 6), (o2[0] + 4, -40, 7), (o2[0], 0, 5)),
        (P_TELE, P_TOMO, (o3[0] - 10, -44, 5), (o3[0], 4, 3), (o3[0] + 4, -40, 4), (o3[0] + 1, 4, 3)),
        (P_TOMO, P_OUTRO, (o4[0] - 8, -50, 8), (o4[0], 4, 2), (o4[0] + 6, -46, 6), (o4[0] + 2, 4, 2)),
        (P_OUTRO, P_END, (o4[0] + 6, -46, 6), (o4[0] + 2, 4, 2), (o4[0] + 2, -70, 16), (o4[0] + 2, 4, 2)),
    ]
    for t0, t1, ca, ta, cb, tb in shots:
        fa, fb = f(max(t0, 1 / FPS)), f(t1) - 1
        key(cam, fa, loc=ca); key(tgt, fa, loc=ta); key(cam, fb, loc=cb); key(tgt, fb, loc=tb)
    for o in (cam, tgt):
        for fc in S.fcurves(o):
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    # ease within each shot: use bezier but keep cuts hard (consecutive keys at fb and fa+1 are different shots)
    for o in (cam, tgt):
        for fc in S.fcurves(o):
            pts = fc.keyframe_points
            for i, kp in enumerate(pts):
                if i % 2 == 0: kp.interpolation = 'BEZIER'; kp.easing = 'EASE_IN_OUT'
                else: kp.interpolation = 'CONSTANT'

    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True; sc.cycles.max_bounces = 3
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Punchy'
    except Exception: pass
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.image_settings.compression = 50
    return sc

def render(start, end, res, samples, out, step=1, device="CPU"):
    sc = build()
    if device != "CPU":
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = device; prefs.get_devices()
            for d in prefs.devices: d.use = True
            sc.cycles.device = 'GPU'
        except Exception as e: print("GPU setup failed:", e)
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.cycles.samples = samples; os.makedirs(out, exist_ok=True)
    for fr in range(start, end + 1, step):
        p = os.path.join(out, f"{fr:04d}.png")
        if os.path.exists(p): continue
        sc.frame_set(fr); sc.render.filepath = p; bpy.ops.render.render(write_still=True); print("rendered", fr, flush=True)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1); ap.add_argument("--end", type=int, default=f(P_END))
    ap.add_argument("--step", type=int, default=5); ap.add_argument("--res", type=int, nargs=2, default=[1280, 720])
    ap.add_argument("--samples", type=int, default=12); ap.add_argument("--out", default="render_p"); ap.add_argument("--device", default="CPU")
    a = ap.parse_args(argv)
    render(a.start, a.end, a.res, a.samples, a.out, a.step, a.device)
