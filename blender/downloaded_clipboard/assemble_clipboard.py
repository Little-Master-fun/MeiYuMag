from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
OBJ_PATH = ROOT / "source" / "model_0.obj"
TEXTURE_DIR = ROOT / "textures"
BLEND_PATH = ROOT / "downloaded_clipboard.blend"
PREVIEW_PATH = ROOT / "downloaded_clipboard_preview.png"
GLB_PATH = ROOT.parent.parent / "front-end" / "public" / "models" / "downloaded_clipboard.glb"


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load_image(filename: str, non_color: bool = False) -> bpy.types.Image:
    image = bpy.data.images.load(str(TEXTURE_DIR / filename), check_existing=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    return image


def image_node(nodes, image, name: str, location: tuple[float, float]):
    node = nodes.new("ShaderNodeTexImage")
    node.name = name
    node.label = name
    node.image = image
    node.location = location
    node.interpolation = "Linear"
    return node


def create_clipboard_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Clipboard_PBR")
    material.use_nodes = True
    material.diffuse_color = (0.42, 0.29, 0.18, 1.0)

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (700, 80)

    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.location = (400, 80)
    shader.inputs["Base Color"].default_value = (0.42, 0.29, 0.18, 1.0)
    shader.inputs["Roughness"].default_value = 0.72
    shader.inputs["Metallic"].default_value = 0.0
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    albedo = image_node(nodes, load_image("clipboard_albedo.png"), "Albedo", (-850, 360))
    roughness = image_node(
        nodes,
        load_image("clipboard_roughness.png", non_color=True),
        "Roughness",
        (-850, 100),
    )
    metallic = image_node(
        nodes,
        load_image("clipboard_metallic.png", non_color=True),
        "Metallic",
        (-850, -140),
    )
    normal = image_node(
        nodes,
        load_image("clipboard_normal.png", non_color=True),
        "Normal",
        (-850, -380),
    )
    ao = image_node(
        nodes,
        load_image("clipboard_AO.png", non_color=True),
        "Ambient Occlusion",
        (-850, -620),
    )

    links.new(albedo.outputs["Color"], shader.inputs["Base Color"])
    links.new(roughness.outputs["Color"], shader.inputs["Roughness"])
    links.new(metallic.outputs["Color"], shader.inputs["Metallic"])

    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (80, -320)
    normal_map.inputs["Strength"].default_value = 0.8
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])

    # Blender's glTF exporter recognizes this node group and exports AO correctly.
    group_name = "glTF Material Output"
    gltf_group = bpy.data.node_groups.get(group_name)
    if gltf_group is None:
        gltf_group = bpy.data.node_groups.new(group_name, "ShaderNodeTree")
        gltf_group.interface.new_socket(
            name="Occlusion",
            in_out="INPUT",
            socket_type="NodeSocketFloat",
        )
        gltf_group.interface.new_socket(
            name="Thickness",
            in_out="INPUT",
            socket_type="NodeSocketFloat",
        )
        gltf_group.nodes.new("NodeGroupInput")
        gltf_group.nodes.new("NodeGroupOutput")

    gltf_output = nodes.new("ShaderNodeGroup")
    gltf_output.name = group_name
    gltf_output.label = group_name
    gltf_output.node_tree = gltf_group
    gltf_output.location = (80, -600)
    links.new(ao.outputs["Color"], gltf_output.inputs["Occlusion"])

    return material


