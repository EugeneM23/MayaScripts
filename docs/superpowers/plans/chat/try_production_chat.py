"""A throwaway colleague on the production chat, run by the animator.

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/chat/try_production_chat.py eugene

It registers a test account (tester_<random>), asks <nick> to be friends, waits up to 10 minutes for the
accept, sends three messages a few seconds apart (collapse the chat window to see the cards over the
Time Bar), waits for a reply for a minute and prints it, then deletes the test account. The token lives
in memory only.
"""
import os
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "SkeldarAnim"))]

import wsclient  # noqa: E402
from maya_chat import SERVER  # noqa: E402
from maya_chat import api as A  # noqa: E402

TEXTS = [
    "Привет! Это тестовый коллега на боевом сервере.",
    "Если чат свёрнут - эта карточка слева над таймслайдером.",
    "Ответь что-нибудь, я прочитаю и удалюсь.",
]


def main(target):
    nick = "tester_" + uuid.uuid4().hex[:6]
    doc = A.Api(SERVER).register(nick)
    token = doc["token"]
    api = A.Api(SERVER, token)
    print("registered @%s on %s" % (nick, SERVER))
    try:
        api.request(target)
        print("friend request sent to @%s - accept it in the chat (Friends)" % target)
        deadline = time.time() + 600
        friend = None
        while time.time() < deadline:
            found = [u for u in api.friends()["friends"] if u["nick"] == target]
            if found:
                friend = found[0]
                break
            time.sleep(3)
        if friend is None:
            print("not accepted in 10 minutes")
            return
        chat = api.dm(friend["id"])
        ws = wsclient.WS(SERVER.replace("https://", "wss://") + "/v1/ws", token)
        try:
            ws.send({"type": "hello", "since": 0})
            ws.until(lambda e: e.get("kind") == "caught_up", 15)
            for text in TEXTS:
                ws.send({"type": "send", "chat": chat["id"], "cid": uuid.uuid4().hex, "text": text})
                ack, _ = ws.until(lambda e: e.get("kind") in ("ack", "error"), 15)
                print("sent:", text, "->", (ack or {}).get("kind"))
                time.sleep(4)
            print("waiting a minute for a reply...")
            got, _ = ws.until(lambda e: e.get("kind") == "message"
                              and (e.get("message") or {}).get("from_id") == friend["id"], 60)
            if got:
                print("reply:", got["message"].get("text"))
            else:
                print("no reply in a minute")
        finally:
            ws.close()
    finally:
        api.delete_me()
        print("test account @%s deleted" % nick)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "eugene")
