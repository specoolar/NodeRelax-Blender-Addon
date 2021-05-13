import mathutils

MOVE_UNIT = 1


def global_loc(node):
    if node.parent:
        return global_loc(node.parent) + node.location
    else:
        return node.location


def calc_node(node, nodes, influence, slide_vec, relax_power, collide_power, collide_dist, pull_non_siblings):
    if node.type == 'FRAME':
        return False

    loc = global_loc(node)
    size = node.dimensions

    offset = mathutils.Vector(slide_vec)

    if relax_power > 0:
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
            tar_y += size.y / 2
            offset.x += (tar_x - loc.x) * relax_power
            offset.y += (tar_y - loc.y) * relax_power

    if collide_power > 0:
        # Collision
        for other in nodes:
            if other == node:
                continue
            if other.type == 'FRAME':
                continue
            collide(loc, global_loc(other), size, other.dimensions,
                    offset, collide_power, collide_dist)

    if abs(offset.x) > MOVE_UNIT or abs(offset.y) > MOVE_UNIT:
        node.location += offset * influence
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
            return (i / len(sockets_filtered)) * size

        i += 1
    return size / 2


def calc_collision_y(node, nodes, collide_power, collide_dist):
    if node.type == 'FRAME':
        return False

    loc = global_loc(node)
    size = node.dimensions

    offset = mathutils.Vector((0, 0))

    # Collision
    for other in nodes:
        if other == node:
            continue
        if other.type == 'FRAME':
            continue
        collide(loc, global_loc(other), size, other.dimensions,
                offset, 1, collide_dist, True)

    if abs(offset.y) > MOVE_UNIT:
        node.location += offset * collide_power
        return True
    else:
        return False


def arrange_relax(node, influence, relax_power, distance, clamped_pull):
    if node.type == 'FRAME':
        return False

    loc = global_loc(node)
    size = node.dimensions

    offset = mathutils.Vector((0, 0))

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

            tar_y += loc_other.y + socket_pos(socket, node.inputs, size.y) - socket_pos(link.from_socket, other.outputs,
                                                                                        size_other.y)
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

            tar_y += loc_other.y + socket_pos(socket, node.outputs, size.y) - socket_pos(link.to_socket, other.inputs,
                                                                                         size_other.y)
            link_cnt += 1

    if link_cnt > 0:
        if clamped_pull:
            tar_x = tar_x_in * int(has_input) + tar_x_out * int(has_output)
            tar_x /= int(has_input) + int(has_output)
        else:
            tar_x = (tar_x_in + tar_x_out) / link_cnt
        tar_y /= link_cnt
        offset.x += (tar_x - loc.x) * relax_power
        offset.y += (tar_y - loc.y) * relax_power

    if abs(offset.x) > MOVE_UNIT or abs(offset.y) > MOVE_UNIT:
        node.location += offset * influence
        return True
    else:
        return False


def collide(loc0, loc1, size0, size1, offset, power, dist, only_y=False):
    pos0 = loc0 + size0 / 2
    pos1 = loc1 + size1 / 2
    pos0.y -= size0.y
    pos1.y -= size1.y

    size = (size0 + size1) / 2 + dist
    delta = pos1 - pos0
    inters = size - mathutils.Vector((abs(delta.x), abs(delta.y)))

    if inters.x > 0 and inters.y > 0:
        if inters.y < inters.x or only_y:
            if delta.y > 0:
                inters.y *= -1
            offset.y += inters.y / 2 * power
        else:
            if delta.x > 0:
                inters.x *= -1
            offset.x += inters.x / 2 * power