def create_parchment_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Clean_Yellow_Parchment")
    material.use_nodes = True
    material.diffuse_color = (0.72, 0.52, 0.24, 1.0)

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (360, 0)
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.location = (40, 0)
    # A clean warm parchment tone. This material intentionally has no normal,
    # metallic, or AO map so the original atlas cannot add grime or diagonal
    # grooves to the visible sheet of paper.
    shader.inputs["Base Color"].default_value = (0.72, 0.52, 0.24, 1.0)
    shader.inputs["Roughness"].default_value = 0.92
    shader.inputs["Metallic"].default_value = 0.0
    if "Coat Weight" in shader.inputs:
        shader.inputs["Coat Weight"].default_value = 0.0
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def create_falling_page(
    source: bpy.types.Object,
    parchment_material: bpy.types.Material,
    polygon_indices: range,
) -> bpy.types.Object:
    polygons = [
        source.data.polygons[index]
        for index in polygon_indices
        if index < len(source.data.polygons)
    ]
    # Use every paper helper face to recover the complete sheet outline. The
    # two broad polygons alone omit the folded top and bottom regions and make
    # the animated overlay look like a shorter, separate card.
    all_vertex_indices = {
        vertex_index
        for polygon in polygons
        for vertex_index in polygon.vertices
    }
    page_vertices = [source.data.vertices[index].co.copy() for index in all_vertex_indices]
    surface_polygons = sorted(polygons, key=lambda polygon: polygon.area, reverse=True)[:2]
    minimum_x = min(vertex.x for vertex in page_vertices)
    maximum_x = max(vertex.x for vertex in page_vertices)
    minimum_z = min(vertex.z for vertex in page_vertices)
    top_z = max(vertex.z for vertex in page_vertices)
    front_y = sum(polygon.center.y for polygon in surface_polygons) / len(surface_polygons)
    pivot = Vector(((minimum_x + maximum_x) * 0.5, front_y, top_z))

    # A regular grid provides enough vertices for the Three.js page shader to
    # create a soft bend. The source sheet only has two broad triangles, which
    # would still move like a rigid board regardless of the shader formula.
    columns = 24
    rows = 34
    width = maximum_x - minimum_x
    height = top_z - minimum_z
    vertices = []
    for row in range(rows + 1):
        z = -height * row / rows
        for column in range(columns + 1):
            x = -width * 0.5 + width * column / columns
            vertices.append((x, 0.0, z))

    faces = []
    row_width = columns + 1
    for row in range(rows):
        for column in range(columns):
            top_left = row * row_width + column
            top_right = top_left + 1
            bottom_left = top_left + row_width
            bottom_right = bottom_left + 1
            faces.append((top_left, bottom_left, bottom_right, top_right))

    mesh = bpy.data.meshes.new("Top_Page_Mesh")
    mesh.from_pydata(vertices, [], faces)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv_layer.data[loop_index].uv = (
                1.0 - (vertex.x + width * 0.5) / width,
                1.0 + vertex.z / height,
            )
    mesh.materials.append(parchment_material)
    for polygon in mesh.polygons:
        polygon.material_index = 0
        polygon.use_smooth = False
    mesh.update()

    page = bpy.data.objects.new("Top_Page", mesh)
    bpy.context.collection.objects.link(page)
    # Keep the duplicate exactly on the stationary sheet. Three.js resolves
    # the coincident depth with polygonOffset, so no visible physical gap is
    # required before the animation begins.
    page.location = pivot
    page["animation_role"] = "falling_page"
    page["page_width"] = width
    page["page_height"] = height
    return page


