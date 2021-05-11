import bpy
import mathutils

from .utils import global_loc, calc_node
import gpu
from gpu_extras.presets import draw_circle_2d
from gpu_extras.batch import batch_for_shader

DRAW_COLOR = (1, 1, 1, 0.5)
DRAW_RADIUS = 10


def draw_callback(self):
    if self.drag_mode:
        if self.dragging_node:
            node = self.dragging_node
            loc = global_loc(node)

            x1, y1 = loc[0] - DRAW_RADIUS, loc[1] + DRAW_RADIUS
            x2, y2 = loc[0] + node.dimensions[0] + DRAW_RADIUS, loc[1] - node.dimensions[1] - DRAW_RADIUS

            shader = gpu.shader.from_builtin('2D_SMOOTH_COLOR')

            vertices = ((x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1))
            vertex_colors = (DRAW_COLOR, DRAW_COLOR, DRAW_COLOR, DRAW_COLOR, DRAW_COLOR)

            batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": vertices, "color": vertex_colors})

            shader.bind()
            batch.draw(shader)
    else:
        draw_circle_2d(self.cursor_pos, DRAW_COLOR, self.radius)


class NodeRelaxBrush(bpy.types.Operator):
    """Relax Nodes"""
    bl_idname = "node_relax.brush"
    bl_label = "Relax Nodes"

    bl_options = {"UNDO", "REGISTER"}

    def __init__(self):
        self.radius = 100
        self.lmb = False
        self.delta = mathutils.Vector((0, 0))
        self.cursor_pos = mathutils.Vector((0, 0))
        self.cursor_prev_pos = mathutils.Vector((0, 0))
        self.slide_vec = mathutils.Vector((0, 0))
        self. drag_mode = False
        self.is_dragging = False
        self.dragging_node = None

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'NODE_EDITOR' and space.node_tree is not None

    def update_cursor_pos(self, context, event):
        self.cursor_prev_pos = self.cursor_pos
        self.cursor_pos = mathutils.Vector(
            context.region.view2d.region_to_view(event.mouse_region_x, event.mouse_region_y))

    def update_radius(self, context, original_radius):
        radiusM = context.region.view2d.region_to_view(original_radius, 0)
        radius0 = context.region.view2d.region_to_view(0, 0)
        self.radius = radiusM[0] - radius0[0]

    def get_brush_influence(self, loc, size):
        self.delta.x = self.cursor_pos.x - min(max(self.cursor_pos.x, loc.x), loc.x + size.x)
        self.delta.y = self.cursor_pos.y - max(min(self.cursor_pos.y, loc.y), loc.y - size.y)

        dist_sqr = self.delta.x * self.delta.x + self.delta.y * self.delta.y

        return 1 - (dist_sqr / (self.radius * self.radius))

    def main_operation(self, context):
        nodes = self.tree.nodes
        props = context.scene.NodeRelax_props

        self.slide_vec = self.cursor_pos - self.cursor_prev_pos
        context.area.tag_redraw()

        if self.drag_mode:
            if self.is_dragging:
                if self.dragging_node:
                    self.dragging_node.location += self.slide_vec
            else:
                self.update_dragging_node(nodes)
        else:
            if self.lmb:
                dist = mathutils.Vector((props.Distance, props.Distance))
                for node in nodes:
                    if node.type == 'FRAME':
                        continue
                    # Brush
                    loc = global_loc(node)
                    size = node.dimensions
                    infl = self.get_brush_influence(loc, size)
                    if infl <= 0:
                        continue

                    # Calculate physics
                    calc_node(node, nodes, infl, self.slide_vec * props.SlidePower, props.RelaxPower,
                              props.CollisionPower, dist, False)

    def update_dragging_node(self, nodes):
        self.dragging_node = None
        nearest = 0
        for node in nodes:
            if node.type == 'FRAME':
                continue
            loc = global_loc(node)
            pos = mathutils.Vector((loc.x, loc.y))
            pos.x += node.dimensions.x / 2
            pos.y -= node.dimensions.y / 2
            pos -= self.cursor_pos
            dist = pos.x * pos.x + pos.y * pos.y  # Squared length
            if self.dragging_node is None or dist < nearest:
                self.dragging_node = node
                nearest = dist

    def finish(self, context, props):
        st = bpy.types.SpaceNodeEditor
        st.draw_handler_remove(self.draw_handler, 'WINDOW')
        props.IsRunning = False

    def modal(self, context, event):
        props = context.scene.NodeRelax_props

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:  # allow navigation shortcuts
            return {'PASS_THROUGH'}

        if event.type == 'LEFT_SHIFT' or event.type == 'RIGHT_SHIFT': # drag individual node
            if event.value == 'PRESS':
                self.drag_mode = True
            if event.value == 'RELEASE':
                self.drag_mode = False
            self.is_dragging = False
            self.update_dragging_node(self.tree.nodes)
            context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            self.update_cursor_pos(context, event)
            self.update_radius(context, props.BrushSize)
            self.main_operation(context)

        if event.type == 'WHEELUPMOUSE' or event.type == 'WHEELDOWNMOUSE':
            self.update_cursor_pos(context, event)
            self.update_radius(context, props.BrushSize)
            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                self.lmb = True
                if self.drag_mode:
                    self.is_dragging = True
                else:
                    self.update_cursor_pos(context, event)
                    self.cursor_prev_pos = self.cursor_pos  # No sliding
                    self.main_operation(context)
            if event.value == 'RELEASE':
                self.lmb = False
                if self.drag_mode:
                    self.is_dragging = False

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.finish(context, props)
            context.area.tag_redraw()
            return {'FINISHED'}

        if event.type == "LEFT_BRACKET":
            props.BrushSize -= 10
            props.BrushSize = max(props.BrushSize, 10)
            self.update_radius(context, props.BrushSize)
            context.area.tag_redraw()

        elif event.type == "RIGHT_BRACKET":
            props.BrushSize += 10
            props.BrushSize = min(props.BrushSize, 1000)
            self.update_radius(context, props.BrushSize)
            context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        props = context.scene.NodeRelax_props
        if props.IsRunning:
            return {'CANCELLED'}

        self.tree = context.space_data.edit_tree
        context.window_manager.modal_handler_add(self)
        st = bpy.types.SpaceNodeEditor
        self.draw_handler = st.draw_handler_add(draw_callback, (self,), 'WINDOW', 'POST_VIEW')

        self.lmb = False
        props.IsRunning = True
        self.update_cursor_pos(context, event)
        self.update_radius(context, props.BrushSize)

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}
