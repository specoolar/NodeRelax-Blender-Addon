# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "Node Relax",
    "author" : "Shahzod Boyhonov (Specoolar)",
    "description" : "Tool for arranging nodes easier",
    "blender" : (2, 92, 0),
    "version" : (1, 0, 0),
    "location" : "Node Editor > Properties > Node Relax. Shortcut: Shift R",
    "category": "Node",
}

import bpy
import bgl
import mathutils 
import gpu
from gpu_extras.presets import draw_circle_2d
from gpu_extras.batch import batch_for_shader

move_unit = 1

def draw_callback(self, context):
    if self.drag_mode:
        if self.dragging_node:
            node = self.dragging_node
            loc = global_loc(node)
            
            x1, y1 = loc[0] - 10,                    loc[1] + 10
            x2, y2 = loc[0] + node.dimensions[0] + 10, loc[1] - node.dimensions[1] - 10

            shader = gpu.shader.from_builtin('2D_SMOOTH_COLOR')

            vertices = ((x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1))
            vertex_colors = ((1,1,1,0.5),
                            (1,1,1,0.5),
                            (1,1,1,0.5),
                            (1,1,1,0.5),
                            (1,1,1,0.5))

            batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": vertices, "color": vertex_colors})

            shader.bind()
            batch.draw(shader)
    else:
        draw_circle_2d(self.cursor_pos, (1, 1, 1, 0.5), self.radius)


def global_loc(node):
    if node.parent:
        return global_loc(node.parent)+node.location
    else:
        return node.location

def collide(loc0, loc1, size0, size1, offset, power, dist, only_y = False):
    pos0 = loc0 + size0 / 2
    pos1 = loc1 + size1 / 2
    pos0.y -= size0.y
    pos1.y -= size1.y

    size = (size0 + size1)/2 + dist
    delta = pos1 - pos0
    inters = size - mathutils.Vector((abs(delta.x), abs(delta.y)))

    if inters.x>0 and inters.y>0:
        if inters.y < inters.x or only_y:
            if delta.y > 0:
                inters.y *= -1
            offset.y += inters.y / 2 * power
        else:
            if delta.x > 0:
                inters.x *= -1
            offset.x += inters.x / 2 * power

def calc_node(node, nodes, influence, slide_vec, relaxPower, collide_power, collide_dist, pull_non_siblings):
    if node.type == 'FRAME':
        return False
    
    loc = global_loc(node)
    size = node.dimensions
    
    offset = mathutils.Vector(slide_vec)

    if relaxPower > 0:
        # Relax
        tar_y = 0
        link_cnt = 0
        tar_x_in = loc.x
        has_input = False
        for socket in node.inputs:  # Input links
            for link in socket.links:
                other = link.from_node
                if not pull_non_siblings and node.parent != other.parent:
                    continue
                loc_other = global_loc(other)
                size_other = other.dimensions

                x = loc_other.x + size_other.x + collide_dist.x
                if has_input > 0:
                    tar_x_in = max(tar_x_in, x)
                else:
                    tar_x_in = x
                has_input = True
                
                tar_y += loc_other.y - size_other.y / 2
                link_cnt += 1

        tar_x_out = loc.x
        has_output = False
        for socket in node.outputs:  # Output links
            for link in socket.links:
                other = link.to_node
                if not pull_non_siblings and node.parent != other.parent:
                    continue
                loc_other = global_loc(other)
                size_other = other.dimensions

                x = loc_other.x - size.x - collide_dist.x
                if has_output > 0:
                    tar_x_out = min(tar_x_out, x)
                else:
                    tar_x_out = x
                has_output = True

                tar_y += loc_other.y - size_other.y / 2
                link_cnt += 1
        
        if link_cnt > 0:
            tar_x = tar_x_in * int(has_input) + tar_x_out * int(has_output)
            tar_x /= int(has_input) + int(has_output)
            tar_y /= link_cnt
            tar_y += size.y/2 
            offset.x += (tar_x-loc.x) * relaxPower
            offset.y += (tar_y-loc.y) * relaxPower

    if collide_power > 0:
        # Collision
        for other in nodes:
            if other == node:
                continue
            if other.type == 'FRAME':
                continue
            collide(loc, global_loc(other), size, other.dimensions,
                    offset, collide_power, collide_dist)

    if abs(offset.x) > move_unit or abs(offset.y) > move_unit:
        node.location += offset*influence
        return True
    else:
        return False
    
