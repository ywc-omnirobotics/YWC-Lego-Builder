bl_info = {
    "name": "Lego Block 產生器",
    "author": "Gemini",
    "version": (1, 4),
    "blender": (2, 1, 1),
    "location": "View3D > Add > Mesh > Lego Block",
    "description": "產生以 8mm 為基準並依單位細分的 LEGO 方塊",
    "category": "Add Mesh",
}

import bpy
import bmesh
import mathutils
import os
import addon_utils

class MeshOtAddLegoBlock(bpy.types.Operator):
    """新增一個 Lego Block"""
    bl_idname = "mesh.add_lego_block"
    bl_label = "Lego Block"
    bl_options = {'REGISTER', 'UNDO'}

    unitsX: bpy.props.IntProperty(
        name="寬度 (X)", description="X 方向的 8mm 單位數量", default=1, min=1, max=100
    )
    unitsY: bpy.props.IntProperty(
        name="長度 (Y)", description="Y 方向的 8mm 單位數量", default=1, min=1, max=100
    )
    unitsZ: bpy.props.IntProperty(
        name="高度 (Z)", description="Z 方向的 8mm 單位數量", default=1, min=1, max=100
    )

    def execute(self, context):
        scene = context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.length_unit = 'MILLIMETERS'
        
        unitSize = 8.0
        finalWidth = self.unitsX * unitSize
        finalDepth = self.unitsY * unitSize
        finalHeight = self.unitsZ * unitSize
        
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False, align='WORLD', location=(0, 0, 0))
        newObj = context.active_object
        newObj.dimensions = (finalWidth, finalDepth, 0)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(newObj.data)

        if self.unitsX > 1:
            targetXCoords, xInt, xFrac = [], int(self.unitsX), self.unitsX - int(self.unitsX)
            if xFrac > 0.0001: targetXCoords.append(xFrac * unitSize)
            for i in range(1, xInt): targetXCoords.append((xFrac * unitSize) + (i * unitSize))
            mappedTargetsX = [c - finalWidth / 2 for c in sorted(targetXCoords)]
            for cutCoord in mappedTargetsX: bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(cutCoord, 0, 0), plane_no=(1, 0, 0))

        if self.unitsY > 1:
            targetYCoords, yInt, yFrac = [], int(self.unitsY), self.unitsY - int(self.unitsY)
            if yFrac > 0.0001: targetYCoords.append(yFrac * unitSize)
            for i in range(1, yInt): targetYCoords.append((yFrac * unitSize) + (i * unitSize))
            mappedTargetsY = [c - finalDepth / 2 for c in sorted(targetYCoords)]
            for cutCoord in mappedTargetsY: bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, cutCoord, 0), plane_no=(0, 1, 0))

        geom = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
        verts = [v for v in geom['geom'] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=verts, vec=(0, 0, finalHeight))
        bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()

        if self.unitsZ > 1:
            targetHeights, zInt, zFrac = [], int(self.unitsZ), self.unitsZ - int(self.unitsZ)
            if zFrac > 0.0001: targetHeights.append(zFrac * unitSize)
            for i in range(1, zInt): targetHeights.append((zFrac * unitSize) + (i * unitSize))
            for cutCoord in sorted(targetHeights): bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, cutCoord), plane_no=(0, 0, 1))

        bmesh.update_edit_mesh(newObj.data)
        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.update()
        
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        newObj.location.z -= (newObj.location.z - newObj.bound_box[0][2] * newObj.scale.z)
        newObj.location += context.scene.cursor.location
        newObj.name = "Lego_Block"
        return {'FINISHED'}

