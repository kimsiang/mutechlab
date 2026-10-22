"""Build + render the 3D plates for the 缪子科技实验室 promo.

Run:   python3 scene.py --start 1 --end 810 --res 1920 1080 --samples 32 --out frames
       (or inside Blender: blender -b -P scene.py -- ...)

Layout (metres):  X = along the street, Y = depth (camera looks +Y), Z = up.
The earth is cut at the plane y = 0; everything with y < 0 is "air" so the
camera can see the strata, pipes and the metro tunnel in cross-section.
"""
import sys, os, math, random, argparse
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import *

random.seed(7)
D = bpy.data

# ----------------------------------------------------------------- helpers
def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, color=(0.8, 0.8, 0.8, 1), rough=0.6, metal=0.0, emit=None, emit_str=0.0, alpha=1.0):
    m = D.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = emit
        b.inputs["Emission Strength"].default_value = emit_str
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = 'BLEND'
    return m

def noisy(m, scale=8.0, detail=6.0, bump=0.4, dark=0.55, light=1.0):
    """Add procedural grime/variation + bump to a material."""
    nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n["Principled BSDF"]
    base = b.inputs["Base Color"].default_value[:]
    tex = n.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = detail; tex.inputs["Roughness"].default_value = 0.7
    g = n.new("ShaderNodeNewGeometry"); l.new(g.outputs["Position"], tex.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (base[0]*dark, base[1]*dark, base[2]*dark, 1)
    ramp.color_ramp.elements[1].color = (min(1, base[0]*light), min(1, base[1]*light), min(1, base[2]*light), 1)
    l.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bmp = n.new("ShaderNodeBump"); bmp.inputs["Strength"].default_value = bump
    l.new(tex.outputs["Fac"], bmp.inputs["Height"])
    l.new(bmp.outputs["Normal"], b.inputs["Normal"])
    return m

def bricky(m, color_a, color_b, mortar=(0.72, 0.68, 0.62, 1), scale=1.0):
    nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n["Principled BSDF"]
    br = n.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = scale
    br.inputs["Color1"].default_value = color_a; br.inputs["Color2"].default_value = color_b
    br.inputs["Mortar"].default_value = mortar; br.inputs["Mortar Size"].default_value = 0.025
    br.inputs["Brick Width"].default_value = 0.45; br.inputs["Row Height"].default_value = 0.16
    tc = n.new("ShaderNodeNewGeometry")
    mp = n.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    l.new(tc.outputs["Position"], mp.inputs["Vector"]); l.new(mp.outputs["Vector"], br.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.8; nz.inputs["Detail"].default_value = 8
    l.new(tc.outputs["Position"], nz.inputs["Vector"])
    mix = n.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = 0.35
    l.new(br.outputs["Color"], mix.inputs[6]); l.new(nz.outputs["Color"], mix.inputs[7])
    l.new(mix.outputs[2], b.inputs["Base Color"])
    bmp = n.new("ShaderNodeBump"); bmp.inputs["Strength"].default_value = 0.6
    l.new(br.outputs["Fac"], bmp.inputs["Height"]); l.new(bmp.outputs["Normal"], b.inputs["Normal"])
    return m

def box(name, size, loc, m=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    o.scale = size
    if m: o.data.materials.append(m)
    return o

def cyl(name, r, depth, loc, m=None, rot=(0, 0, 0), verts=48):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.object; o.name = name
    if m: o.data.materials.append(m)
    return o

def sphere(name, r, loc, m=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=48, ring_count=24)
    o = bpy.context.object; o.name = name; o.scale = scale
    bpy.ops.object.shade_smooth()
    if m: o.data.materials.append(m)
    return o

def boolean(o, cutter, op='DIFFERENCE'):
    md = o.modifiers.new("bool", 'BOOLEAN'); md.operation = op; md.object = cutter
    md.solver = 'EXACT'
    cutter.hide_render = True; cutter.hide_viewport = True
    return md

def key(o, frame, loc=None, rot=None, scale=None):
    if loc is not None:
        o.location = loc; o.keyframe_insert("location", frame=frame)
    if rot is not None:
        o.rotation_euler = rot; o.keyframe_insert("rotation_euler", frame=frame)
    if scale is not None:
        o.scale = scale; o.keyframe_insert("scale", frame=frame)


def fcurves(o):
    """All fcurves of an object's action (Blender 4.4+ layered actions)."""
    ad = o.animation_data
    if not ad or not ad.action: return []
    act = ad.action
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])): return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out

