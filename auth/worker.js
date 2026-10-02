/**
 * GitHub sign-in for the knowledge-graph site.
 *
 * The site is static and served from GitHub Pages. OAuth needs a client secret
 * and a secret cannot live in a page, so this sits beside it and holds the one
 * thing the browser must never see.
 *
 * A sibling of relay/worker.js and deliberately a separate Worker, for the
 * reason given there: a Worker should answer to exactly one set of
 * credentials, and these are two different apps.
 *
 * WHAT THIS DOES NOT DO YET. The read path below is complete: sign in, say who
 * you are, sign out. The write path — filing a resource or a verdict from the
 * site — is specified at the bottom and not implemented, because it turns on a
 * question nobody should answer by guessing. See `docs/sign-in.md`.
 *
 * Nothing here grants anything. A session says which GitHub account is
 * present; whether that account's judgment counts as an author's is decided by
 * the attestation ladder in data/people/, offline, by a person. Sign-in must
 * never become a second route to a rung somebody did not earn.
 */

const SESSION = "aokg_session";
const STATE = "aokg_state";
const SESSION_TTL = 60 * 60 * 8;   // eight hours; a reviewer's sitting, not a month
const STATE_TTL = 60 * 10;

const enc = new TextEncoder();

/** Constant-time compare; a fast exit leaks signature bytes one at a time. */
function equal(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function sign(value, secret) {
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(value));
  return [...new Uint8Array(mac)].map(b => b.toString(16).padStart(2, "0")).join("");
}

/** `payload.expiry.mac`. Signed rather than encrypted: the contents are a
 *  GitHub login and a timestamp, neither of which is a secret. What matters is
 *  that the browser cannot edit them. */
async function seal(payload, ttl, secret) {
  const body = btoa(JSON.stringify(payload)).replace(/=+$/, "");
  const expiry = Math.floor(Date.now() / 1000) + ttl;
  return `${body}.${expiry}.${await sign(`${body}.${expiry}`, secret)}`;
}

async function open(token, secret) {
  const [body, expiry, mac] = (token || "").split(".");
  if (!body || !expiry || !mac) return null;
  if (!equal(mac, await sign(`${body}.${expiry}`, secret))) return null;
  if (Number(expiry) < Date.now() / 1000) return null;   // expiry is inside the MAC
  try { return JSON.parse(atob(body)); } catch { return null; }
}

function cookie(request, name) {
  const jar = request.headers.get("cookie") || "";
  const hit = jar.split(/;\s*/).find(part => part.startsWith(name + "="));
  return hit ? hit.slice(name.length + 1) : null;
}

/** HttpOnly so no script can read it, Secure so it never crosses plain HTTP,
 *  and Lax so a cross-site POST cannot ride on it. */
function setCookie(name, value, maxAge) {
  return `${name}=${value}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=${maxAge}`;
}

/** Exactly one origin, named in config. A wildcard here would let any page
 *  anywhere read a signed-in person's identity. */
function cors(request, env) {
  const origin = request.headers.get("origin");
  if (!origin || origin !== env.SITE_ORIGIN) return {};
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-credentials": "true",
    "vary": "origin",
  };
}

