import bpy
from bpy.types import Panel, UIList
import os
from .ops import SyncBackendConfigOperator  # ✅ Move Operator to ops

class CW_Sollumz_UIList(UIList):
    bl_idname = "CW_SOL_UL_SEARCH_LIST"  # 🔄 Use proper Blender naming convention (_UL_)

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)

        filename = os.path.basename(item.name)
        folder = os.path.dirname(item.name)

        # Filename display
        row.label(text=filename, icon='FILE')

        # Import button
        op = row.operator("cw_sollumz.import_file", text="Import")
        op.index = index

class CodeWalkerSollumzPanel(Panel):
    bl_label = "CodeWalker-Sollumz API Panel"
    bl_idname = "CW_SOL_PANEL_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CodeWalker-Sollumz'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if not hasattr(scene, "cw_sollumz_props"):
            layout.label(text="[ERROR] Addon not initialized properly.", icon='ERROR')
            return

        props = scene.cw_sollumz_props

        # ⚙️ API Config
        box = layout.box()
        row = box.row()
        row.prop(props, "show_api_section", text="", icon='TRIA_DOWN' if props.show_api_section else 'TRIA_RIGHT', emboss=False)
        row.label(text="API Configuration")
        if props.show_api_section:
            box.prop(props, "api_port")

            row = box.row()
            row.prop(props, "codewalker_output_dir", text="CodeWalker Output")
            op = row.operator("cw_sollumz.pick_folder", text="", icon='FILE_FOLDER')
            op.folder_prop = "codewalker_output_dir"

            row = box.row()
            row.prop(props, "blender_output_dir", text="Blender Output")
            op = row.operator("cw_sollumz.pick_folder", text="", icon='FILE_FOLDER')
            op.folder_prop = "blender_output_dir"

            row = box.row()
            row.prop(props, "fivem_output_dir", text="FiveM Output")
            op = row.operator("cw_sollumz.pick_folder", text="", icon='FILE_FOLDER')
            op.folder_prop = "fivem_output_dir"

            row = box.row()
            row.prop(props, "rpf_path", text="RPF Archive")
            op = row.operator("cw_sollumz.pick_folder", text="", icon='FILE_FOLDER')
            op.folder_prop = "rpf_path"

            box.operator("cw_sollumz.sync_config")
            box.operator("cw_sollumz.pull_config", text="Pull Config")

            
        # 📦 Export Options
        box = layout.box()
        row = box.row()
        row.prop(props, "show_export_section", text="", icon='TRIA_DOWN' if props.show_export_section else 'TRIA_RIGHT', emboss=False)
        row.label(text="Export")
        if props.show_export_section:
            box.prop(props, "export_with_ytyp")
            box.operator("cw_sollumz.export_to_rpf")
            box.operator("cw_sollumz.export_ytyp")

        # 🔍 Search Section
        box = layout.box()
        row = box.row()
        row.prop(props, "show_search_section", text="", icon='TRIA_DOWN' if props.show_search_section else 'TRIA_RIGHT', emboss=False)
        row.label(text="Search Files")
        if props.show_search_section:
            box.prop(props, "search_filename")
            box.operator("cw_sollumz.search_file")

        # 📄 Search Results
        layout.label(text="Results:", icon='PREVIEW_RANGE')
        layout.template_list("CW_SOL_UL_SEARCH_LIST", "", props, "search_results", scene, "cw_sollumz_active_index")



classes = [CW_Sollumz_UIList, CodeWalkerSollumzPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