def calc_collision_y(node, nodes, collide_power, collide_dist):
    if node.type == 'FRAME':
        return False
    
    loc = global_loc(node)
    size = node.dimensions
    
    offset = mathutils.Vector((0,0))

    # Collision
    for other in nodes:
        if other == node:
            continue
        if other.type == 'FRAME':
            continue
        collide(loc, global_loc(other), size, other.dimensions,
                offset, 1, collide_dist, True)
    
    if abs(offset.y) > move_unit:
        node.location += offset * collide_power
        return True
    else:
        return False

def socket_pos(socket, sockets, size):
    i = 0
    sockets_filtered = []
    for s in sockets:
        if len(s.links) > 0:
            sockets_filtered.append(s)
            
    for s in sockets_filtered:
        if s == socket:
            return (i/len(sockets_filtered)) * size
        
        i += 1
    return size/2
    
def arrange_relax(node, nodes, influence, relaxPower, distance, clamped_pull):
    if node.type == 'FRAME':
        return False
    
    loc = global_loc(node)
    size = node.dimensions
    
    offset = mathutils.Vector((0,0))

    # Relax
    tar_y = 0
    tar_x_in = loc.x if clamped_pull else 0
    link_cnt = 0
    has_input = False
    for socket in node.inputs:  # Input links
        for link in socket.links:
            other = link.from_node
            # if node.parent != other.parent: continue
            loc_other = global_loc(other)
            size_other = other.dimensions
            
            x = loc_other.x + size_other.x + distance
            if clamped_pull:
                if has_input > 0:
                    tar_x_in = max(tar_x_in, x)
                else:
                    tar_x_in = x
            else:
                tar_x_in += x
            has_input = True

            tar_y += loc_other.y + socket_pos(socket, node.inputs, size.y) - socket_pos(link.from_socket, other.outputs, size_other.y)
            link_cnt += 1

    tar_x_out = loc.x if clamped_pull else 0
    has_output = False
    for socket in node.outputs:  # Output links
        for link in socket.links:
            other = link.to_node
            # if node.parent != other.parent: continue
            loc_other = global_loc(other)
            size_other = other.dimensions

            x = loc_other.x - size.x - distance
            if clamped_pull:
                if has_output > 0:
                    tar_x_out = min(tar_x_out, x)
                else:
                    tar_x_out = x
            else:
                tar_x_out += x
            has_output = True

            tar_y += loc_other.y + socket_pos(socket, node.outputs, size.y) - socket_pos(link.to_socket, other.inputs, size_other.y)
            link_cnt += 1

    
    if link_cnt > 0:
        if clamped_pull:
            tar_x = tar_x_in * int(has_input) + tar_x_out * int(has_output)
            tar_x /= int(has_input) + int(has_output)
        else:
            tar_x = (tar_x_in + tar_x_out)/link_cnt
        tar_y /= link_cnt
        offset.x += (tar_x-loc.x) * relaxPower
        offset.y += (tar_y - loc.y) * relaxPower
    
    if abs(offset.x) > move_unit or abs(offset.y) > move_unit:
        node.location += offset*influence
        return True
    else:
        return False

