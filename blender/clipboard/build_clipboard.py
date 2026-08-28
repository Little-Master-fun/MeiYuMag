import math
import os

import bpy
from mathutils import Vector


PROJECT_ROOT = "/Users/mact/code/web/MeiyuSystem"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "blender", "clipboard")
BLEND_PATH = os.path.join(OUTPUT_DIR, "wooden_clipboard.blend")
PREVIEW_PATH = os.path.join(OUTPUT_DIR, "wooden_clipboard_preview.png")
GLB_PATH = os.path.join(PROJECT_ROOT, "front-end", "public", "models", "wooden_clipboard.glb")
REFERENCE_PATH = os.path.join(
    PROJECT_ROOT,
    "front-end",
    "src",
    "assets",
    "images",
    "clipboard-concept.png",
)


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.curves, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def make_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def make_material(name, color, roughness=0.72, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = next((node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    output = next((node for node in nodes if node.bl_idname == "ShaderNodeOutputMaterial"), None)
    shader = shader or nodes.new("ShaderNodeBsdfPrincipled")
    output = output or nodes.new("ShaderNodeOutputMaterial")
    if not output.inputs["Surface"].is_linked:
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return material


def parent_to_model(obj):
    obj.parent = model_root
    move_to_collection(obj, model_collection)
    return obj


def add_bevel(obj, width, segments=1):
    modifier = obj.modifiers.new("Soft worn edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def make_box(name, dimensions, location, material, bevel=0.0, segments=1):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        add_bevel(obj, bevel, segments)
    obj.data.materials.append(material)
    return parent_to_model(obj)


def make_outline_prism(name, points, depth, y, material, bevel=0.0):
    count = len(points)
    front_y = y - depth * 0.5
    back_y = y + depth * 0.5
    vertices = [(x, front_y, z) for x, z in points]
    vertices += [(x, back_y, z) for x, z in points]
    faces = [tuple(range(count)), tuple(reversed(range(count, count * 2)))]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, count + next_index, count + index))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    model_collection.objects.link(obj)
    obj.parent = model_root
    obj.data.materials.append(material)
    if bevel:
        add_bevel(obj, bevel, 1)
    return obj


def chamfered_rectangle(width, height, chamfer, offsets=None):
    offsets = offsets or [(0.0, 0.0)] * 8
    base = [
        (-width / 2 + chamfer, -height / 2),
        (width / 2 - chamfer, -height / 2),
        (width / 2, -height / 2 + chamfer),
        (width / 2, height / 2 - chamfer),
        (width / 2 - chamfer, height / 2),
        (-width / 2 + chamfer, height / 2),
        (-width / 2, height / 2 - chamfer),
        (-width / 2, -height / 2 + chamfer),
    ]
    return [(x + dx, z + dz) for (x, z), (dx, dz) in zip(base, offsets)]


def make_flat_polygon(name, points, y, material, parent=True):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata([(x, y, z) for x, z in points], [], [tuple(range(len(points)))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    model_collection.objects.link(obj)
    obj.data.materials.append(material)
    if parent:
        obj.parent = model_root
    return obj


def make_curve(name, points, material, bevel_depth=0.012, cyclic=False, collection=None):
    curve_data = bpy.data.curves.new(name, "CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 1
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = 0
    spline = curve_data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        point.co = (*coordinate, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve_data)
    (collection or model_collection).objects.link(obj)
    curve_data.materials.append(material)
    if collection is None:
        obj.parent = model_root
    return obj


def make_leaf(name, center, length, width, angle, material, y=-0.246):
    direction = Vector((math.cos(angle), math.sin(angle)))
    normal = Vector((-direction.y, direction.x))
    center_vec = Vector(center)
    points_2d = [
        center_vec - direction * length * 0.5,
        center_vec + normal * width * 0.5,
        center_vec + direction * length * 0.5,
        center_vec - normal * width * 0.5,
    ]
    return make_flat_polygon(name, [(p.x, p.y) for p in points_2d], y, material)


def make_paper():
    width = 1.82
    bottom = -1.24
    top = 1.15
    x_segments = 9
    z_segments = 13
    vertices = []
    faces = []

    for z_index in range(z_segments + 1):
        v = z_index / z_segments
        z = bottom + (top - bottom) * v
        for x_index in range(x_segments + 1):
            u = x_index / x_segments
            x = -width * 0.5 + width * u
            if x_index == 0:
                x += math.sin(v * 17.0) * 0.012
            elif x_index == x_segments:
                x += math.sin(v * 19.0 + 0.8) * 0.014
            wave = math.sin(u * math.pi * 2.0 + v * 2.4) * 0.007
            edge = abs(u - 0.5) * 2.0
            lower = max(0.0, 0.2 - v) / 0.2
            corner_curl = lower * max(0.0, edge - 0.62) / 0.38
            y = -0.183 - wave - corner_curl * 0.095
            z_offset = corner_curl * 0.055
            if z_index in (0, z_segments):
                z_offset += math.sin(u * 21.0) * 0.009
            x_offset = math.sin(v * math.pi) * math.sin(u * math.pi * 2.0) * 0.006
            vertices.append((x + x_offset, y, z + z_offset))

    row = x_segments + 1
    for z_index in range(z_segments):
        for x_index in range(x_segments):
            a = z_index * row + x_index
            faces.append((a, a + 1, a + row + 1, a + row))

    mesh = bpy.data.meshes.new("Paper_Sheet_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    paper = bpy.data.objects.new("Paper_Sheet", mesh)
    model_collection.objects.link(paper)
    paper.parent = model_root
    paper.data.materials.append(paper_material)

    solidify = paper.modifiers.new("Paper thickness", "SOLIDIFY")
    solidify.thickness = 0.012
    solidify.offset = 0.0
    bevel = paper.modifiers.new("Soft paper edge", "BEVEL")
    bevel.width = 0.006
    bevel.segments = 1
    bpy.context.view_layer.objects.active = paper
    paper.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    paper.select_set(False)
    return paper


def make_cylinder(name, radius, depth, location, rotation, material, vertices=12, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    if bevel:
        add_bevel(obj, bevel, 1)
    obj.data.materials.append(material)
    return parent_to_model(obj)


def make_spring(name, x_start, x_end, y, z, material):
    turns = 4
    steps = 32
    radius = 0.072
    points = []
    for index in range(steps + 1):
        t = index / steps
        angle = turns * math.tau * t
        x = x_start + (x_end - x_start) * t
        points.append((x, y + math.cos(angle) * radius, z + math.sin(angle) * radius))
    return make_curve(name, points, material, bevel_depth=0.018)


def setup_preview():
    world = bpy.context.scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.915, 0.86, 0.74, 1.0)
    background.inputs["Strength"].default_value = 0.75

    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -1.77))
    ground = bpy.context.object
    ground.name = "Preview_Ground"
    move_to_collection(ground, preview_collection)
    ground.data.materials.append(background_material)

    bpy.ops.object.light_add(type="AREA", location=(-3.5, -4.5, 6.0))
    key = bpy.context.object
    key.name = "Preview_Key_Light"
    key.data.energy = 280
    key.data.shape = "DISK"
    key.data.size = 4.0
    move_to_collection(key, preview_collection)

    bpy.ops.object.light_add(type="AREA", location=(4.0, -1.5, 2.0))
    fill = bpy.context.object
    fill.name = "Preview_Fill_Light"
    fill.data.energy = 135
    fill.data.color = (0.68, 0.82, 0.73)
    fill.data.size = 3.0
    move_to_collection(fill, preview_collection)

    bpy.ops.object.light_add(type="AREA", location=(0.0, 3.0, 4.5))
    rim = bpy.context.object
    rim.name = "Preview_Rim_Light"
    rim.data.energy = 155
    rim.data.color = (1.0, 0.72, 0.48)
    rim.data.size = 2.5
    move_to_collection(rim, preview_collection)

    bpy.ops.object.camera_add(location=(4.15, -7.2, 3.9))
    camera = bpy.context.object
    camera.name = "Preview_Camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.65
    target = Vector((0.0, 0.0, 0.05))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    move_to_collection(camera, preview_collection)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 760
    scene.render.resolution_y = 920
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = PREVIEW_PATH
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_percentage = 100
    scene.render.use_file_extension = True
    scene.view_settings.look = "AgX - Medium Low Contrast"


def export_model():
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    bpy.ops.object.select_all(action="DESELECT")
    model_root.select_set(True)
    for obj in model_collection.all_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = model_root
    bpy.ops.export_scene.gltf(
        filepath=GLB_PATH,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
    )

    bpy.context.scene.render.filepath = PREVIEW_PATH
    bpy.ops.render.render(write_still=True)


os.makedirs(OUTPUT_DIR, exist_ok=True)
reset_scene()

model_collection = make_collection("CLIPBOARD_MODEL")
preview_collection = make_collection("PREVIEW_ONLY")

model_root = bpy.data.objects.new("WoodenClipboard_Root", None)
model_collection.objects.link(model_root)

wood_material = make_material("Wood_Painted_Slate_Blue", (0.055, 0.14, 0.21), 0.96)
wood_light_material = make_material("Wood_Faded_Blue", (0.10, 0.22, 0.29), 0.95)
wood_dark_material = make_material("Wood_Grain_Deep_Blue", (0.018, 0.052, 0.078), 0.98)
wood_highlight_material = make_material("Wood_Dry_Brush_Highlight", (0.17, 0.30, 0.34), 0.98)
exposed_wood_material = make_material("Wood_Exposed_Warm_Core", (0.30, 0.12, 0.045), 0.97)
sage_material = make_material("Worn_Moss_Sage", (0.14, 0.27, 0.18), 0.98)
paper_material = make_material("Paper_Warm_Ivory", (0.75, 0.65, 0.49), 0.99)
paper_mark_material = make_material("Paper_Botanical_Marks", (0.25, 0.33, 0.25), 0.99)
paper_wash_material = make_material("Paper_Painted_Wash", (0.70, 0.61, 0.47), 0.99)
metal_material = make_material("Clip_Matte_Rust", (0.30, 0.075, 0.028), 0.89, 0.18)
metal_dark_material = make_material("Clip_Dark_Iron", (0.035, 0.045, 0.042), 0.84, 0.28)
patina_material = make_material("Clip_Mossy_Patina", (0.10, 0.23, 0.17), 0.94, 0.06)
rust_highlight_material = make_material("Clip_Dry_Rust_Highlight", (0.46, 0.14, 0.055), 0.96, 0.04)
background_material = make_material("Preview_Warm_Cream", (0.915, 0.86, 0.74), 1.0)

# Main irregular wooden board.
board_outline = chamfered_rectangle(
    2.42,
    3.34,
    0.16,
    [
        (-0.02, 0.02),
        (0.015, 0.0),
        (-0.01, -0.01),
        (0.0, 0.015),
        (0.02, -0.01),
        (-0.015, 0.01),
        (0.0, -0.02),
        (0.012, 0.0),
    ],
)
board = make_outline_prism("Wooden_Board", board_outline, 0.18, 0.0, wood_material, 0.026)

inset_outline = chamfered_rectangle(2.16, 3.05, 0.12)
make_outline_prism("Wooden_Inset", inset_outline, 0.055, -0.112, wood_light_material, 0.016)

# Hand-painted plank seams and grain accents.
for index, x in enumerate((-0.98, -0.48, 0.02, 0.54, 1.0)):
    make_curve(
        f"Bottom_Plank_Seam_{index + 1}",
        [(x, -0.153, -1.60), (x + 0.012, -0.153, -1.37), (x - 0.008, -0.153, -1.18)],
        wood_dark_material,
        0.009,
    )

make_curve(
    "Left_Wood_Grain",
    [(-1.03, -0.154, -1.1), (-1.07, -0.154, -0.3), (-1.015, -0.154, 0.54)],
    wood_dark_material,
    0.012,
)
make_curve(
    "Right_Wood_Grain",
    [(1.04, -0.154, -0.9), (1.0, -0.154, 0.0), (1.055, -0.154, 0.82)],
    wood_dark_material,
    0.012,
)

# Worn moss patches and uneven dry-brush strokes around the exposed wooden border.
paint_patches = [
    [(-1.09, -1.50), (-0.88, -1.53), (-0.78, -1.39), (-0.85, -1.25), (-1.07, -1.30)],
    [(0.78, -1.50), (1.08, -1.46), (1.04, -1.24), (0.92, -1.17), (0.84, -1.31)],
    [(-1.09, 0.14), (-1.01, 0.04), (-0.96, 0.33), (-1.02, 0.66), (-1.10, 0.72)],
    [(0.99, 0.42), (1.08, 0.55), (1.04, 0.91), (0.96, 0.78), (0.92, 0.58)],
]
for index, patch in enumerate(paint_patches):
    make_flat_polygon(f"Sage_Paint_Patch_{index + 1}", patch, -0.157, sage_material)

dry_brush_strokes = [
    ("Blue_Stroke_01", [(-0.78, -1.58), (-0.58, -1.55), (-0.62, -1.27), (-0.73, -1.31)]),
    ("Blue_Stroke_02", [(-0.37, -1.58), (-0.18, -1.56), (-0.23, -1.23), (-0.32, -1.30)]),
    ("Blue_Stroke_03", [(0.18, -1.58), (0.39, -1.56), (0.33, -1.26), (0.23, -1.22)]),
    ("Blue_Stroke_04", [(0.57, -1.55), (0.77, -1.52), (0.70, -1.25), (0.61, -1.32)]),
    ("Blue_Stroke_Left", [(-1.105, -0.88), (-0.99, -0.82), (-1.01, -0.18), (-1.09, -0.30)]),
    ("Blue_Stroke_Right", [(0.99, -0.72), (1.09, -0.62), (1.06, 0.12), (1.00, -0.02)]),
]
for name, stroke in dry_brush_strokes:
    make_flat_polygon(name, stroke, -0.160, wood_highlight_material)

fine_brush_lines = [
    [(-0.90, -1.56), (-0.86, -1.54), (-0.82, -1.21), (-0.85, -1.17), (-0.89, -1.34)],
    [(-0.10, -1.55), (-0.06, -1.57), (-0.02, -1.20), (-0.07, -1.26)],
    [(0.46, -1.55), (0.50, -1.54), (0.55, -1.18), (0.50, -1.25)],
    [(-1.09, 0.78), (-1.04, 0.74), (-1.01, 1.34), (-1.07, 1.28)],
    [(1.01, 0.92), (1.07, 0.87), (1.04, 1.39), (0.99, 1.31)],
]
for index, stroke in enumerate(fine_brush_lines):
    make_flat_polygon(f"Fine_Dry_Brush_{index + 1}", stroke, -0.164, wood_light_material)

exposed_chips = [
    [(-1.15, -1.13), (-1.02, -1.08), (-1.09, -0.93)],
    [(1.06, -0.96), (1.14, -0.79), (1.03, -0.74)],
    [(-0.78, 1.52), (-0.55, 1.55), (-0.62, 1.47)],
    [(0.48, 1.53), (0.70, 1.52), (0.58, 1.45)],
]
for index, chip in enumerate(exposed_chips):
    make_flat_polygon(f"Exposed_Wood_Chip_{index + 1}", chip, -0.163, exposed_wood_material)

# Paper with a gentle, geometry-based curl.
paper = make_paper()

paper_washes = [
    [(-0.78, 0.61), (-0.58, 0.70), (-0.34, 0.61), (-0.27, 0.43), (-0.48, 0.35), (-0.72, 0.40)],
    [(0.33, -0.94), (0.55, -0.89), (0.72, -0.73), (0.64, -0.56), (0.38, -0.61), (0.27, -0.78)],
    [(-0.15, -0.18), (0.02, -0.13), (0.16, -0.02), (0.08, 0.08), (-0.11, 0.03)],
]
for index, wash in enumerate(paper_washes):
    make_flat_polygon(f"Paper_Wash_{index + 1}", wash, -0.244, paper_wash_material)

# Botanical pencil marks on the paper.
left_stem = [
    (-0.57, -0.249, -0.78),
    (-0.64, -0.249, -0.45),
    (-0.60, -0.249, -0.10),
    (-0.67, -0.249, 0.23),
    (-0.62, -0.249, 0.55),
]
right_stem = [
    (0.49, -0.249, -0.86),
    (0.58, -0.249, -0.58),
    (0.52, -0.249, -0.29),
]
make_curve("Paper_Left_Botanical_Stem", left_stem, paper_mark_material, 0.007)
make_curve("Paper_Right_Botanical_Stem", right_stem, paper_mark_material, 0.007)

leaf_specs = [
    ("Leaf_01", (-0.61, -0.48), 0.22, 0.09, 0.55),
    ("Leaf_02", (-0.62, -0.24), 0.20, 0.08, 2.55),
    ("Leaf_03", (-0.64, 0.02), 0.21, 0.085, 0.48),
    ("Leaf_04", (-0.63, 0.30), 0.19, 0.08, 2.62),
    ("Leaf_05", (0.54, -0.66), 0.19, 0.08, 2.45),
    ("Leaf_06", (0.54, -0.43), 0.18, 0.075, 0.64),
]
for spec in leaf_specs:
    make_leaf(*spec, paper_mark_material)

# Metal top clip, mounting plates, and bolts.
make_box("Clip_Main_Bar", (1.56, 0.24, 0.34), (0.0, -0.315, 1.23), metal_material, 0.035, 1)
make_box("Clip_Lower_Lip", (1.34, 0.09, 0.10), (0.0, -0.455, 1.10), metal_dark_material, 0.012, 1)

for side, x in (("Left", -0.89), ("Right", 0.89)):
    make_box(f"Clip_{side}_Mount", (0.34, 0.16, 0.28), (x, -0.27, 1.22), metal_material, 0.025, 1)
    make_cylinder(
        f"Clip_{side}_Bolt",
        0.082,
        0.085,
        (x, -0.385, 1.22),
        (math.pi / 2, 0.0, 0.0),
        metal_dark_material,
        12,
        0.01,
    )
    make_cylinder(
        f"Clip_{side}_Bolt_Cap",
        0.035,
        0.092,
        (x, -0.432, 1.22),
        (math.pi / 2, 0.0, 0.0),
        wood_light_material,
        10,
        0.006,
    )

# Raised handle tab with a visible hanging hole.
make_box("Clip_Tab_Stem", (0.43, 0.18, 0.62), (0.0, -0.24, 1.62), metal_material, 0.035, 1)
bpy.ops.mesh.primitive_torus_add(
    major_radius=0.17,
    minor_radius=0.075,
    major_segments=12,
    minor_segments=4,
    location=(0.0, -0.24, 1.91),
    rotation=(math.pi / 2, 0.0, 0.0),
)
tab_ring = bpy.context.object
tab_ring.name = "Clip_Tab_Ring"
tab_ring.data.materials.append(metal_material)
parent_to_model(tab_ring)

make_cylinder(
    "Clip_Hinge_Rod",
    0.045,
    1.33,
    (0.0, -0.145, 1.43),
    (0.0, math.pi / 2, 0.0),
    metal_dark_material,
    12,
    0.01,
)
make_spring("Clip_Left_Spring", -0.65, -0.28, -0.16, 1.43, metal_dark_material)
make_spring("Clip_Right_Spring", 0.28, 0.65, -0.16, 1.43, metal_dark_material)

# Sparse oxidized patina details on the metal face.
metal_patches = [
    [(-0.61, 1.32), (-0.28, 1.34), (-0.20, 1.18), (-0.51, 1.13)],
    [(0.16, 1.31), (0.47, 1.29), (0.42, 1.13), (0.09, 1.18)],
]
for index, patch in enumerate(metal_patches):
    make_flat_polygon(f"Clip_Patina_{index + 1}", patch, -0.442, patina_material)

clip_scratches = [
    [(-0.66, 1.31), (-0.50, 1.29), (-0.47, 1.25), (-0.63, 1.27)],
    [(-0.12, 1.17), (0.05, 1.19), (0.01, 1.23), (-0.16, 1.21)],
    [(0.48, 1.31), (0.68, 1.28), (0.64, 1.24), (0.45, 1.27)],
    [(-0.10, 1.72), (0.06, 1.76), (0.08, 1.70), (-0.08, 1.67)],
]
for index, scratch in enumerate(clip_scratches):
    make_flat_polygon(f"Clip_Rust_Scratch_{index + 1}", scratch, -0.447, rust_highlight_material)

# Small stylized nicks that help the board read as hand painted at a distance.
for index, (x, z, length, tilt) in enumerate(
    [
        (-0.82, -1.31, 0.18, 0.3),
        (-0.35, -1.46, 0.14, -0.15),
        (0.31, -1.40, 0.17, 0.2),
        (0.86, -1.26, 0.15, -0.28),
    ]
):
    dx = math.sin(tilt) * length * 0.5
    dz = math.cos(tilt) * length * 0.5
    make_curve(
        f"Board_Nick_{index + 1}",
        [(x - dx, -0.164, z - dz), (x + dx, -0.164, z + dz)],
        wood_dark_material,
        0.008,
    )

setup_preview()
export_model()

print(f"BLEND: {BLEND_PATH}")
print(f"GLB: {GLB_PATH}")
print(f"PREVIEW: {PREVIEW_PATH}")
