import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import DashboardForm from "./DashboardForm";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ ig_connected?: string; ig_error?: string }>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: connection } = await supabase
    .from("store_connections")
    .select(
      "shopee_app_id, shopee_store_link, manual_products, ig_business_account_id, ig_username, is_active",
    )
    .eq("user_id", user.id)
    .maybeSingle();

  const params = await searchParams;

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col gap-8 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Painel</h1>
          <p className="text-sm text-black/60 dark:text-white/60">{user.email}</p>
        </div>
        <form action="/api/auth/logout" method="post">
          <button
            type="submit"
            className="text-sm text-black/60 underline dark:text-white/60"
          >
            Sair
          </button>
        </form>
      </div>

      <DashboardForm
        initialShopeeAppId={connection?.shopee_app_id ?? ""}
        initialShopeeStoreLink={connection?.shopee_store_link ?? ""}
        initialManualProducts={
          connection?.manual_products
            ? JSON.stringify(connection.manual_products, null, 2)
            : ""
        }
        igUsername={connection?.ig_username ?? null}
        igConnectedFlag={params.ig_connected === "1"}
        igError={params.ig_error ?? null}
      />
    </main>
  );
}
