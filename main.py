bl_info = {
    "name": "Lego Block 產生器",
    "author": "Gemini",
    "version": (1, 1),
    "blender": (5, 1, 1),
    "location": "View3D > Add > Mesh > Lego Block",
    "description": "產生以 8mm 為基準並依單位細分的 LEGO 方塊",
    "category": "Add Mesh",
}

import bpy
import bmesh
import mathutils

def add_subdivided_face(bm, p0, p1, p2, p3, seg_u, seg_v):
    v_matrix = []
    for j in range(seg_v + 1):
        row = []
        v_frac = j / seg_v
        for i in range(seg_u + 1):
            u_frac = i / seg_u
            
            # 用雙線性差值算出每個細分格點的座標位置
            w0 = (1 - u_frac) * (1 - v_frac)
            w1 = u_frac * (1 - v_frac)
            w2 = u_frac * v_frac
            w3 = (1 - u_frac) * v_frac
            
            pt = p0 * w0 + p1 * w1 + p2 * w2 + p3 * w3
            v = bm.verts.new(pt)
            row.append(v)
        v_matrix.append(row)
        
    for j in range(seg_v):
        for i in range(seg_u):
            v0 = v_matrix[j][i]
            v1 = v_matrix[j][i+1]
            v2 = v_matrix[j+1][i+1]
            v3 = v_matrix[j+1][i]
            bm.faces.new((v0, v1, v2, v3))

class MeshOtAddLegoBlock(bpy.types.Operator):
    """新增一個 Lego Block"""
    bl_idname = "mesh.add_lego_block"
    bl_label = "Lego Block"
    bl_options = {'REGISTER', 'UNDO'}

    unitsX: bpy.props.IntProperty(
        name="寬度 (X)",
        description="X 方向的 8mm 單位數量",
        default=1,
        min=1,
        max=100
    )
    unitsY: bpy.props.IntProperty(
        name="長度 (Y)",
        description="Y 方向的 8mm 單位數量",
        default=1,
        min=1,
        max=100
    )
    unitsZ: bpy.props.IntProperty(
        name="高度 (Z)",
        description="Z 方向的 8mm 單位數量",
        default=1,
        min=1,
        max=100
    )

    def execute(self, context):
        # 基準單位是 8mm，如果你的 Blender 已經設為 mm 單位，這裡用 8.0 就剛好
        unitSize = 8.0
        
        sizeX = self.unitsX * unitSize
        sizeY = self.unitsY * unitSize
        sizeZ = self.unitsZ * unitSize
        
        # 建立網格跟物件
        mesh = bpy.data.meshes.new(name="Lego_Block")
        obj = bpy.data.objects.new("Lego_Block", mesh)
        
        # 把物件丟進現在的場景裡，並設為選取狀態
        context.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        
        # 開一個空的 bmesh 來處理幾何
        bm = bmesh.new()
        
        x = sizeX / 2.0
        y = sizeY / 2.0
        z = sizeZ
        
        # 定義長方體的 8 個頂點，原點設在底部的正中心
        c0 = mathutils.Vector((-x, -y, 0))
        c1 = mathutils.Vector(( x, -y, 0))
        c2 = mathutils.Vector(( x,  y, 0))
        c3 = mathutils.Vector((-x,  y, 0))
        c4 = mathutils.Vector((-x, -y, z))
        c5 = mathutils.Vector(( x, -y, z))
        c6 = mathutils.Vector(( x,  y, z))
        c7 = mathutils.Vector((-x,  y, z))
        
        # 依序產生六個面，這裡會根據我們設定的單位數直接把面切好 (類似 Loop Cut)
        # 這樣之後要針對單一 8x8mm 的格子挖洞或做布林運算會很方便
        add_subdivided_face(bm, c0, c3, c2, c1, self.unitsY, self.unitsX)  # 底面
        add_subdivided_face(bm, c4, c5, c6, c7, self.unitsX, self.unitsY)  # 頂面
        add_subdivided_face(bm, c0, c1, c5, c4, self.unitsX, self.unitsZ)  # 前面
        add_subdivided_face(bm, c2, c3, c7, c6, self.unitsX, self.unitsZ)  # 後面
        add_subdivided_face(bm, c1, c2, c6, c5, self.unitsY, self.unitsZ)  # 右面
        add_subdivided_face(bm, c3, c0, c4, c7, self.unitsY, self.unitsZ)  # 左面
        
        # 因為每個面都是獨立產生的，邊緣的頂點會重疊在一起，這裡用距離判斷把它們融併起來
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
        
        # 合併完頂點後，法線方向可能會亂掉，順手重新計算一下法線朝外
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        
        bm.to_mesh(mesh)
        bm.free()
        
        return {'FINISHED'}

def menuFunc(self, context):
    self.layout.operator(MeshOtAddLegoBlock.bl_idname, icon='CUBE')

classes = (
    MeshOtAddLegoBlock,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.append(menuFunc)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.remove(menuFunc)

if __name__ == "__main__":
    register()
