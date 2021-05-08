from bpy.types import Panel


class NodeRelaxBrushPanel(Panel):
    """Node Relax Panel"""
    bl_label = "Node Relax Brush"
    bl_idname = "NODE_RELAX_PT_brush_menu"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Node Relax'

    def draw(self, context):
        layout = self.layout
        props = context.scene.NodeRelax_props
        layout.operator("node_relax.brush", text="Relax Brush")
        layout.label(text = "Shortcut: Shift R")
        layout.separator()
        layout.prop(props, "BrushSize")
        layout.prop(props, "Distance")
        layout.separator()
        box = layout.box()
        box.prop(props, "RelaxPower")
        box.prop(props, "SlidePower")
        box.prop(props, "CollisionPower")