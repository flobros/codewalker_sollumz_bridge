import bpy
import os
import requests
from bpy.types import Operator
from bpy.props import BoolProperty, StringProperty
from .utils import promote_to_root_objects, get_api_base_url, import_file
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
                props.gtapath = config.get("GTAPath", props.gtapath)
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
    
class PickFolderAndSyncOperator(Operator):
    bl_idname = "cw_sollumz.pick_folder"
    bl_label = "Pick Folder and Sync"

    filepath: StringProperty(subtype="FILE_PATH")  # still needed by Blender internally
    directory: StringProperty(subtype="DIR_PATH")  # ✅ actual folder selected
    folder_prop: StringProperty()

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        props = context.scene.cw_sollumz_props
        folder_path = self.directory.rstrip("\\/")  # Normalize path

        # Track whether restart is needed
        requires_restart = False

        if self.folder_prop == "gtapath":
            if props.gtapath != folder_path:
                requires_restart = True
            props.gtapath = folder_path

        if self.folder_prop == "codewalker_output_dir":
            props.codewalker_output_dir = folder_path
        elif self.folder_prop == "blender_output_dir":
            props.blender_output_dir = folder_path
        elif self.folder_prop == "fivem_output_dir":
            props.fivem_output_dir = folder_path
        elif self.folder_prop == "rpf_path":
            props.rpf_path = folder_path

        # === Sync to backend
        try:
            payload = {
                "GTAPath": props.gtapath,
                "codewalkerOutputDir": props.codewalker_output_dir,
                "blenderOutputDir": props.blender_output_dir,
                "fivemOutputDir": props.fivem_output_dir,
                "rpfArchivePath": props.rpf_path
            }
            response = requests.post(f"{get_api_base_url(props.api_port)}/set-config", json=payload)
            if response.status_code == 200:
                self.report({'INFO'}, "Folder set and backend synced.")
                if requires_restart:
                    self.report({'WARNING'}, "GTA Path changed — please restart the backend to apply changes.")
            else:
                self.report({'ERROR'}, f"Sync failed: {response.status_code}")
        except Exception as e:
            self.report({'ERROR'}, f"Error: {e}")

        return {'FINISHED'}
class ExportToRpfOperator(Operator):
    bl_idname = "cw_sollumz.export_to_rpf"
    bl_label = "Export to RPF/FiveM"

    def execute(self, context):
        props = context.scene.cw_sollumz_props
        exported_files = []

        # === Force disable internal YTYP export ===
        prefs = bpy.context.preferences.addons.get("bl_ext.user_default.sollumz")
        if prefs:
            export_settings = prefs.preferences.export_settings
            if hasattr(export_settings, 'export_with_ytyp'):
                export_settings.export_with_ytyp = False
                print("[DEBUG] export_with_ytyp has been set to:", export_settings.export_with_ytyp)

        selected_objects = context.selected_objects
        selected_objects = promote_to_root_objects(selected_objects)

        for obj in selected_objects:
            try:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                context.view_layer.objects.active = obj

                # === Export model (YDR/YFT/etc) ===
                result = bpy.ops.sollumz.export_assets(directory=props.blender_output_dir)
                if result != {'FINISHED'}:
                    self.report({'WARNING'}, f"Model export failed for {obj.name}")
                    continue

                # === Conditionally export YTYP ===
                if props.export_with_ytyp:
                    print(f"[DEBUG] Exporting YTYP for {obj.name}")
                    try:
                        # Try to find an existing YTYP by name (case-insensitive match)
                        existing_ytyp = next((y for y in context.scene.ytyps if y.name.lower() == obj.name.lower()), None)

                        if existing_ytyp:
                            context.scene.ytyp_index = list(context.scene.ytyps).index(existing_ytyp)
                            print(f"[DEBUG] Found existing YTYP: {existing_ytyp.name}")
                        else:
                            # Create a new YTYP and name it after the object
                            bpy.ops.sollumz.createytyp()
                            new_ytyp = context.scene.ytyps[-1]
                            new_ytyp.name = obj.name.lower()
                            context.scene.ytyp_index = len(context.scene.ytyps) - 1
                            print(f"[DEBUG] Created new YTYP: {new_ytyp.name}")

                        # Add archetype to selected object
                        bpy.ops.sollumz.createarchetypefromselected()

                        # Export just this YTYP (per object export)
                        bpy.ops.sollumz.exportytyp(directory=props.blender_output_dir)

                    except Exception as e:
                        self.report({'WARNING'}, f"YTYP export failed for {obj.name}: {e}")

                # === Collect any matching .xml files for this object ===
                obj_name_lower = obj.name.lower()
                for f in os.listdir(props.blender_output_dir):
                    if f.lower().startswith(obj_name_lower + ".") and f.endswith(".xml"):
                        full_path = os.path.join(props.blender_output_dir, f)
                        exported_files.append(full_path)

            except Exception as e:
                self.report({'WARNING'}, f"Export failed for {obj.name}: {e}")

        if not exported_files:
            self.report({'ERROR'}, "No valid XML files were exported.")
            return {'CANCELLED'}

        # === Send collected files to backend ===
        try:
            response = requests.post(f"{get_api_base_url(props.api_port)}/import", data={
                "xml": "true",
                "filePaths": exported_files,
                "rpfArchivePath": props.rpf_path,
                "outputFolder": props.fivem_output_dir
            })

            if response.status_code == 200:
                self.report({'INFO'}, f"Imported {len(exported_files)} file(s) to RPF and FiveM.")
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
            selected_objects = promote_to_root_objects(selected_objects)
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
                "GTAPath": props.gtapath,
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
    PullBackendConfigOperator,
    PickFolderAndSyncOperator
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)