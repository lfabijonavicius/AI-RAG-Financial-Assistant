// Thin proxy to FastAPI /chat — keeps all business logic in the backend.
export async function POST(req: Request) {
  const body = await req.json()
  const upstream = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return new Response(upstream.body, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
  })
}