def import_model(
    material: bpy.types.Material,
    parchment_material: bpy.types.Material,
) -> tuple[list[bpy.types.Object], bpy.types.Object]:
    bpy.ops.wm.obj_import(
        filepath=str(OBJ_PATH),
        forward_axis="NEGATIVE_Y",
        up_axis="Z",
    )
    meshes = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("OBJ import produced no mesh objects")

    paper_polygon_indices = range(45, 90)
    for obj in meshes:
        obj.name = "Downloaded_Clipboard" if len(meshes) == 1 else f"Clipboard_{obj.name}"
        obj.data.name = f"{obj.name}_Mesh"
        obj.data.materials.clear()
        obj.data.materials.append(material)
        obj.data.materials.append(parchment_material)
        for polygon in obj.data.polygons:
            polygon.material_index = 0
        # Blender's OBJ importer reorders the source faces. This imported face
        # range contains the uppermost sheet and its thin folded edges. Giving
        # the complete sheet a dedicated material prevents dirty strips from
        # surviving around the otherwise clean paper surface.
        for polygon_index in paper_polygon_indices:
            if polygon_index < len(obj.data.polygons):
                obj.data.polygons[polygon_index].material_index = 1
        # Preserve the authored hard edges while smoothing curved metal components.
        for polygon in obj.data.polygons:
            polygon.use_smooth = True

    top_page = create_falling_page(meshes[0], parchment_material, paper_polygon_indices)
    meshes.append(top_page)

    world_corners = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    minimum = Vector((min(p.x for p in world_corners), min(p.y for p in world_corners), min(p.z for p in world_corners)))
    maximum = Vector((max(p.x for p in world_corners), max(p.y for p in world_corners), max(p.z for p in world_corners)))
    center = (minimum + maximum) * 0.5

    root = bpy.data.objects.new("Clipboard_Root", None)
    bpy.context.collection.objects.link(root)
    root.location = -center
    # The downloaded OBJ is authored upside down for Blender's Z-up view.
    # A 180-degree Y rotation keeps the textured front facing forward while
    # placing the metal clamp at the top like a conventional clipboard.
    root.rotation_euler.y = math.pi
    for obj in meshes:
        obj.parent = root

    return meshes, root


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_preview(meshes: list[bpy.types.Object], root: bpy.types.Object) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 760
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(PREVIEW_PATH)

    if scene.world is None:
        scene.world = bpy.data.worlds.new("Preview_World")
    scene.world.color = (0.8, 0.77, 0.68)
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.91, 0.86, 0.74, 1.0)
        background.inputs["Strength"].default_value = 0.65

    camera_data = bpy.data.cameras.new("Preview_Camera")
    camera = bpy.data.objects.new("Preview_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (2.65, -4.8, 2.3)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.75
    camera_data.lens = 55
    look_at(camera, Vector((0.0, 0.0, 0.0)))
    scene.camera = camera

    key_data = bpy.data.lights.new("Key_Light", "AREA")
    key_data.energy = 650
    key_data.shape = "DISK"
    key_data.size = 4.0
    key = bpy.data.objects.new("Key_Light", key_data)
    bpy.context.collection.objects.link(key)
    key.location = (-3.0, -4.0, 5.0)
    look_at(key, Vector((0.0, 0.0, 0.0)))

    fill_data = bpy.data.lights.new("Fill_Light", "AREA")
    fill_data.energy = 350
    fill_data.size = 3.0
    fill = bpy.data.objects.new("Fill_Light", fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (3.5, -1.0, 1.2)
    look_at(fill, Vector((0.0, 0.0, 0.0)))

    rim_data = bpy.data.lights.new("Rim_Light", "AREA")
    rim_data.energy = 500
    rim_data.size = 2.5
    rim = bpy.data.objects.new("Rim_Light", rim_data)
    bpy.context.collection.objects.link(rim)
    rim.location = (-2.5, 2.5, 3.5)
    look_at(rim, Vector((0.0, 0.0, 0.2)))

    # A simple matte floor is preview-only and is not included in the exported GLB.
    floor_size = 8.0
    bpy.ops.mesh.primitive_plane_add(size=floor_size, location=(0.0, 0.0, -1.04))
    floor = bpy.context.object
    floor.name = "Preview_Floor"
    floor_material = bpy.data.materials.new("Preview_Floor_Material")
    floor_material.diffuse_color = (0.70, 0.72, 0.57, 1.0)
    floor_material.use_nodes = True
    floor_shader = next(
        node for node in floor_material.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"
    )
    floor_shader.inputs["Base Color"].default_value = (0.47, 0.52, 0.36, 1.0)
    floor_shader.inputs["Roughness"].default_value = 1.0
    floor.data.materials.append(floor_material)

    # Save the complete editable scene, with packed images for portability.
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    # Export only the downloaded model and its transform root.
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
    )

    scene.render.filepath = str(PREVIEW_PATH)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    if not OBJ_PATH.exists():
        raise FileNotFoundError(OBJ_PATH)
    reset_scene()
    material = create_clipboard_material()
    parchment_material = create_parchment_material()
    meshes, root = import_model(material, parchment_material)
    setup_preview(meshes, root)
    print(f"ASSEMBLED_BLEND={BLEND_PATH}")
    print(f"EXPORTED_GLB={GLB_PATH}")
    print(f"PREVIEW={PREVIEW_PATH}")
    print(f"MESHES={len(meshes)} VERTICES={sum(len(obj.data.vertices) for obj in meshes)}")


if __name__ == "__main__":
    main()
