"""The hub card of the chat (Scene): one line and Open Chat - the messenger is its own window.

On the rail a press on the icon opens the window itself (maya_hub.WINDOW_SECTIONS); this card
is what the accordion and the classic hub show.
"""
from maya import cmds

HUB_SECTION = "chat"
NOTE_NAME = "skeldarChatNote"
OPEN_BUTTON = "skeldarChatOpen"
NOTE = "Сообщения коллегам: личные чаты и группы, прямо в Maya"


def build_panel():
    import maya_hubstyle as hubstyle
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(NOTE_NAME, label=NOTE, align="left"), "note")
    hubstyle.mark(cmds.button(OPEN_BUTTON, label="Open Chat",
                              height=hubstyle.height("button", 34),
                              annotation="The messenger's window: chats, friends, groups",
                              command=lambda *_a: open_window()),
                  "primary", "message-circle")
    cmds.setParent("..")
    return column


def open_window():
    import maya_chat
    return maya_chat.show()
