"""maya_voice - group voice rooms and screen share, through our own server.

The hub's Voice section is `maya_voice.window`. The pure modules (protocol,
jitter, gate, roster, pcm, ws, session) import nothing from Maya or Qt; the
Qt glue is `maya_voice.media`, imported when a device is first opened.

Spec: docs/superpowers/specs/2026-10-10-voice-screen-design.md
"""