const json = (body, request, env, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...cors(request, env) },
  });

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: {
        ...cors(request, env),
        "access-control-allow-methods": "GET, POST, OPTIONS",
        "access-control-allow-headers": "content-type",
      } });
    }

    // --- start the flow --------------------------------------------------
    if (url.pathname === "/login") {
      // `state` is the CSRF guard: signed here, handed to GitHub, and checked
      // on the way back. Without it, anyone can feed a victim's browser a
      // callback and sign them in as somebody else.
      const nonce = crypto.randomUUID();
      const state = await seal({ nonce }, STATE_TTL, env.SESSION_SECRET);
      const to = new URL("https://github.com/login/oauth/authorize");
      to.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
      to.searchParams.set("redirect_uri", `${url.origin}/callback`);
      // No scope at all. Reading public contribution data needs none, and an
      // unscoped token cannot be turned into a write if this is ever leaked.
      // The write path will need `public_repo` and that is the decision the
      // docs say to make deliberately.
      to.searchParams.set("scope", "");
      to.searchParams.set("state", state);
      return new Response(null, {
        status: 302,
        headers: { location: to.toString(), "set-cookie": setCookie(STATE, state, STATE_TTL) },
      });
    }

    // --- come back from GitHub -------------------------------------------
    if (url.pathname === "/callback") {
      const given = url.searchParams.get("state");
      const held = cookie(request, STATE);
      if (!given || !held || !equal(given, held) || !await open(held, env.SESSION_SECRET)) {
        return new Response("state mismatch", { status: 400 });
      }
      const code = url.searchParams.get("code");
      if (!code) return new Response("no code", { status: 400 });

      const exchanged = await fetch("https://github.com/login/oauth/access_token", {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        body: JSON.stringify({
          client_id: env.GITHUB_CLIENT_ID,
          client_secret: env.GITHUB_CLIENT_SECRET,
          code,
          redirect_uri: `${url.origin}/callback`,
        }),
      }).then(r => r.json());
      if (!exchanged.access_token) return new Response("exchange failed", { status: 502 });

      const who = await fetch("https://api.github.com/user", {
        headers: {
          authorization: `Bearer ${exchanged.access_token}`,
          accept: "application/vnd.github+json",
          "user-agent": "ao-commons-kg",
        },
      }).then(r => r.json());
      if (!who.id) return new Response("could not read the account", { status: 502 });

      // The numeric id is what the session carries. A login can be renamed and
      // GitHub then releases the old one for anybody to claim, so a session
      // keyed on the handle would hand a departed contributor's history to
      // whoever registers it next. The handle rides along for display only.
      //
      // The access token is NOT kept. The read path does not need it, and a
      // token at rest is a liability with no current use.
      const session = await seal(
        { id: who.id, login: who.login, name: who.name || who.login, avatar: who.avatar_url },
        SESSION_TTL, env.SESSION_SECRET);

      return new Response(null, {
        status: 302,
        headers: {
          location: env.SITE_ORIGIN,
          "set-cookie": setCookie(SESSION, session, SESSION_TTL),
        },
      });
    }

    // --- who is here ------------------------------------------------------
    if (url.pathname === "/me") {
      const session = await open(cookie(request, SESSION), env.SESSION_SECRET);
      if (!session) return json({ signed_in: false }, request, env);
      return json({ signed_in: true, ...session }, request, env);
    }

    if (url.pathname === "/logout") {
      return new Response(null, {
        status: 302,
        headers: { location: env.SITE_ORIGIN, "set-cookie": setCookie(SESSION, "", 0) },
      });
    }

    return new Response("not found", { status: 404 });
  },
};

/*
 * THE WRITE PATH, and the question it turns on.
 *
 * Filing a resource or a verdict from the site means writing to the corpus,
 * and there are two ways to do it:
 *
 *   (a) with the signed-in person's own token, so the pull request is genuinely
 *       theirs. Honest attribution, which is the whole point of the
 *       contribution layer — but it needs `public_repo` scope and a user token
 *       held for the length of a session, which is a real liability.
 *
 *   (b) with a bot token, recording who asked. No user token at rest, and the
 *       git history then says the bot did something a person decided. The
 *       corpus already has a worked example of why that is bad: nine claim
 *       relations carried `asserted_by: ankeliu` when a model drafted them,
 *       and correcting it was the point of the confidence class.
 *
 * (a) is right for attribution and (b) is right for security, and the choice
 * belongs to whoever accepts the risk. It is not made here.
 *
 * Whichever is chosen, two things hold. A filing still lands as a pull request
 * and never as a direct commit — `merge_filing.py` and the review path assume
 * it. And signing in must not confer a rung: `by_author` is derived from
 * data/people/, where a person wrote down how they checked, and a session that
 * could set it would make the attestation ladder decorative.
 */
