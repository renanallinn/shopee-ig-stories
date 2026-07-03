// Helpers for the "Instagram API with Facebook Login" OAuth flow.
// Docs: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/get-started
//
// GRAPH_API_VERSION drifts every few months when Meta deprecates old
// versions — bump it if calls start failing with a version-deprecated error.
const GRAPH_API_VERSION = "v21.0";
const GRAPH_BASE = `https://graph.facebook.com/${GRAPH_API_VERSION}`;

export const INSTAGRAM_OAUTH_SCOPES = [
  "instagram_basic",
  "instagram_content_publish",
  "pages_show_list",
  "pages_read_engagement",
  "business_management",
].join(",");

export function buildFacebookOAuthUrl(redirectUri: string, state: string) {
  const url = new URL(`https://www.facebook.com/${GRAPH_API_VERSION}/dialog/oauth`);
  url.searchParams.set("client_id", process.env.FACEBOOK_APP_ID!);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("state", state);
  url.searchParams.set("scope", INSTAGRAM_OAUTH_SCOPES);
  url.searchParams.set("response_type", "code");
  return url.toString();
}

async function graphGet<T>(path: string, params: Record<string, string>) {
  const url = new URL(`${GRAPH_BASE}${path}`);
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
  const res = await fetch(url.toString());
  const json = await res.json();
  if (!res.ok) {
    throw new Error(
      `Graph API error on ${path}: ${json?.error?.message ?? res.statusText}`,
    );
  }
  return json as T;
}

export async function exchangeCodeForUserToken(code: string, redirectUri: string) {
  const data = await graphGet<{ access_token: string }>("/oauth/access_token", {
    client_id: process.env.FACEBOOK_APP_ID!,
    client_secret: process.env.FACEBOOK_APP_SECRET!,
    redirect_uri: redirectUri,
    code,
  });
  return data.access_token;
}

export async function exchangeForLongLivedUserToken(shortLivedToken: string) {
  const data = await graphGet<{ access_token: string; expires_in: number }>(
    "/oauth/access_token",
    {
      grant_type: "fb_exchange_token",
      client_id: process.env.FACEBOOK_APP_ID!,
      client_secret: process.env.FACEBOOK_APP_SECRET!,
      fb_exchange_token: shortLivedToken,
    },
  );
  return data;
}

interface FacebookPage {
  id: string;
  access_token: string;
  instagram_business_account?: { id: string };
}

// Finds the first Facebook Page (belonging to the authorizing user) that has
// an Instagram Business/Creator account linked to it. MVP simplification:
// if someone manages multiple pages, only the first linked one is used.
export async function findLinkedInstagramAccount(longLivedUserToken: string) {
  const { data: pages } = await graphGet<{ data: FacebookPage[] }>("/me/accounts", {
    access_token: longLivedUserToken,
    fields: "id,access_token,instagram_business_account",
  });

  const pageWithIg = pages.find((page) => page.instagram_business_account?.id);
  if (!pageWithIg?.instagram_business_account) {
    return null;
  }

  const igAccount = await graphGet<{ id: string; username: string }>(
    `/${pageWithIg.instagram_business_account.id}`,
    { access_token: pageWithIg.access_token, fields: "id,username" },
  );

  return {
    igBusinessAccountId: igAccount.id,
    igUsername: igAccount.username,
    // Publishing calls use the Page access token, not the user token.
    pageAccessToken: pageWithIg.access_token,
  };
}

// Long-lived Page access tokens derived this way don't have a fixed expiry
// while the underlying user token is valid, but we still track an
// expires_at (~60 days out) so the worker knows when to prompt for
// re-connection if it ever does go stale.
export function sixtyDaysFromNow() {
  return new Date(Date.now() + 60 * 24 * 60 * 60 * 1000);
}