class NodeRelax_Brush(bpy.types.Operator):
    """Relax Nodes"""
    bl_idname = "node_relax.brush"
    bl_label = "Relax Nodes"

    bl_options = {"UNDO", "REGISTER"}

    radius = 100
    delta = mathutils.Vector((0, 0))
    cursor_pos = mathutils.Vector((0, 0))
    cursor_prev_pos = mathutils.Vector((0, 0))
    slide_vec = mathutils.Vector((0, 0))
    drag_mode = False
    is_dragging = False
    dragging_node = None

    @classmethod
    def poll(cls, context):
        space = context.space_data
        if space.type == 'NODE_EDITOR' and space.node_tree is not None:
            return True
        return False

    def update_cursor_pos(self, context, event):
        self.cursor_prev_pos = self.cursor_pos
        self.cursor_pos = mathutils.Vector(context.region.view2d.region_to_view(event.mouse_region_x, event.mouse_region_y))

    def update_radius(self, context, original_radius):
        radiusM = context.region.view2d.region_to_view(original_radius, 0)
        radius0 = context.region.view2d.region_to_view(0, 0)
        self.radius = radiusM[0]-radius0[0]

    def get_brush_influence(self, loc, size):
        self.delta.x = self.cursor_pos.x - min( max(self.cursor_pos.x, loc.x), loc.x + size.x)
        self.delta.y = self.cursor_pos.y - max( min(self.cursor_pos.y, loc.y), loc.y - size.y)

        dist_sqr = self.delta.x*self.delta.x + self.delta.y*self.delta.y

        return 1 - (dist_sqr / (self.radius * self.radius))

    def main_operation(self, context):
        infl = 0
        nodes = self.tree.nodes
        props = context.scene.NodeRelax_props

        self.slide_vec = self.cursor_pos - self.cursor_prev_pos
        context.area.tag_redraw()

        if self.drag_mode:
            if self.is_dragging:
                if self.dragging_node:
                    self.dragging_node.location += self.slide_vec
            else:
                self.updateDraggingNode(nodes)
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
                    calc_node(node, nodes, infl, self.slide_vec * props.SlidePower, props.RelaxPower, props.CollisionPower, dist, False)

    def updateDraggingNode(self, nodes):
        self.dragging_node = None
        nearest = 0
        for node in nodes:
            if node.type == 'FRAME':
                continue
            loc = global_loc(node)
            pos = mathutils.Vector((loc.x, loc.y))
            pos.x += node.dimensions.x/2
            pos.y -= node.dimensions.y/2
            pos -= self.cursor_pos
            dist = pos.x*pos.x + pos.y * pos.y  # Squared length
            if self.dragging_node is None or dist < nearest:
                self.dragging_node = node
                nearest = dist
            
    def Finish(self, context, props):
        st = bpy.types.SpaceNodeEditor
        st.draw_handler_remove(self.draw_handler, 'WINDOW')
        props.IsRunning = False

    def modal(self, context, event):
        props = context.scene.NodeRelax_props

        # When window maximized the region becomes None, which gives error, 
        # Workaround: stop modal operator when window maximized;
        # TODO fix later(maybe)
        if context.region is None:
            self.Finish(context, props)
            return {'FINISHED'}

        if event.type == 'LEFT_SHIFT' or event.type == 'RIGHT_SHIFT':
            if event.value == 'PRESS':
                self.drag_mode = True
            if event.value == 'RELEASE':
                self.drag_mode = False
            self.is_dragging = False
            self.updateDraggingNode(self.tree.nodes)
            context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            self.update_cursor_pos(context, event)
            self.update_radius(context, props.BrushSize)
            self.main_operation(context)
            return {'RUNNING_MODAL'}

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
                    self.cursor_prev_pos = self.cursor_pos # No sliding
                    self.main_operation(context)
            if event.value == 'RELEASE':
                self.lmb = False
                if self.drag_mode:
                    self.is_dragging = False
            return {'RUNNING_MODAL'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.Finish(context, props)
            context.area.tag_redraw()
            return {'FINISHED'}

        if event.type == "LEFT_BRACKET":
            props.BrushSize -= 10
            props.BrushSize = max(props.BrushSize, 10)
            self.update_radius(context, props.BrushSize)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == "RIGHT_BRACKET":
            props.BrushSize += 10
            props.BrushSize = min(props.BrushSize, 1000)
            self.update_radius(context, props.BrushSize)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        props = context.scene.NodeRelax_props
        if props.IsRunning:
            return {'CANCELLED'}
        
        self.tree = context.space_data.edit_tree
        context.window_manager.modal_handler_add(self)
        st = bpy.types.SpaceNodeEditor
        self.draw_handler = st.draw_handler_add(draw_callback, (self, context), 'WINDOW', 'POST_VIEW')
        
        self.lmb = False
        props.IsRunning = True
        self.update_cursor_pos(context, event)
        self.update_radius(context, props.BrushSize)
        
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

class NodeRelaxBrushPanel(bpy.types.Panel):
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

#####################################################################################
################## Arrange ##########################################################
        
class NodeRelax_Arrange(bpy.types.Operator):
    """Arrange Nodes"""
    bl_idname = "node_relax.arrange"
    bl_label = "Arrange Nodes"

    bl_options = {"UNDO", "REGISTER"}

    _timer = None

    @classmethod
    def poll(cls, context):
        space = context.space_data
        if space.type == 'NODE_EDITOR' and space.node_tree is not None:
            return True
        return False
        
    def main_routine(self, context):
        yield 1
        nodes = self.tree.nodes
        props = context.scene.NodeRelax_props
        slide = mathutils.Vector((0, 0))

        if not props.ArrangeOnlySelected:
            root_center = mathutils.Vector((0, 0)) # Original Center
            node_cnt = 0
            for node in nodes:
                if node.type == 'FRAME':
                    continue
                root_center += global_loc(node)
                node_cnt += 1
            root_center /= node_cnt

        iter_cnt = 0
        bIters = props.BackgroundIterations

        ########################################################################
        for i in range(props.Iterations_S1):
            new_center = mathutils.Vector((0, 0))
            node_cnt = 0
            changed = False
            for node in nodes:
                if node.type == 'FRAME':
                    continue
                if props.ArrangeOnlySelected and not node.select:
                    continue
                if arrange_relax(node, nodes, 1, 1, props.Distance, False):
                    changed = True
                new_center += global_loc(node)
                node_cnt += 1
            
            if not changed and props.AdaptiveIters:
                break
            if not props.ArrangeOnlySelected:
                new_center /= node_cnt
                slide = root_center - new_center  # Keep Center
                for node in nodes:
                    if node.type == 'FRAME':
                        continue
                    node.location += slide
            iter_cnt += 1
            if iter_cnt > bIters:
                iter_cnt = 0
                props.ArrangeState = str(i) + "/" + str(props.Iterations_S1) + " 1/4"
                yield 1

        ########################################################################
        for i in range(props.Iterations_S2):
            new_center = mathutils.Vector((0, 0))
            node_cnt = 0
            changed = False
            for node in nodes:
                if node.type == 'FRAME':
                    continue
                if props.ArrangeOnlySelected and not node.select:
                    continue
                if arrange_relax(node, nodes, 1, 1, props.Distance, True):
                    changed = True
                new_center += global_loc(node)
                node_cnt += 1

            if not changed and props.AdaptiveIters:
                break
            if not props.ArrangeOnlySelected:
                new_center /= node_cnt
                slide = root_center - new_center  # Keep Center
                for node in nodes:
                    if node.type == 'FRAME':
                        continue
                    node.location += slide
            iter_cnt += 1
            if iter_cnt > bIters:
                iter_cnt = 0
                props.ArrangeState = str(i) + "/" + str(props.Iterations_S2) + " 2/4"
                yield 1

        ########################################################################
        dist = mathutils.Vector((0, props.Distance))
        for i in range(props.Iterations_S3):
            new_center = mathutils.Vector((0, 0))
            node_cnt = 0
            changed = False
            for node in nodes:
                if node.type == 'FRAME':
                    continue
                if props.ArrangeOnlySelected and not node.select:
                    continue
                t = i/props.Iterations_S4  # Growing power
                if calc_collision_y(node, nodes, t, dist):
                    changed = True
                new_center += global_loc(node)
                node_cnt += 1

            if not changed and props.AdaptiveIters:
                break
            if not props.ArrangeOnlySelected:
                new_center /= node_cnt
                slide = root_center - new_center  # Keep Center
                for node in nodes:
                    if node.type == 'FRAME':
                        continue
                    node.location += slide
            iter_cnt += 1
            if iter_cnt > bIters:
                iter_cnt = 0
                props.ArrangeState = str(i) + "/" + str(props.Iterations_S3) + " 3/4"
                yield 1

        ########################################################################
        dist = mathutils.Vector((props.Distance, props.Distance))
        zero_vec = mathutils.Vector((0,0))
        for i in range(props.Iterations_S4):
            new_center = mathutils.Vector((0, 0))
            node_cnt = 0
            changed = False
            for node in nodes:
                if node.type == 'FRAME':
                    continue
                if props.ArrangeOnlySelected and not node.select:
                    continue
                t = i/props.Iterations_S3 # Growing power
                if calc_node(node, nodes, min(1,t*2), zero_vec, 0.2, 1, dist, True):
                    changed = True
                new_center += global_loc(node)
                node_cnt += 1

            if not changed and props.AdaptiveIters:
                break
            if not props.ArrangeOnlySelected:
                new_center /= node_cnt
                slide = root_center - new_center  # Keep Center
                for node in nodes:
                    if node.type == 'FRAME':
                        continue
                    node.location += slide
            iter_cnt += 1
            if iter_cnt > bIters:
                iter_cnt = 0
                props.ArrangeState = str(i) + "/" + str(props.Iterations_S4) + " 4/4"
                yield 1
        ########################################################################
        
        yield 0

    def Finish(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        props = context.scene.NodeRelax_props
        props.ArrangeState = ""

    def modal(self, context, event):
        if event.type == 'TIMER':
            state = next(self.main_coroutine)
            if state == 0:
                self.Finish(context)
                return {'FINISHED'}

        if event.type in {'ESC'}:
            self.Finish(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.tree = context.space_data.edit_tree

        wm = context.window_manager
        self.main_coroutine = self.main_routine(context)
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class NodeRelaxArrangePanel(bpy.types.Panel):
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


class NodeRelaxProps(bpy.types.PropertyGroup):
    #### Brush settings

    IsRunning : bpy.props.BoolProperty(default=False)
    BrushSize : bpy.props.FloatProperty(default=150)
    Distance: bpy.props.FloatProperty(
        name="Distance",
        description="Target distance between nodes",
        default=80)
    RelaxPower : bpy.props.FloatProperty(
        name="Relax power",
        min=0,
        soft_max=0.2,
        max=1,
        default=0.1)
    SlidePower : bpy.props.FloatProperty(
        name="Slide power",
        min=0,
        max=1,
        default=0.6)
    CollisionPower : bpy.props.FloatProperty(
        name="Collision power",
        min=0,
        max=1,
        default=0.9)

    #### Arrange settings

    ArrangeOnlySelected: bpy.props.BoolProperty(
        name="Only Selected",
        default=False)
    Iterations_S1: bpy.props.IntProperty(
        name="Step 1",
        min=0,
        default=200)
    Iterations_S2: bpy.props.IntProperty(
        name="Step 2",
        min=0,
        default=200)
    Iterations_S3: bpy.props.IntProperty(
        name="Step 3",
        min=0,
        default=200)
    Iterations_S4: bpy.props.IntProperty(
        name="Step 4",
        min=0,
        default=200)
    AdaptiveIters: bpy.props.BoolProperty(
        name="Adaptive Iterations",
        default=True)
    BackgroundIterations: bpy.props.IntProperty(
        name="Background Iterations",
        min=0,
        max=10,
        default=2)
    ArrangeState: bpy.props.StringProperty(default="")

addon_keymaps = []

def register():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
        kmi = km.keymap_items.new("node_relax.brush", 'R', 'PRESS', shift = True)

        addon_keymaps.append((km, kmi))

    bpy.utils.register_class(NodeRelax_Brush)
    bpy.utils.register_class(NodeRelaxBrushPanel)
    bpy.utils.register_class(NodeRelax_Arrange)
    bpy.utils.register_class(NodeRelaxArrangePanel)
    bpy.utils.register_class(NodeRelaxProps)

    bpy.types.Scene.NodeRelax_props = bpy.props.PointerProperty(type = NodeRelaxProps)

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(NodeRelax_Brush)
    bpy.utils.unregister_class(NodeRelaxBrushPanel)
    bpy.utils.unregister_class(NodeRelax_Arrange)
    bpy.utils.unregister_class(NodeRelaxArrangePanel)
    bpy.utils.unregister_class(NodeRelaxProps)
    del bpy.types.Scene.NodeRelax_props

if __name__ == "__main__":
    register()
