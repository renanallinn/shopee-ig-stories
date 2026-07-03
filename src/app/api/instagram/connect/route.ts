import { NextResponse } from "next/server";
import { randomBytes } from "crypto";
import { createClient } from "@/lib/supabase/server";
import { buildFacebookOAuthUrl } from "@/lib/instagram";

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const state = randomBytes(16).toString("hex");
  const redirectUri = new URL("/api/instagram/callback", request.url).toString();
  const oauthUrl = buildFacebookOAuthUrl(redirectUri, state);

  const response = NextResponse.redirect(oauthUrl);
  // Short-lived CSRF nonce; the callback checks it against this cookie.
  response.cookies.set("ig_oauth_state", state, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 60 * 10,
    path: "/",
  });
  return response;
}