def performBooleanCut(operator, context, stlName, scaleY=None):
    stlImporterModule = "io_mesh_stl"
    isEnabled, _ = addon_utils.check(stlImporterModule)
    if not isEnabled:
        addon_utils.enable(stlImporterModule, default_set=True, persistent=False)
        
    try:
        baseDir = os.path.dirname(__file__)
    except NameError:
        baseDir = r"e:\3D Print\YWC Lego Builder"
        
    stlPath = os.path.join(baseDir, stlName)
    if not os.path.exists(stlPath):
        stlPath = os.path.join(r"e:\3D Print\YWC Lego Builder", stlName)
        if not os.path.exists(stlPath):
            operator.report({'ERROR'}, f"找不到 {stlName} 檔案: {stlPath}")
            return {'CANCELLED'}
            
    targetObj = context.active_object
    if not targetObj:
        return {'CANCELLED'}
        
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    
    bm = bmesh.from_edit_mesh(targetObj.data)
    
    selectedFaces = [f for f in bm.faces if f.select]
    if not selectedFaces:
        operator.report({'WARNING'}, "沒有選擇任何面。")
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'CANCELLED'}
        
    avgCenter = mathutils.Vector()
    avgNormal = mathutils.Vector()
    for f in selectedFaces:
        avgCenter += f.calc_center_median()
        avgNormal += f.normal
        
    avgCenter /= len(selectedFaces)
    avgNormal.normalize()
    
    worldCenter = targetObj.matrix_world @ avgCenter
    worldNormal = targetObj.matrix_world.to_3x3() @ avgNormal
    worldNormal.normalize()
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    objectsBeforeImport = set(context.scene.objects)
    
    try:
        bpy.ops.wm.stl_import(filepath=stlPath)
    except AttributeError:
        try:
            bpy.ops.import_mesh.stl(filepath=stlPath)
        except AttributeError:
            operator.report({'ERROR'}, "您的 Blender 版本不支援預設 STL 匯入，請更新 Blender。")
            return {'CANCELLED'}
            
    objectsAfterImport = set(context.scene.objects)
    newObjects = objectsAfterImport - objectsBeforeImport
    
    cutterObj = None
    if newObjects:
        cutterObj = list(newObjects)[0]
        
    if cutterObj is None:
        operator.report({'ERROR'}, "STL 檔案匯入失敗，可能是檔案損壞或格式不正確。")
        return {'CANCELLED'}
        
    cutterObj.name = f"CUTTER_{os.path.splitext(stlName)[0]}"
    
    bpy.ops.object.select_all(action='DESELECT')
    context.view_layer.objects.active = cutterObj
    cutterObj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    
    # --- 布林破圖終極修復 ---
    # 1. 清理 STL 幾何 (避免重疊點或法線反轉)
    cutterBm = bmesh.new()
    cutterBm.from_mesh(cutterObj.data)
    bmesh.ops.remove_doubles(cutterBm, verts=cutterBm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(cutterBm, faces=cutterBm.faces)
    cutterBm.to_mesh(cutterObj.data)
    cutterBm.free()
    
    # 2. 微調縮放打破共面 (Coplanar) 問題
    # 如果 Cutter 剛好 8mm 長，切 8mm 的積木會導致表面完美重疊，這會讓 EXACT 布林直接崩潰 (破圖或失敗)。
    # 我們沿著深度軸 (Y軸) 稍微放大 1% (8.08mm)，讓兩端稍微突出去，保證完美切穿！
    if scaleY is not None:
        # 轉軸模式：先按用戶指定的格數縮放，再多 1% 避免共面
        cutterObj.scale.y = scaleY * 1.01
    else:
        cutterObj.scale.y = 1.01
    
    fromVector = mathutils.Vector((0, -1, 0))
    rotationQuat = fromVector.rotation_difference(worldNormal)
    
    cutterObj.location = worldCenter
    cutterObj.rotation_euler = rotationQuat.to_euler()
    
    cutterObj.location -= worldNormal * 4.0
    
    context.view_layer.update()
    context.view_layer.objects.active = targetObj
    targetObj.select_set(True)
    
    boolMod = targetObj.modifiers.new(name="LegoBoolean", type='BOOLEAN')
    boolMod.object = cutterObj
    boolMod.operation = 'DIFFERENCE'
    boolMod.solver = 'EXACT'
    
    try:
        bpy.ops.object.modifier_apply(modifier=boolMod.name)
    except RuntimeError as e:
        operator.report({'ERROR'}, f"布林運算失敗: {e}。請檢查模型幾何是否有問題。")
        bpy.data.objects.remove(cutterObj, do_unlink=True)
        return {'CANCELLED'}
        
    bpy.data.objects.remove(cutterObj, do_unlink=True)
    bpy.ops.object.mode_set(mode='EDIT')
    
    return {'FINISHED'}

class MeshOtInsertPin(bpy.types.Operator):
    """在選取的面上插入 PIN 圓孔"""
    bl_idname = "mesh.insert_pin"
    bl_label = "插入 PIN 孔"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH' and
                context.active_object is not None and
                context.active_object.type == 'MESH')

    def execute(self, context):
        return performBooleanCut(self, context, "PIN.stl")

class MeshOtInsertAxle(bpy.types.Operator):
    """在選取的面上插入 AXLE 十字孔"""
    bl_idname = "mesh.insert_axle"
    bl_label = "插入 AXLE 孔"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH' and
                context.active_object is not None and
                context.active_object.type == 'MESH')

    def execute(self, context):
        return performBooleanCut(self, context, "AXLE.stl")

class MeshOtInsertShaft(bpy.types.Operator):
    """在選取的面上插入 轉軸 孔（可指定格數拉長）"""
    bl_idname = "mesh.insert_shaft"
    bl_label = "插入 轉軸 孔"
    bl_options = {'REGISTER', 'UNDO'}

    units: bpy.props.IntProperty(
        name="格數", description="轉軸長度（幾格，1格 = 8mm）", default=1, min=1, max=100
    )

    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH' and
                context.active_object is not None and
                context.active_object.type == 'MESH')

    def invoke(self, context, event):
        # 彈出對話框讓用戶輸入格數
        return context.window_manager.invoke_props_dialog(self, title="轉軸設定")

    def execute(self, context):
        # scaleY = 用戶指定的格數（shaft.stl 預設為 1 格 = 8mm）
        return performBooleanCut(self, context, "SHAFT.stl", scaleY=float(self.units))

def editMenuFunc(self, context):
    self.layout.separator()
    self.layout.operator(MeshOtInsertPin.bl_idname, icon='MESH_CYLINDER')
    self.layout.operator(MeshOtInsertAxle.bl_idname)
    self.layout.operator(MeshOtInsertShaft.bl_idname, icon='CON_ROTLIMIT')

def menuFunc(self, context):
    self.layout.operator(MeshOtAddLegoBlock.bl_idname, icon='CUBE')

classes = (
    MeshOtAddLegoBlock,
    MeshOtInsertPin,
    MeshOtInsertAxle,
    MeshOtInsertShaft,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.append(menuFunc)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(editMenuFunc)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.remove(menuFunc)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(editMenuFunc)

if __name__ == "__main__":
    register()
