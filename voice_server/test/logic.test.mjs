// Run with: npm test (Node 18+). Covers the pure rules in src/logic.js.
// The Durable Objects themselves need `wrangler dev`; see README.md.

import { test } from "node:test";
import assert from "node:assert/strict";
import * as L from "../src/logic.js";

test("room names: lowercased, the server's rule, nothing else", () => {
  assert.equal(L.validRoom("Layout-Room"), "layout-room");
  assert.equal(L.validRoom("a_b-9"), "a_b-9");
  for (const bad of ["", "-start", "has/slash", "x".repeat(41), "ünï", "a b"]) {
    assert.equal(L.validRoom(bad), null, bad);
  }
});

test("names: collapsed spaces, capped, never empty", () => {
  assert.equal(L.cleanName("  Eugene   M "), "Eugene M");
  assert.equal(L.cleanName("x".repeat(60)).length, L.NAME_MAX);
  assert.equal(L.cleanName("   "), "Guest");
  assert.equal(L.cleanName(undefined), "Guest");
});

test("free ids: the lowest one nobody holds", () => {
  assert.equal(L.freeId(new Set()), 1);
  assert.equal(L.freeId(new Set([1, 2, 4])), 3);
});

test("media: the sender id is rewritten, the rest is kept", () => {
  const frame = new Uint8Array([0x41, 0, 0, 0, 0, 0, 9, 1, 2, 3]);
  const stamped = L.stampSender(frame.buffer, 0x0102);
  assert.deepEqual(Array.from(stamped), [0x41, 0x01, 0x02, 0, 0, 0, 9, 1, 2, 3]);
  //  the original is not touched
  assert.equal(frame[1], 0);
});

test("media: only audio and video frames are stamped", () => {
  assert.equal(L.stampSender(new Uint8Array([0x58, 0, 0, 0, 0, 0, 0]).buffer, 1), null);
  assert.equal(L.stampSender(new Uint8Array([0x41, 0]).buffer, 1), null);
});

test("control messages: objects with a type, nothing else", () => {
  assert.deepEqual(L.parseControl('{"t":"join","name":"x"}'), { t: "join", name: "x" });
  assert.equal(L.parseControl("[1,2]"), null);
  assert.equal(L.parseControl('{"name":"x"}'), null);
  assert.equal(L.parseControl("not json"), null);
});

test("state: three booleans, whatever else the client sent", () => {
  assert.deepEqual(
    L.cleanState({ muted: 1, deafened: "", sharing: true, name: "evil" }),
    { muted: true, deafened: false, sharing: true },
  );
});

test("the messages the client reads", () => {
  assert.deepEqual(JSON.parse(L.welcomeMessage(4, "lay")), { t: "welcome", id: 4, room: "lay" });
  assert.deepEqual(JSON.parse(L.errorMessage("room full")), { t: "error", msg: "room full" });
  assert.deepEqual(JSON.parse(L.rosterMessage([])), { t: "roster", members: [] });
});

test("lobby: a room with no members leaves the list", () => {
  let rooms = L.lobbyUpdate({}, "lay", ["Eugene"], 1000);
  assert.deepEqual(rooms, { lay: { members: ["Eugene"], updated: 1000 } });
  rooms = L.lobbyUpdate(rooms, "lay", [], 2000);
  assert.deepEqual(rooms, {});
});

test("lobby list: sorted by room, day-old entries dropped", () => {
  const now = 10_000_000_000;
  const rooms = {
    b: { members: ["x"], updated: now },
    a: { members: ["y", "z"], updated: now },
    old: { members: ["q"], updated: now - L.LOBBY_MAX_AGE_MS - 1 },
  };
  assert.deepEqual(L.lobbyList(rooms, now), [
    { room: "a", members: ["y", "z"] },
    { room: "b", members: ["x"] },
  ]);
});
