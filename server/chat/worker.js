export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/v1/health") return Response.json({ ok: true, placeholder: true });
    return Response.json({ error: "not_found", text: "No such address" }, { status: 404 });
  },
};
export class Studio {
  constructor(ctx, env) { this.ctx = ctx; }
  async fetch() { return new Response("placeholder", { status: 503 }); }
}
