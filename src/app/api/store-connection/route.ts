import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { encryptSecret } from "@/lib/crypto";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Não autenticado" }, { status: 401 });
  }

  const body = await request.json();
  const shopeeAppId = typeof body.shopeeAppId === "string" ? body.shopeeAppId.trim() : "";
  const shopeeAppSecret =
    typeof body.shopeeAppSecret === "string" ? body.shopeeAppSecret.trim() : "";
  const shopeeStoreLink =
    typeof body.shopeeStoreLink === "string" ? body.shopeeStoreLink.trim() : "";
  const manualProductsRaw =
    typeof body.manualProducts === "string" ? body.manualProducts.trim() : "";

  if (!shopeeAppId && !shopeeStoreLink && !manualProductsRaw) {
    return NextResponse.json(
      {
        error:
          "Informe ao menos o App ID da Shopee, o link da loja, ou uma lista manual de produtos.",
      },
      { status: 400 },
    );
  }

  // Leaving the secret or manual-products field blank on an edit means "keep
  // the existing value" — otherwise every save without retyping them would
  // wipe out what was already stored. Paste "[]" to explicitly clear the list.
  let shopeeAppSecretEncrypted: string | null | undefined = undefined;
  let manualProducts: unknown = undefined;

  if (shopeeAppSecret || !manualProductsRaw) {
    const { data: existing } = await supabase
      .from("store_connections")
      .select("shopee_app_secret_encrypted, manual_products")
      .eq("user_id", user.id)
      .maybeSingle();

    shopeeAppSecretEncrypted = shopeeAppSecret
      ? encryptSecret(shopeeAppSecret)
      : (existing?.shopee_app_secret_encrypted ?? null);
    if (!manualProductsRaw) {
      manualProducts = existing?.manual_products ?? null;
    }
  }

  if (manualProductsRaw) {
    try {
      manualProducts = JSON.parse(manualProductsRaw);
      if (!Array.isArray(manualProducts)) {
        throw new Error("not an array");
      }
    } catch {
      return NextResponse.json(
        { error: "A lista manual de produtos precisa ser um JSON válido (array de produtos)." },
        { status: 400 },
      );
    }
  }

  const { error } = await supabase.from("store_connections").upsert(
    {
      user_id: user.id,
      shopee_app_id: shopeeAppId || null,
      shopee_app_secret_encrypted: shopeeAppSecretEncrypted,
      shopee_store_link: shopeeStoreLink || null,
      manual_products: manualProducts,
    },
    { onConflict: "user_id" },
  );

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
