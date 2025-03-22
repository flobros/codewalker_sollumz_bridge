import bpy
import os
import requests
from bpy.types import Operator
from bpy.props import BoolProperty
from .utils import get_api_base_url, import_file
from .props import CW_Sollumz_Properties


class PullBackendConfigOperator(Operator):
    bl_idname = "cw_sollumz.pull_config"
    bl_label = "Pull Config from Backend"

    def execute(self, context):
        props = context.scene.cw_sollumz_props
        try:
            response = requests.get(f"{get_api_base_url(props.api_port)}/get-config")
            if response.status_code == 200:
                config = response.json()
                props.codewalker_output_dir = config.get("codewalkerOutputDir", props.codewalker_output_dir)
                props.blender_output_dir = config.get("blenderOutputDir", props.blender_output_dir)
                props.fivem_output_dir = config.get("fivemOutputDir", props.fivem_output_dir)
                props.rpf_path = config.get("rpfArchivePath", props.rpf_path)
                self.report({'INFO'}, "Configuration pulled from backend.")
            else:
                self.report({'ERROR'}, f"Failed to fetch config: {response.status_code}")
        except Exception as e:
            self.report({'ERROR'}, f"Fetch failed: {str(e)}")
        return {'FINISHED'}

class SearchFileOperator(Operator):
    bl_idname = "cw_sollumz.search_file"
    bl_label = "Search File"

    def execute(self, context):
        props = context.scene.cw_sollumz_props
        if not props.search_filename.strip():
            self.report({'WARNING'}, "Please enter a filename to search.")
            return {'CANCELLED'}

        try:
            response = requests.get(f"{get_api_base_url(props.api_port)}/search-file", params={"filename": props.search_filename})
            if response.status_code == 200:
                results = response.json()
                props.search_results.clear()
                for result in results:
                    item = props.search_results.add()
                    item.name = result
                self.report({'INFO'}, f"Found {len(results)} files.")
            else:
                self.report({'ERROR'}, f"Search failed: {response.status_code}")
        except Exception as e:
            self.report({'ERROR'}, f"Request failed: {str(e)}")
        return {'FINISHED'}

class ImportFileOperator(Operator):
    bl_idname = "cw_sollumz.import_file"
    bl_label = "Import Selected File"

    index: bpy.props.IntProperty()

    def execute(self, context):
        props = context.scene.cw_sollumz_props
        if self.index >= len(props.search_results):
            self.report({'ERROR'}, "Invalid index.")
            return {'CANCELLED'}

        selected_path = props.search_results[self.index].name
        try:
            response = requests.get(f"{get_api_base_url(props.api_port)}/download-files", params={
                "fullPaths": selected_path,
                "xml": "true",
                "outputFolderPath": props.codewalker_output_dir
            })
            if response.status_code == 200:
                file_name = os.path.basename(selected_path) + ".xml"
                result = bpy.ops.sollumz.import_assets(directory=props.codewalker_output_dir, files=[{"name": file_name}])
                if result == {'FINISHED'}:
                    self.report({'INFO'}, "Import completed.")
            else:
                self.report({'ERROR'}, f"Import failed: {response.status_code}")
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {str(e)}")
        return {'FINISHED'}

