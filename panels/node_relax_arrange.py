from bpy.types import Panel


class NodeRelaxArrangePanel(Panel):
    """Node Arrange Panel"""
    bl_label = "Node Arrange"
    bl_idname = "NODE_RELAX_PT_arrange_menu"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Node Relax'

    def draw(self, context):
        layout = self.layout
        props = context.scene.NodeRelax_props
        layout.operator("node_relax.arrange")
        if len(props.ArrangeState) > 0:
            layout.label(text=props.ArrangeState)
        layout.prop(props, "ArrangeOnlySelected")
        layout.separator()
        layout.label(text="Max Iterations:")
        box = layout.box()
        box.prop(props, "Iterations_S1")
        box.prop(props, "Iterations_S2")
        box.prop(props, "Iterations_S3")
        box.prop(props, "Iterations_S4")
        box.prop(props, "AdaptiveIters")
        # layout.separator()
        # layout.prop(props, "BackgroundIterations")
