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
from .model.node_relax_props import NodeRelaxProps
from .operators.node_relax_arrange import NodeRelaxArrange
from .operators.node_relax_brush import NodeRelaxBrush
from .panels.node_relax_arrange import NodeRelaxArrangePanel
from .panels.node_relax_brush import NodeRelaxBrushPanel

bl_info = {
    "name": "Node Relax",
    "author": "Shahzod Boyhonov (Specoolar)",
    "description": "Tool for arranging nodes easier",
    "blender": (2, 92, 0),
    "version": (1, 0, 0),
    "location": "Node Editor > Properties > Node Relax. Shortcut: Shift R",
    "category": "Node",
}

import bpy

addon_keymaps = []


def register():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
        kmi = km.keymap_items.new("node_relax.brush", 'R', 'PRESS', shift=True)

        addon_keymaps.append((km, kmi))

    bpy.utils.register_class(NodeRelaxBrush)
    bpy.utils.register_class(NodeRelaxBrushPanel)
    bpy.utils.register_class(NodeRelaxArrange)
    bpy.utils.register_class(NodeRelaxArrangePanel)
    bpy.utils.register_class(NodeRelaxProps)

    bpy.types.Scene.NodeRelax_props = bpy.props.PointerProperty(type=NodeRelaxProps)


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(NodeRelaxBrush)
    bpy.utils.unregister_class(NodeRelaxBrushPanel)
    bpy.utils.unregister_class(NodeRelaxArrange)
    bpy.utils.unregister_class(NodeRelaxArrangePanel)
    bpy.utils.unregister_class(NodeRelaxProps)
    del bpy.types.Scene.NodeRelax_props


if __name__ == "__main__":
    register()
