// Helpers for "Instagram API with Instagram Login" (Business Login).
// Docs: https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login
//
// This flow does NOT go through a Facebook Page — the user authorizes
// directly with their Instagram professional account, and everything
// (auth, refresh, publish) happens against graph.instagram.com /
// api.instagram.com with a single Instagram User access token.
//
// GRAPH_API_VERSION drifts every few months when Meta deprecates old
// versions — bump it if calls start failing with a version-deprecated error.
const GRAPH_API_VERSION = "v21.0";

export const INSTAGRAM_OAUTH_SCOPES = [
  "instagram_business_basic",
  "instagram_business_content_publish",
].join(",");

export function buildInstagramOAuthUrl(redirectUri: string, state: string) {
  const url = new URL("https://www.instagram.com/oauth/authorize");
  url.searchParams.set("client_id", process.env.INSTAGRAM_APP_ID!);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("state", state);
  url.searchParams.set("scope", INSTAGRAM_OAUTH_SCOPES);
  url.searchParams.set("response_type", "code");
  return url.toString();
}

async function instagramApiError(res: Response, path: string) {
  const json = await res.json().catch(() => ({}));
  return new Error(`Instagram API error on ${path}: ${json?.error_message ?? json?.error?.message ?? res.statusText}`);
}

// Step 1: exchange the OAuth `code` for a short-lived Instagram User token.
// Note the different host (api.instagram.com) and that this is a POST with a
// form body, unlike the rest of the Graph API calls below.
export async function exchangeCodeForShortLivedToken(code: string, redirectUri: string) {
  const body = new URLSearchParams({
    client_id: process.env.INSTAGRAM_APP_ID!,
    client_secret: process.env.INSTAGRAM_APP_SECRET!,
    grant_type: "authorization_code",
    redirect_uri: redirectUri,
    code,
  });
  const res = await fetch("https://api.instagram.com/oauth/access_token", {
    method: "POST",
    body,
  });
  if (!res.ok) throw await instagramApiError(res, "/oauth/access_token");
  return (await res.json()) as { access_token: string; user_id: number };
}

// Step 2: exchange the short-lived token for a 60-day long-lived one.
export async function exchangeForLongLivedToken(shortLivedToken: string) {
  const url = new URL("https://graph.instagram.com/access_token");
  url.searchParams.set("grant_type", "ig_exchange_token");
  url.searchParams.set("client_secret", process.env.INSTAGRAM_APP_SECRET!);
  url.searchParams.set("access_token", shortLivedToken);
  const res = await fetch(url.toString());
  if (!res.ok) throw await instagramApiError(res, "/access_token");
  return (await res.json()) as { access_token: string; expires_in: number };
}

// Step 3: fetch the connected account's id + username with the new token.
export async function fetchInstagramAccount(accessToken: string) {
  const url = new URL(`https://graph.instagram.com/${GRAPH_API_VERSION}/me`);
  url.searchParams.set("fields", "id,username");
  url.searchParams.set("access_token", accessToken);
  const res = await fetch(url.toString());
  if (!res.ok) throw await instagramApiError(res, "/me");
  return (await res.json()) as { id: string; username: string };
}

export function expiresInToDate(expiresInSeconds: number) {
  return new Date(Date.now() + expiresInSeconds * 1000);
}
