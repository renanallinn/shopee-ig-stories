import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { encryptSecret } from "@/lib/crypto";
import {
  exchangeCodeForShortLivedToken,
  exchangeForLongLivedToken,
  fetchInstagramAccount,
  expiresInToDate,
} from "@/lib/instagram";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const errorParam = url.searchParams.get("error_description") ?? url.searchParams.get("error");

  const dashboardUrl = new URL("/dashboard", request.url);

  if (errorParam) {
    dashboardUrl.searchParams.set("ig_error", errorParam);
    return NextResponse.redirect(dashboardUrl);
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const cookieState = request.headers
    .get("cookie")
    ?.split("; ")
    .find((c) => c.startsWith("ig_oauth_state="))
    ?.split("=")[1];

  if (!code || !state || !cookieState || state !== cookieState) {
    dashboardUrl.searchParams.set("ig_error", "Falha na verificação de segurança (state). Tente novamente.");
    return NextResponse.redirect(dashboardUrl);
  }

  try {
    const redirectUri = new URL("/api/instagram/callback", request.url).toString();
    const { access_token: shortLivedToken } = await exchangeCodeForShortLivedToken(code, redirectUri);
    const { access_token: longLivedToken, expires_in: expiresIn } =
      await exchangeForLongLivedToken(shortLivedToken);

    const account = await fetchInstagramAccount(longLivedToken);

    const { error } = await supabase.from("store_connections").upsert(
      {
        user_id: user.id,
        ig_business_account_id: account.id,
        ig_username: account.username,
        ig_access_token_encrypted: encryptSecret(longLivedToken),
        ig_token_expires_at: expiresInToDate(expiresIn).toISOString(),
      },
      { onConflict: "user_id" },
    );

    if (error) {
      dashboardUrl.searchParams.set("ig_error", error.message);
      return NextResponse.redirect(dashboardUrl);
    }

    dashboardUrl.searchParams.set("ig_connected", "1");
    const response = NextResponse.redirect(dashboardUrl);
    response.cookies.delete("ig_oauth_state");
    return response;
  } catch (err) {
    dashboardUrl.searchParams.set(
      "ig_error",
      err instanceof Error ? err.message : "Erro desconhecido ao conectar o Instagram.",
    );
    return NextResponse.redirect(dashboardUrl);
  }
}
