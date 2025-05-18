import bpy




def get_api_base_url(port):
    return f"http://localhost:{port}/api"

def import_file(directory, file_name):
    try:
        result = bpy.ops.sollumz.import_assets(
            directory=directory,
            files=[{"name": file_name}],
        )
        return result == {'FINISHED'}
    except Exception as e:
        print(f"[ERROR] Failed to import file '{file_name}': {e}")
        return False
    
def filter_only_top_level_objects(objects):
    local_set = set(objects)
    return [obj for obj in objects if obj.parent not in local_set]

def promote_to_root_objects(objects):
    result = set()
    for obj in objects:
        # Climb to the topmost parent
        top = obj
        while top.parent is not None:
            top = top.parent
        result.add(top)
    return list(result)

# This is a default equivalence profile for comparing objects, prepared for additional requirements
# in the future. It can be modified to include or exclude specific properties.
DEFAULT_EQUIVALENCE_PROFILE = {
    "mesh": True,
    "flags": False,
    "transform": False,
    "modifiers": False,
    "materials": False,
    "custom_properties": False,
}

def are_objects_equivalent(obj1, obj2, profile=None):
    if profile is None:
        profile = DEFAULT_EQUIVALENCE_PROFILE

    if obj1.type != obj2.type:
        return False

    if profile.get("mesh", False) and obj1.data != obj2.data:
        return False

    if profile.get("transform", False):
        if obj1.location != obj2.location:
            return False
        if obj1.rotation_euler != obj2.rotation_euler:
            return False
        if obj1.scale != obj2.scale:
            return False

    if profile.get("modifiers", False):
        if len(obj1.modifiers) != len(obj2.modifiers):
            return False
        for m1, m2 in zip(obj1.modifiers, obj2.modifiers):
            if m1.type != m2.type:
                return False
            # You can go deeper if needed (e.g., compare modifier properties)

    if profile.get("materials", False):
        if len(obj1.material_slots) != len(obj2.material_slots):
            return False
        for s1, s2 in zip(obj1.material_slots, obj2.material_slots):
            if s1.material != s2.material:
                return False

    if profile.get("custom_properties", False):
        keys1 = {k for k in obj1.keys() if not k.startswith("_")}
        keys2 = {k for k in obj2.keys() if not k.startswith("_")}
        if keys1 != keys2:
            return False
        for key in keys1:
            if obj1[key] != obj2[key]:
                return False

    if profile.get("flags", False):
        if getattr(obj1, "flags", None) != getattr(obj2, "flags", None):
            return False

    return True


def get_canonical_object_name(obj, scene_objects, profile=None):
    import re

    match = re.match(r"^(.*)\.(\d{3})$", obj.name)
    if not match:
        return obj.name  # not a duplicate

    base_name = match.group(1)
    base_obj = scene_objects.get(base_name)
    if not base_obj:
        return obj.name

    if are_objects_equivalent(obj, base_obj, profile=profile):
        return base_name

    return obj.name