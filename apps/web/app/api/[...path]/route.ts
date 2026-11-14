import { NextRequest } from "next/server";
const allowed = /^(summary|optimizations(?:\/[a-f0-9-]+(?:\/(?:cancel|report|events|candidates|plans|benchmarks))?)?|workloads(?:\/[a-z_]+)?|health|readiness|experiments(?:\/[a-f0-9-]+)?)$/;
async function forward(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const {path} = await context.params;
  const route = path.join("/");
  if (!allowed.test(route)) return Response.json({error:"Unknown API route"}, {status:404});
  // Reject cross-origin writes before adding server-side credentials.
  const origin = request.headers.get("origin");
  if (request.method === "POST" && origin && origin !== request.nextUrl.origin) return Response.json({error:"Origin rejected"}, {status:403});
  const body = request.method === "POST" ? await request.text() : undefined;
  if (body && Buffer.byteLength(body) > 24000) return Response.json({error:"Request too large"}, {status:413});
  try {
    const headers: Record<string,string> = {"Content-Type":"application/json"};
    if (request.headers.get("authorization")) headers.Authorization = request.headers.get("authorization")!;
    const upstream = await fetch(`${process.env.API_INTERNAL_URL || "http://localhost:8000"}/api/v1/${route}${request.nextUrl.search}`, {method:request.method, headers, body, cache:"no-store", signal:AbortSignal.timeout(10000)});
    return new Response(await upstream.text(), {status:upstream.status, headers:{"Content-Type":"application/json", "Cache-Control":"no-store"}});
  } catch { return Response.json({error:"API unavailable. Check the API and database services."}, {status:503}); }
}
export const GET = forward;
export const POST = forward;
