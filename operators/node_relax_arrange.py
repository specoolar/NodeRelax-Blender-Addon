import bpy
import mathutils

from .utils import arrange_relax, global_loc, calc_collision_y, calc_node


def step(step_num, iter_num, nodes, props, root_center, iter_func):
    iter_cnt = 0
    for i in range(iter_num):
        new_center = mathutils.Vector((0, 0))
        node_cnt = 0
        changed = False
        for node in nodes:
            if node.type == 'FRAME':
                continue
            if props.ArrangeOnlySelected and not node.select:
                continue
            t = i / iter_num
            if iter_func(node, t):
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
        if iter_cnt > props.BackgroundIterations:
            iter_cnt = 0
            props.ArrangeState = str(i) + "/" + str(iter_num) + " " + str(step_num) + "/4"
            yield 1


class NodeRelaxArrange(bpy.types.Operator):
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
        root_center = mathutils.Vector((0, 0))  # Original Center

        if not props.ArrangeOnlySelected:
            node_cnt = 0
            for node in nodes:
                if node.type == 'FRAME':
                    continue
                root_center += global_loc(node)
                node_cnt += 1
            root_center /= node_cnt

        yield from step(1, props.Iterations_S1, nodes, props, root_center,
                        lambda curr_node, e: arrange_relax(curr_node, 1, 1, props.Distance, False))

        yield from step(2, props.Iterations_S2, nodes, props, root_center,
                        lambda curr_node, e: arrange_relax(curr_node, 1, 1, props.Distance, True))

        dist = mathutils.Vector((0, props.Distance))
        yield from step(3, props.Iterations_S3, nodes, props, root_center,
                        lambda curr_node, e: calc_collision_y(curr_node, nodes, e, dist))

        dist = mathutils.Vector((props.Distance, props.Distance))
        zero_vec = mathutils.Vector((0, 0))
        yield from step(4, props.Iterations_S4, nodes, props, root_center,
                        lambda curr_node, e: calc_node(curr_node, nodes, min(1, e * 2), zero_vec, 0.2, 1, dist, True))

        yield 0

    def finish(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        props = context.scene.NodeRelax_props
        props.ArrangeState = ""

    def modal(self, context, event):
        if event.type == 'TIMER':
            state = next(self.main_coroutine)
            if state == 0:
                self.finish(context)
                return {'FINISHED'}

        if event.type in {'ESC'}:
            self.finish(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.tree = context.space_data.edit_tree

        wm = context.window_manager
        self.main_coroutine = self.main_routine(context)
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}
