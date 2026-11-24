import { BUILD_ID } from '../lib';
// Health + parity endpoint used by CDN probes and the post-deploy parity check.
export const GET = () => new Response(JSON.stringify({ ok: true, build_id: BUILD_ID, built_at: new Date().toISOString() }), { headers: { 'Content-Type': 'application/json' } });
