"""Pure resolution of picker buttons to scene controllers.

The window collects what actually exists -- FK controllers by joint, IK
controls by (limb, role) -- and this module turns it into the two things the
view needs: which buttons are alive, and which scene node each one selects.
Imports nothing outside the stdlib, like bodymap, so it tests in plain Python.
"""

from maya_overrig import bodymap


def resolve(fk_nodes, ik_nodes):
    """Map every resolvable button id to the controller it selects.

    `fk_nodes` is {joint: long path or None}, `ik_nodes` is {(limb, role):
    long path or None}. Buttons whose controller is missing are simply absent
    from the result -- absence is what the view paints as dimmed.
    """
    out = {}
    for button in bodymap.BUTTONS:
        path = fk_nodes.get(button.joint)
        if path:
            out[button.id] = path
    for button in bodymap.IK_BUTTONS:
        path = ik_nodes.get((button.limb, button.role))
        if path:
            out[button.id] = path
    return out


def selected_ids(resolution, selected_paths):
    """Button ids whose controller is in the given selection, in map order.

    Matching is on full DAG paths, never bare names -- another character's
    same-named controller must not light our buttons up.
    """
    found = []
    for button in bodymap.BUTTONS:
        if resolution.get(button.id) in selected_paths:
            found.append(button.id)
    for button in bodymap.IK_BUTTONS:
        if resolution.get(button.id) in selected_paths:
            found.append(button.id)
    return found
