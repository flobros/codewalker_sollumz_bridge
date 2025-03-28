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