class ExportToRpfOperator(Operator):
    bl_idname = "cw_sollumz.export_to_rpf"
    bl_label = "Export to RPF/FiveM"

    def execute(self, context):
        props = context.scene.cw_sollumz_props

        prefs = bpy.context.preferences.addons.get("bl_ext.user_default.sollumz")
        if prefs:
            export_settings = prefs.preferences.export_settings
            if hasattr(export_settings, 'export_with_ytyp'):
                export_settings.export_with_ytyp = False
                print("[DEBUG] export_with_ytyp has been set to:", export_settings.export_with_ytyp)
            else:
                print("[DEBUG] export_with_ytyp attribute not found on export_settings")
        else:
            print("[DEBUG] 'sollumz' addon not found in preferences")

        # === Track existing XMLs BEFORE export ===
        before_files = set(os.listdir(props.blender_output_dir))

        if props.export_with_ytyp:
            try:
                bpy.ops.sollumz.createytyp()

                selected_objects = context.selected_objects
                if len(selected_objects) == 1:
                    selected_name = selected_objects[0].name
                    ytyp_index = context.scene.ytyp_index
                    if 0 <= ytyp_index < len(context.scene.ytyps):
                        context.scene.ytyps[ytyp_index].name = selected_name
                else:
                    self.report({'WARNING'}, "Please select exactly one object to name the YTYP.")

                bpy.ops.sollumz.createarchetypefromselected()
                bpy.ops.sollumz.exportytyp(directory=props.blender_output_dir)
                self.report({'INFO'}, "YTYP created and exported.")
            except Exception as e:
                self.report({'WARNING'}, f"YTYP export failed: {e}")

        result = bpy.ops.sollumz.export_assets(directory=props.blender_output_dir)
        if result != {'FINISHED'}:
            self.report({'ERROR'}, "Export failed.")
            return {'CANCELLED'}

        # === Track new XML files created ===
        after_files = set(os.listdir(props.blender_output_dir))
        new_xmls = [os.path.join(props.blender_output_dir, f) for f in (after_files - before_files) if f.endswith(".xml")]

        if not new_xmls:
            self.report({'WARNING'}, "No new XML files to import.")
            return {'CANCELLED'}

        try:
            response = requests.post(f"{get_api_base_url(props.api_port)}/import-xml", data={
                "filePaths": new_xmls,
                "rpfArchivePath": props.rpf_path,
                "outputFolder": props.fivem_output_dir
            })
            if response.status_code == 200:
                self.report({'INFO'}, "Imported to RPF and FiveM output folder.")
            else:
                self.report({'ERROR'}, f"Import API failed: {response.status_code}")
        except Exception as e:
            self.report({'ERROR'}, f"Export error: {e}")

        return {'FINISHED'}


class ExportYtypOperator(Operator):
    bl_idname = "cw_sollumz.export_ytyp"
    bl_label = "Export YTYP Only"

    def execute(self, context):
        props = context.scene.cw_sollumz_props

        try:
            bpy.ops.sollumz.createytyp()

            selected_objects = context.selected_objects
            if len(selected_objects) == 1:
                selected_name = selected_objects[0].name
                ytyp_index = context.scene.ytyp_index
                if 0 <= ytyp_index < len(context.scene.ytyps):
                    context.scene.ytyps[ytyp_index].name = selected_name
            else:
                self.report({'WARNING'}, "Please select exactly one object to name the YTYP.")

            bpy.ops.sollumz.createarchetypefromselected()
            bpy.ops.sollumz.exportytyp(directory=props.blender_output_dir)
            self.report({'INFO'}, "YTYP exported successfully.")
        except Exception as e:
            self.report({'ERROR'}, f"YTYP export failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}
    
class SyncBackendConfigOperator(Operator):
    bl_idname = "cw_sollumz.sync_config"
    bl_label = "Sync Config to Backend"

    def execute(self, context):
        props = context.scene.cw_sollumz_props
        try:
            payload = {
                "codewalkerOutputDir": props.codewalker_output_dir,
                "blenderOutputDir": props.blender_output_dir,
                "fivemOutputDir": props.fivem_output_dir,
                "rpfArchivePath": props.rpf_path
            }
            response = requests.post(f"{get_api_base_url(props.api_port)}/set-config", json=payload)
            if response.status_code == 200:
                self.report({'INFO'}, "Backend configuration updated.")
            else:
                self.report({'ERROR'}, f"Failed to update backend config: {response.status_code}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to sync config: {str(e)}")
        return {'FINISHED'}

classes = [
    SearchFileOperator,
    ImportFileOperator,
    ExportToRpfOperator,
    ExportYtypOperator,
    SyncBackendConfigOperator,
    PullBackendConfigOperator
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)