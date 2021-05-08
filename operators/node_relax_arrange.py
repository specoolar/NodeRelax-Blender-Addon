import bpy
import mathutils

from .utils import arrange_relax, global_loc, calc_collision_y, calc_node


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
        slide = mathutils.Vector((0, 0))

        if not props.ArrangeOnlySelected:
            root_center = mathutils.Vector((0, 0))  # Original Center
            node_cnt = 0
            for node in nodes:
                if node.type == 'FRAME':
                    continue
                root_center += global_loc(node)
                node_cnt += 1
            root_center /= node_cnt

        iter_cnt = 0
        b_iters = props.BackgroundIterations

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
            if iter_cnt > b_iters:
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
            if iter_cnt > b_iters:
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
                t = i / props.Iterations_S4  # Growing power
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
            if iter_cnt > b_iters:
                iter_cnt = 0
                props.ArrangeState = str(i) + "/" + str(props.Iterations_S3) + " 3/4"
                yield 1

        ########################################################################
        dist = mathutils.Vector((props.Distance, props.Distance))
        zero_vec = mathutils.Vector((0, 0))
        for i in range(props.Iterations_S4):
            new_center = mathutils.Vector((0, 0))
            node_cnt = 0
            changed = False
            for node in nodes:
                if node.type == 'FRAME':
                    continue
                if props.ArrangeOnlySelected and not node.select:
                    continue
                t = i / props.Iterations_S3  # Growing power
                if calc_node(node, nodes, min(1, t * 2), zero_vec, 0.2, 1, dist, True):
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
            if iter_cnt > b_iters:
                iter_cnt = 0
                props.ArrangeState = str(i) + "/" + str(props.Iterations_S4) + " 4/4"
                yield 1
        ########################################################################

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