def smooth_keys(o):
    for fc in fcurves(o):
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'; kp.easing = 'EASE_IN_OUT'

def linear_keys(o):
    for fc in fcurves(o):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'

# ----------------------------------------------------------------- palette
NAVY   = (0.004, 0.047, 0.098, 1)
CYAN   = (0.0, 0.66, 0.96, 1)
EBLUE  = (0.13, 0.32, 1.0, 1)

# ----------------------------------------------------------------- build
def build():
    clear()
    sc = bpy.context.scene
    sc.frame_start = 1; sc.frame_end = f(PLATE_END)
    sc.render.fps = FPS

    # ---- world: daylight sky
    w = D.worlds.new("World"); sc.world = w; w.use_nodes = True
    wn = w.node_tree.nodes; wl = w.node_tree.links
    sky = wn.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
    try:
        sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(200)
        sky.sun_intensity = 0.35; sky.altitude = 50
    except Exception:
        pass
    wn["Background"].inputs["Strength"].default_value = 0.05
    wl.new(sky.outputs["Color"], wn["Background"].inputs["Color"])
    # sun lamp
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 60))
    sun = bpy.context.object; sun.data.energy = 4.5; sun.data.angle = math.radians(2)
    sun.rotation_euler = (math.radians(45), math.radians(-25), math.radians(20))

    # ---- materials
    m_brick   = bricky(mat("brick", (0.45, 0.17, 0.10, 1), 0.85), (0.48, 0.17, 0.09, 1), (0.36, 0.12, 0.07, 1))
    m_brick2  = bricky(mat("brick2", (0.55, 0.30, 0.18, 1), 0.85), (0.60, 0.33, 0.18, 1), (0.46, 0.24, 0.13, 1))
    m_leaf    = noisy(mat("leaf", (0.12, 0.32, 0.08, 1), 0.8), scale=6, bump=0.8, dark=0.5, light=1.3)
    m_bark    = noisy(mat("bark", (0.22, 0.14, 0.08, 1), 0.9), scale=10, bump=0.6)
    m_awning  = mat("awning", (0.75, 0.12, 0.08, 1), 0.6)
    m_awning2 = mat("awning2", (0.05, 0.25, 0.18, 1), 0.6)
    m_stone   = noisy(mat("stone", (0.62, 0.58, 0.50, 1), 0.8), scale=1.2, detail=8, bump=0.3)
    m_glass   = mat("glass", (0.05, 0.08, 0.12, 1), 0.15, 0.6)
    m_asphalt = noisy(mat("asphalt", (0.12, 0.12, 0.13, 1), 0.95), scale=2, detail=10, bump=0.3, dark=0.7, light=1.1)
    m_curb    = noisy(mat("curb", (0.55, 0.55, 0.52, 1), 0.9), scale=1.5, bump=0.2)
    m_paint   = mat("paint", (0.9, 0.85, 0.6, 1), 0.7)
    m_soil    = noisy(mat("soil", (0.33, 0.22, 0.13, 1), 1.0), scale=0.6, detail=12, bump=1.0, dark=0.45, light=1.2)
    m_gravel  = noisy(mat("gravel", (0.40, 0.36, 0.30, 1), 1.0), scale=25, detail=10, bump=1.0, dark=0.4, light=1.3)
    m_rock    = noisy(mat("rock", (0.30, 0.29, 0.27, 1), 0.95), scale=0.5, detail=12, bump=1.0, dark=0.35, light=1.3)
    m_clay    = noisy(mat("clay", (0.60, 0.32, 0.18, 1), 0.8), scale=15, bump=0.3)
    m_copper  = mat("copper", (0.80, 0.45, 0.28, 1), 0.35, 1.0)
    m_steel   = mat("steel", (0.70, 0.72, 0.75, 1), 0.35, 1.0)
    m_alu     = mat("alu", (0.78, 0.80, 0.82, 1), 0.45, 0.9)
    m_concrete= noisy(mat("concrete", (0.52, 0.52, 0.50, 1), 0.9), scale=1.5, detail=10, bump=0.4, dark=0.7, light=1.1)
    m_lamp    = mat("lamp", (1, 1, 1, 1), 0.5, emit=(1, 0.85, 0.6, 1), emit_str=30)
    m_scint   = mat("scint", (0.1, 0.35, 0.9, 1), 0.2, emit=(0.2, 0.5, 1.0, 1), emit_str=0.6)
    m_muon    = mat("muon", CYAN, 0.3, emit=CYAN, emit_str=25)
    m_image   = mat("image", CYAN, 0.3, emit=CYAN, emit_str=0.0, alpha=0.6)
    m_image2  = mat("image2", CYAN, 0.3, emit=CYAN, emit_str=0.0, alpha=0.2)
    m_yellow  = mat("yellow", (0.95, 0.75, 0.05, 1), 0.3, 0.2)
    m_silver  = mat("silver", (0.75, 0.76, 0.78, 1), 0.3, 0.8)
    m_red     = mat("red", (0.55, 0.05, 0.05, 1), 0.3, 0.2)
    m_tyre    = mat("tyre", (0.03, 0.03, 0.03, 1), 0.9)
    m_rail    = mat("rail", (0.5, 0.5, 0.52, 1), 0.3, 1.0)
    m_box     = mat("eqbox", (0.85, 0.85, 0.82, 1), 0.5)
    m_frame   = mat("frame", NAVY, 0.4, 0.6)
    m_stripe  = mat("stripe", (0.9, 0.5, 0.05, 1), 0.5)

    # ---- earth block (y 0..70, z -24..0) with tunnel and a hidden void cut out
    earth = box("earth", (160, 70, 24), (0, 35, -12), m_soil)
    # strata: override base color by depth using a color ramp on z
    nt = m_soil.node_tree; n = nt.nodes; l = nt.links
    geo = n.new("ShaderNodeNewGeometry"); sep = n.new("ShaderNodeSeparateXYZ")
    l.new(geo.outputs["Position"], sep.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -24; mr.inputs["From Max"].default_value = 0
    l.new(sep.outputs["Z"], mr.inputs["Value"])
    strata = n.new("ShaderNodeValToRGB")
    cr = strata.color_ramp; cr.interpolation = 'CONSTANT'
    cr.elements[0].color = (0.20, 0.19, 0.18, 1)             # bedrock
    cr.elements[1].position = 0.42; cr.elements[1].color = (0.40, 0.35, 0.27, 1)  # gravel
    e = cr.elements.new(0.60); e.color = (0.42, 0.23, 0.10, 1)   # red clay
    e = cr.elements.new(0.70); e.color = (0.55, 0.45, 0.28, 1)   # sand lens
    e = cr.elements.new(0.76); e.color = (0.24, 0.15, 0.08, 1)   # subsoil
    e = cr.elements.new(0.90); e.color = (0.15, 0.09, 0.04, 1)   # topsoil
    e = cr.elements.new(0.975); e.color = (0.32, 0.32, 0.30, 1)  # road base
    l.new(mr.outputs["Result"], strata.inputs["Fac"])
    # multiply strata with existing noise ramp
    ramp = [x for x in n if x.type == 'VALTORGB' and x is not strata][0]
    mix = n.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = 1.0
    l.new(strata.outputs["Color"], mix.inputs[6]); l.new(ramp.outputs["Color"], mix.inputs[7])
    # ramp was dark..light of soil colour -> normalise to grey multiplier
    ramp.color_ramp.elements[0].color = (0.3, 0.3, 0.3, 1); ramp.color_ramp.elements[1].color = (1.6, 1.6, 1.6, 1)
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[1].position = 0.65
    # pebbles: voronoi cells, strongest in gravel / road-base bands
    vor = n.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 6.0; vor.feature = 'F1'
    l.new(geo.outputs["Position"], vor.inputs["Vector"])
    vr = n.new("ShaderNodeValToRGB"); vr.color_ramp.elements[0].position = 0.25; vr.color_ramp.elements[0].color = (0.55, 0.52, 0.48, 1)
    vr.color_ramp.elements[1].position = 0.45; vr.color_ramp.elements[1].color = (1, 1, 1, 1)
    l.new(vor.outputs["Distance"], vr.inputs["Fac"])
    mix2 = n.new("ShaderNodeMix"); mix2.data_type = 'RGBA'; mix2.blend_type = 'MULTIPLY'
    pm = n.new("ShaderNodeValToRGB"); pm.color_ramp.interpolation = 'CONSTANT'
    pm.color_ramp.elements[0].color = (0, 0, 0, 1); pm.color_ramp.elements[1].position = 0.30; pm.color_ramp.elements[1].color = (1, 1, 1, 1)
    e = pm.color_ramp.elements.new(0.60); e.color = (0, 0, 0, 1)
    e = pm.color_ramp.elements.new(0.975); e.color = (1, 1, 1, 1)
    l.new(mr.outputs["Result"], pm.inputs["Fac"]); l.new(pm.outputs["Color"], mix2.inputs["Factor"])
    l.new(mix.outputs[2], mix2.inputs[6]); l.new(vr.outputs["Color"], mix2.inputs[7])
    l.new(mix2.outputs[2], n["Principled BSDF"].inputs["Base Color"])
    # bump from pebbles + noise
    bmp = [x for x in n if x.type == 'BUMP'][0]
    add = n.new("ShaderNodeMath"); add.operation = 'ADD'
    l.new(vor.outputs["Distance"], add.inputs[0]); l.new([x for x in n if x.type == 'TEX_NOISE'][0].outputs["Fac"], add.inputs[1])
    l.new(add.outputs[0], bmp.inputs["Height"]); bmp.inputs["Strength"].default_value = 0.8

    TUN_Y, TUN_Z, TUN_R = 2.2, -10.0, 3.2
    tun_cut = cyl("tun_cut", TUN_R + 0.35, 200, (0, TUN_Y, TUN_Z), rot=(0, math.pi/2, 0))
    boolean(earth, tun_cut)
    VOID = (9.0, 0.9, -5.0)
    void_cut = sphere("void_cut", 1.0, VOID, scale=(2.6, 2.0, 1.4))
    boolean(earth, void_cut)

    # foreground rock shelf (y<0, below the tunnel floor) like the reference
    shelf = box("shelf", (160, 40, 10), (0, -20, -19), m_rock)
    shelf2 = box("shelf2", (160, 12, 2.5), (0, -6, -14.9), m_rock)

    # ---- street level
    box("road", (160, 9, 0.1), (0, 7.5, 0.02), m_asphalt)
    for x in range(-70, 71, 6):
        box(f"dash{x}", (2.5, 0.18, 0.02), (x, 7.5, 0.08), m_paint)
    box("walk_near", (160, 3, 0.3), (0, 1.5, 0.15), m_curb)
    box("walk_far", (160, 3, 0.3), (0, 13.5, 0.15), m_curb)

    # ---- buildings (brick blocks with window grids), two rows
    def building(name, x, y, w, d, h, m):
        b = box(name, (w, d, h), (x, y + d/2, h/2), m)
        # cornice + window slabs
        box(name + "_cor", (w + 0.4, d + 0.4, 0.4), (x, y + d/2, h + 0.1), m_stone)
        nx = max(2, int(w / 2.8)); nz = max(2, int((h - 2) / 3.2))
        for i in range(nx):
            for j in range(nz):
                wx = x - w/2 + (i + 0.5) * w / nx
                wz = 2.2 + j * 3.2
                box(f"{name}_w{i}{j}", (1.4, 0.3, 1.9), (wx, y - 0.08, wz), m_glass)
                box(f"{name}_s{i}{j}", (1.7, 0.4, 0.15), (wx, y - 0.1, wz - 1.0), m_stone)
        return b
    xs = -40; i = 0
    mats_b = [m_brick, m_brick2, m_stone, m_brick]
    while xs < 44:
        w = random.uniform(9, 15); h = random.uniform(12, 24)
        if xs > -4 and xs < 6:      # street gap in the middle of the far row
            xs += 10; continue
        building(f"b{i}", xs + w/2, 15.2, w, 14, h, mats_b[i % 4]); xs += w + 0.8; i += 1
    # tall skyline silhouettes further back
    for k in range(14):
        x = random.uniform(-80, 80); h = random.uniform(40, 110); w = random.uniform(8, 16)
        box(f"sky{k}", (w, w, h), (x, random.uniform(70, 140), h/2), m_stone if k % 3 else m_glass)

    # trees on the far sidewalk, street lamps, awnings, water towers
    for x in range(-38, 44, 9):
        cyl(f"trunk{x}", 0.18, 3.0, (x, 13.6, 1.5), m_bark)
        sphere(f"crown{x}", 1.0, (x, 13.6, 3.6), m_leaf, scale=(1.6, 1.6, 1.3))
        cyl(f"lamp{x}", 0.07, 5.5, (x + 4.5, 1.2, 2.75), m_alu)
        box(f"lamph{x}", (0.5, 0.25, 0.15), (x + 4.5, 1.2, 5.5), m_alu)
    for k, x in enumerate(range(-32, 40, 11)):
        box(f"awn{x}", (3.0, 1.6, 0.08), (x, 14.4, 3.2), m_awning if k % 2 else m_awning2, rot=(math.radians(15), 0, 0))

    # ---- cars rolling along the road
    cars = []
    for k, (col, x0, lane) in enumerate([(m_yellow, -30, 5.3), (m_silver, -8, 5.3), (m_red, 12, 9.7), (m_silver, 34, 9.7)]):
        body = box(f"car{k}", (4.4, 1.9, 0.9), (x0, lane, 0.7), col)
        cab = box(f"cab{k}", (2.4, 1.7, 0.8), (x0 - 0.2, lane, 1.45), m_glass); cab.parent = body; cab.matrix_parent_inverse = body.matrix_world.inverted()
        for dx in (-1.4, 1.4):
            for dy in (-0.95, 0.95):
                t = cyl(f"ty{k}{dx}{dy}", 0.36, 0.3, (x0 + dx, lane + dy, 0.36), m_tyre, rot=(math.pi/2, 0, 0))
                t.parent = body; t.matrix_parent_inverse = body.matrix_world.inverted()
        v = 7.0 if lane < 7 else -6.0
        key(body, 1, loc=(x0, lane, 0.7)); key(body, f(PLATE_END), loc=(x0 + v * PLATE_END, lane, 0.7))
        linear_keys(body)

    # ---- utilities in the cut face: clay sewer (sticks out), copper mains, sheet piles
    sewer = cyl("sewer", 0.9, 6, (-6, 2.6, -2.6), m_clay, rot=(math.pi/2, 0, 0))
    sewer_in = cyl("sewer_in", 0.72, 6.2, (-6, 2.6, -2.6), m_rock, rot=(math.pi/2, 0, 0))
    cyl("main1", 0.22, 160, (0, 0.0, -1.5), m_copper, rot=(0, math.pi/2, 0))
    cyl("main2", 0.16, 160, (0, 0.0, -2.3), m_steel, rot=(0, math.pi/2, 0))
    for x in range(-34, 40, 7):
        box(f"pile{x}", (0.5, 0.6, 7), (x, 0.0, -3.6), m_stripe if x % 2 else m_alu)

    # ---- metro tunnel: concrete rings, cut open at y=0
    cutter = box("front_cutter", (300, 60, 60), (0, -30, 0))
    rings = []
    for k in range(-24, 25):
        r = cyl(f"ring{k}", TUN_R, 3.6, (k * 3.8, TUN_Y, TUN_Z), m_concrete, rot=(0, math.pi/2, 0), verts=64)
        inner = cyl(f"ringin{k}", TUN_R - 0.32, 4.0, (k * 3.8, TUN_Y, TUN_Z), rot=(0, math.pi/2, 0), verts=64)
        boolean(r, inner); boolean(r, cutter)
    box("floor", (200, 5.2, 0.6), (0, TUN_Y, TUN_Z - 2.0), m_concrete)
    for dy in (-0.72, 0.72):
        box(f"rail{dy}", (200, 0.1, 0.12), (0, TUN_Y + dy, TUN_Z - 1.64), m_rail)
    for x in range(-60, 61, 6):
        box(f"strip{x}", (3.5, 0.25, 0.08), (x, TUN_Y + 1.2, TUN_Z + 2.35), m_lamp)
        box(f"strip2{x}", (3.5, 0.25, 0.08), (x, TUN_Y - 1.2, TUN_Z + 2.35), m_lamp)
    # equipment cabinets on the far side
    for x in (-12, -9, 16, 19):
        box(f"cab{x}", (1.2, 0.8, 1.8), (x, TUN_Y + 2.0, TUN_Z - 0.8), m_box)

    # ---- muon telescope: 4 blue scintillator planes in an aluminium frame on a trolley
    TEL = (4.0, TUN_Y, TUN_Z - 1.55)
    box("trolley", (2.4, 2.0, 0.25), (TEL[0], TEL[1], TEL[2] + 0.12), m_alu)
    for dx in (-1.0, 1.0):
        for dy in (-0.8, 0.8):
            cyl(f"wheel{dx}{dy}", 0.18, 0.12, (TEL[0] + dx, TEL[1] + dy, TEL[2] - 0.0), m_tyre, rot=(math.pi/2, 0, 0))
            box(f"post{dx}{dy}", (0.08, 0.08, 2.2), (TEL[0] + dx, TEL[1] + dy, TEL[2] + 1.3), m_alu)
    planes = []
    for j in range(4):
        z = TEL[2] + 0.55 + j * 0.5
        box(f"frame{j}", (2.1, 1.7, 0.10), (TEL[0], TEL[1], z), m_frame)
        p = box(f"scint{j}", (1.9, 1.5, 0.12), (TEL[0], TEL[1], z + 0.06), m_scint); planes.append(p)
    box("daq", (0.6, 0.4, 0.5), (TEL[0] + 1.6, TEL[1], TEL[2] + 0.4), m_box)
    box("daq_led", (0.05, 0.1, 0.05), (TEL[0] + 1.6, TEL[1] - 0.22, TEL[2] + 0.55), m_muon)

    # ---- muon rain: thin emissive rods from the sky through buildings/earth into the telescope
    rods = []
    top = Vector((TEL[0], TEL[1], TEL[2] + 2.2))
    for k in range(130):
        th = random.uniform(0, math.radians(32)); ph = random.uniform(0, 2*math.pi)
        d = Vector((math.sin(th)*math.cos(ph), math.sin(th)*math.sin(ph), math.cos(th)))
        hit = Vector((TEL[0] + random.uniform(-0.9, 0.9), TEL[1] + random.uniform(-0.7, 0.7), TEL[2] + 0.5))
        L = 75.0
        mid = hit + d * (L/2)
        rot = d.to_track_quat('Z', 'Y').to_euler()
        r = cyl(f"muon{k}", 0.035, L, mid, m_muon, rot=rot, verts=8)
        t0 = random.uniform(T_MUONS, T_WIDE + 3.0)
        fa = f(t0); dur = 12
        key(r, 1, scale=(0, 0, 0)); key(r, fa, scale=(0, 0, 0)); key(r, fa + 2, scale=(1, 1, 1))
        key(r, fa + dur, scale=(1, 1, 1)); key(r, fa + dur + 2, scale=(0, 0, 0))
        linear_keys(r)
        rods.append((r, fa))
    # hits: scintillator planes flash when a rod is "on"
    bsd = m_scint.node_tree.nodes["Principled BSDF"]
    es = bsd.inputs["Emission Strength"]
    es.default_value = 0.6; es.keyframe_insert("default_value", frame=1)
    for r, fa in sorted(rods, key=lambda x: x[1]):
        es.default_value = 0.6; es.keyframe_insert("default_value", frame=fa + 1)
        es.default_value = 6.0; es.keyframe_insert("default_value", frame=fa + 3)
        es.default_value = 0.6; es.keyframe_insert("default_value", frame=fa + 7)

    # ---- muography image: glowing cyan reconstruction of the void + a halo along the pipes
    img = sphere("void_img", 1.0, VOID, m_image, scale=(2.5, 1.9, 1.3))
    mod = img.modifiers.new("wire", 'WIREFRAME'); mod.thickness = 0.05; mod.use_replace = False
    pipe_img = cyl("pipe_img", 0.30, 40, (0, 0.0, -1.5), m_image2, rot=(0, math.pi/2, 0))
    pm = pipe_img.modifiers.new("wire", 'WIREFRAME'); pm.thickness = 0.03; pm.use_replace = False
    for mm, top in ((m_image, 14.0), (m_image2, 2.0)):
        ie = mm.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        ie.default_value = 0.0; ie.keyframe_insert("default_value", frame=f(T_IMAGE))
        ie.default_value = top; ie.keyframe_insert("default_value", frame=f(T_IMAGE + 2.5))
        ie.default_value = top; ie.keyframe_insert("default_value", frame=f(PLATE_END))
    for o in (img, pipe_img):
        key(o, 1, scale=(0, 0, 0)); key(o, f(T_IMAGE) - 1, scale=(0, 0, 0))
        key(o, f(T_IMAGE), scale=o.scale if o is img else (1, 1, 1))
    # scanning plane that sweeps up through the earth as the image forms
    scan = box("scan", (60, 60, 0.03), (0, 30, TUN_Z), m_muon)
    key(scan, 1, scale=(0, 0, 0)); key(scan, f(T_IMAGE) - 1, scale=(0, 0, 0)); key(scan, f(T_IMAGE), scale=(60, 60, 0.03))
    key(scan, f(T_IMAGE), loc=(0, 30, TUN_Z - 1)); key(scan, f(T_IMAGE + 3.0), loc=(0, 30, 0.0))
    key(scan, f(T_IMAGE + 3.0), scale=(60, 60, 0.03)); key(scan, f(T_IMAGE + 3.1), scale=(0, 0, 0))
    scan.hide_render = True  # the scan plane is loud; keep only the glowing void/pipes (toggle here)

    # ---- camera
    bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
    cam.data.lens = 32; cam.data.sensor_width = 36
    cam.data.dof.use_dof = False
    tgt = bpy.data.objects.new("target", None); sc.collection.objects.link(tgt)
    c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    # (time, cam pos, target pos, lens)
    path = [
        (T_STREET,      (-10, -34,  6.5), (2, 20,  8.0), 30),
        (T_CUT,         (-12, -34,  3.0), (2, 14,  4.0), 30),
        (T_CUT + 3.5,   (-10, -32, -6.0), (2,  8, -5.0), 32),
        (T_TUNNEL,      (-6,  -20, -8.5), (3,  4, -8.5), 35),
        (T_TUNNEL + 1.8,(-2,  -13, -9.0), (4,  2.2, -9.2), 40),
        (T_IMAGE,       ( 0,  -13, -8.6), (4.5, 2.2, -8.6), 40),
        (T_IMAGE + 2.5, ( 2,  -20, -6.0), (5,  4, -5.5), 36),
        (T_WIDE,        (-4,  -30, -3.0), (3,  8, -3.0), 32),
        (T_LOGO_IN,     (-6,  -38, -1.0), (2, 10, -2.0), 30),
        (PLATE_END,     (-8,  -40,  0.0), (2, 10, -2.0), 30),
    ]
    for t, cp, tp, lens in path:
        key(cam, f(max(t, 1/FPS)), loc=cp); key(tgt, f(max(t, 1/FPS)), loc=tp)
        cam.data.lens = lens; cam.data.keyframe_insert("lens", frame=f(max(t, 1/FPS)))
    smooth_keys(cam); smooth_keys(tgt)

    # ---- render settings
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = 0.0
    try: sc.view_settings.look = 'AgX - Punchy'
    except Exception: pass
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.compression = 50
    # (bloom is added in post by compose.py)
    return sc

def render(start, end, res, samples, out, step=1, device="CPU"):
    sc = build()
    if device != "CPU":
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = device; prefs.get_devices()
            for d in prefs.devices: d.use = True
            sc.cycles.device = 'GPU'
        except Exception as e:
            print("GPU setup failed, falling back to CPU:", e)
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    os.makedirs(out, exist_ok=True)
    for fr in range(start, end + 1, step):
        p = os.path.join(out, f"{fr:04d}.png")
        if os.path.exists(p): continue
        sc.frame_set(fr); sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print("rendered", fr, flush=True)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1); ap.add_argument("--end", type=int, default=f(PLATE_END))
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--res", type=int, nargs=2, default=[1920, 1080]); ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--out", default="frames"); ap.add_argument("--save", default="")
    ap.add_argument("--device", default="CPU", help="CPU | METAL | CUDA | OPTIX")
    a = ap.parse_args(argv)
    if a.save:
        sc = build(); bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save))
    else:
        render(a.start, a.end, a.res, a.samples, a.out, a.step, a.device)
