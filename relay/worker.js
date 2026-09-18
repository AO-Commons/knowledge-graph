/**
 * Slack → GitHub Actions relay, for the knowledge-graph agent.
 *
 * Slack needs an HTTPS endpoint that answers within three seconds. GitHub
 * Actions cannot be one. This sits between them: it verifies the request is
 * genuinely from Slack, answers immediately, and fires a repository_dispatch
 * in the background.
 *
 * It holds no Slack or Anthropic credentials and forwards no message text. The
 * payload carries a channel and two timestamps — where to look — and the
 * Actions run reads the thread itself with the token it already has. A relay
 * that carried the question would be a second place the question exists, and
 * the reason to avoid that is not privacy so much as truth: the run would be
 * answering a copy, and a copy can be stale or edited.
 *
 * A sibling of AO-Commons/slack-agents' relay, and deliberately a separate
 * Worker rather than another route on it. A Worker verifies against exactly
 * one signing secret, and these are two Slack apps.
 */

const enc = new TextEncoder();

/** Constant-time string compare; a fast exit leaks signature bytes. */
function equal(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

/** Slack's v0 signing scheme, plus the replay window it requires. */
async function fromSlack(request, body, secret) {
  const ts = request.headers.get("x-slack-request-timestamp");
  const sig = request.headers.get("x-slack-signature");
  if (!ts || !sig || !secret) return false;
  if (Math.abs(Date.now() / 1000 - Number(ts)) > 300) return false;   // replay

  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(`v0:${ts}:${body}`));
  const expected = "v0=" + [...new Uint8Array(mac)].map((b) => b.toString(16).padStart(2, "0")).join("");
  return equal(expected, sig);
}

async function dispatch(env, payload) {
  const res = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "aokg-slack-relay",
    },
    body: JSON.stringify({ event_type: "slack-mention", client_payload: payload }),
  });
  if (!res.ok) console.log(`dispatch failed: ${res.status} ${await res.text()}`);
}

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") {
      // Something other than Slack, or somebody checking the URL is alive.
      return new Response("this endpoint takes Slack events", { status: 405 });
    }

    const body = await request.text();

    // Say which kind of 401 this is. Without the secret every request is
    // rejected — including the url_verification challenge, so Slack cannot
    // even save the Request URL — and the tail is silent, which looks exactly
    // like Slack not delivering. Two very different problems, one symptom.
    if (!env.SLACK_SIGNING_SECRET) {
      console.log(
        "SLACK_SIGNING_SECRET is not set, so every Slack request is rejected " +
        "including the challenge. Run: npx wrangler secret put SLACK_SIGNING_SECRET");
      return new Response("relay has no signing secret", { status: 401 });
    }
    if (!(await fromSlack(request, body, env.SLACK_SIGNING_SECRET))) {
      console.log("signature did not verify — wrong signing secret, or not from Slack");
      return new Response("bad signature", { status: 401 });
    }

    let payload;
    try { payload = JSON.parse(body); } catch { return new Response("bad json", { status: 400 }); }

    // Slack proves it owns the endpoint by asking us to echo a challenge. This
    // has to work before the signing secret is ever exercised in anger, which
    // is why a wrong secret shows up as "didn't respond with the challenge".
    if (payload.type === "url_verification") {
      return new Response(payload.challenge, { headers: { "content-type": "text/plain" } });
    }

    const e = payload.event;

    // Only a mention, and never our own. A bot that answers itself in a thread
    // it is already in will do so until somebody notices.
    const worthWaking =
      e?.type === "app_mention" &&
      !e.bot_id &&
      e.user &&
      (!env.CHANNELS || env.CHANNELS.split(",").map((c) => c.trim()).includes(e.channel));

    // Answer first: Slack retries anything slower than three seconds, and a
    // retry would wake Actions twice for one question.
    // A mention that wakes nothing is the other silent failure: the event
    // arrived and was dropped, which reads identically to never arriving.
    if (!worthWaking && e?.type === "app_mention") {
      console.log(`ignored an app_mention in ${e.channel} — not in CHANNELS ` +
                  `(${env.CHANNELS ?? "unset"}). Add the id to wrangler.toml and redeploy.`);
    }
    if (worthWaking) {
      ctx.waitUntil(dispatch(env, {
        channel: e.channel,
        ts: e.ts,
        thread_ts: e.thread_ts ?? "",
      }));
    }
    return new Response("", { status: 200 });
  },
};
