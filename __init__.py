bl_info = {
    "name": "CodeWalker-Sollumz Bridge",
    "author": "tr1cks",
    "version": (1, 1, 0),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > CodeWalker-Sollumz",
    "description": "Import/export bridge between CodeWalker and Sollumz",
    "category": "Import-Export"
}

from . import props, ops, ui
def register():
    props.register()  # ✅ must be first
    ops.register()
    ui.register()

def unregister():
    ui.unregister()
    ops.unregister()
    props.unregister()
