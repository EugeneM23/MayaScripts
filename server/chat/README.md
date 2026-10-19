# Skeldar chat server

The server of the in-Maya messenger (spec: docs/superpowers/specs/2026-10-19-chat-messenger-design.md).
It never ships with the plugin.

## Once (the animator)
1. A Cloudflare account (free); open Workers & Pages once and accept the workers.dev subdomain.
2. An API token: Account · Workers Scripts · Edit, Account · Account Settings · Read.
3. User environment variables CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID; restart the Claude app.

## Deploy
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server/chat/deploy.py check
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server/chat/deploy.py staging

## Verify (against staging)
    $env:CHAT_SERVER = '<the URL staging printed>'
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_chat_server.py all
