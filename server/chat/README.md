# Skeldar chat server

The server of the in-Maya messenger (spec: docs/superpowers/specs/2026-10-19-chat-messenger-design.md).
It never ships with the plugin.

## Once (the animator)
1. A Cloudflare account (free); open Workers & Pages once and accept the workers.dev subdomain.
2. An API token: Account · Workers Scripts · Edit, Account · Account Settings · Read.
3. `deploy.py keys` in a terminal: paste the token (hidden). It finds the account and keeps both as
   the user variables CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID; deploy.py reads them from there
   too, so no restart is needed.

4. Chat files (2026-10-22) need R2: dashboard -> R2 Object Storage -> enable (free to 10 GB), and the
   token needs Account · Workers R2 Storage · Edit. `deploy.py` makes the bucket on its first run.

## Deploy
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server/chat/deploy.py check
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server/chat/deploy.py staging

## Verify (against staging)
    $env:CHAT_SERVER = '<the URL staging printed>'
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_chat_server.py all
