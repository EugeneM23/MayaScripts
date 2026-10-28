"""Menus whose rows' Python wrappers are dead when exec answers.

Measured 2026-10-28 in the animator's Maya (animBot, AdvancedSkeleton and
OverRig loaded): after a real click on a row, every QAction wrapper the menu's
builder held was dead («Internal C++ object (PySide6.QtGui.QAction) already
deleted») while the menu and its QActions lived, and exec answered the row
through a NEW wrapper. A row found by `picked is row`, or by a dict keyed by
the wrappers, was never found and the press did nothing (the scene tabs' «+»).
`answer_dead` does that to one menu, `dead_rows` to every menu built meanwhile.
"""

import contextlib

import shiboken6
from PySide6.QtWidgets import QMenu      # the real class: dead_rows swaps the module's


def actions_of(menu):
    """Every row of `menu` and of its submenus, depth first. Submenus by the
    menu's children: QAction.menu() hands back a wrapper that dies with the
    temporary it came through, its rows with it (PySide6 6.8, test_atbar_bar)."""
    subs = dict((c.title(), c) for c in menu.children() if isinstance(c, QMenu))
    found = []
    for action in menu.actions():
        found.append(action)
        if action.text() in subs:
            found.extend(actions_of(subs[action.text()]))
    return found


def answer_dead(menu, pick):
    """Every row wrapper of `menu` killed, then the row labelled `pick` (None:
    dismissed) answered through a fresh wrapper, as Maya's exec answered it."""
    for action in actions_of(menu):
        shiboken6.invalidate(action)
    if pick is None:
        return None
    for action in actions_of(menu):
        if action.text() == pick:
            return action
    return None


@contextlib.contextmanager
def dead_rows(holder, pick):
    """`holder.QMenu` (a QtWidgets module, or a stand-in for one) replaced while
    the block runs by a QMenu whose exec answers as `answer_dead` does."""
    real = holder.QMenu

    class DeadRows(real):
        def exec(self, *_args, **_kwargs):                  # noqa: A003
            return answer_dead(self, pick)

    holder.QMenu = DeadRows
    try:
        yield DeadRows
    finally:
        holder.QMenu = real
