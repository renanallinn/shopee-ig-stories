"use client";

import { useState } from "react";

interface Props {
  initialShopeeAppId: string;
  initialShopeeStoreLink: string;
  initialManualProducts: string;
  igUsername: string | null;
  igConnectedFlag: boolean;
  igError: string | null;
}

export default function DashboardForm({
  initialShopeeAppId,
  initialShopeeStoreLink,
  initialManualProducts,
  igUsername,
  igConnectedFlag,
  igError,
}: Props) {
  const [shopeeAppId, setShopeeAppId] = useState(initialShopeeAppId);
  const [shopeeAppSecret, setShopeeAppSecret] = useState("");
  const [shopeeStoreLink, setShopeeStoreLink] = useState(initialShopeeStoreLink);
  const [manualProducts, setManualProducts] = useState(initialManualProducts);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    const res = await fetch("/api/store-connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shopeeAppId, shopeeAppSecret, shopeeStoreLink, manualProducts }),
    });
    const json = await res.json();
    setSaving(false);
    setMessage(res.ok ? "Salvo com sucesso." : json.error ?? "Erro ao salvar.");
    if (res.ok) setShopeeAppSecret("");
  }

  return (
    <div className="flex flex-col gap-10">
      <section className="flex flex-col gap-4">
        <h2 className="font-medium">1. Sua loja Shopee (afiliado)</h2>
        <p className="text-sm text-black/60 dark:text-white/60">
          Se você já tem acesso à Shopee Affiliate Open API, informe o App ID e o App
          Secret do seu painel de afiliados. Se ainda não tiver, cole o link da sua
          loja/afiliado como alternativa temporária.
        </p>
        <form onSubmit={handleSave} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="shopeeAppId" className="text-sm font-medium">
              Shopee App ID
            </label>
            <input
              id="shopeeAppId"
              value={shopeeAppId}
              onChange={(e) => setShopeeAppId(e.target.value)}
              className="rounded border border-black/10 px-3 py-2 dark:border-white/20"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="shopeeAppSecret" className="text-sm font-medium">
              Shopee App Secret
            </label>
            <input
              id="shopeeAppSecret"
              type="password"
              value={shopeeAppSecret}
              onChange={(e) => setShopeeAppSecret(e.target.value)}
              placeholder={initialShopeeAppId ? "Deixe em branco para manter o atual" : ""}
              className="rounded border border-black/10 px-3 py-2 dark:border-white/20"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="shopeeStoreLink" className="text-sm font-medium">
              Link da loja/afiliado (alternativa)
            </label>
            <input
              id="shopeeStoreLink"
              value={shopeeStoreLink}
              onChange={(e) => setShopeeStoreLink(e.target.value)}
              placeholder="https://shopee.com.br/..."
              className="rounded border border-black/10 px-3 py-2 dark:border-white/20"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="manualProducts" className="text-sm font-medium">
              Lista manual de produtos (fallback, formato JSON)
            </label>
            <p className="text-xs text-black/50 dark:text-white/50">
              Use isso enquanto não tiver acesso à API de afiliados da Shopee. Cole um
              array JSON com nome, preço, imagem e link de afiliado de cada produto.
            </p>
            <textarea
              id="manualProducts"
              value={manualProducts}
              onChange={(e) => setManualProducts(e.target.value)}
              rows={6}
              placeholder='[{"id":"1","name":"...","price":"R$ 49,90","image_url":"https://...","affiliate_link":"https://..."}]'
              className="rounded border border-black/10 px-3 py-2 font-mono text-xs dark:border-white/20"
            />
          </div>

          {message && <p className="text-sm">{message}</p>}

          <button
            type="submit"
            disabled={saving}
            className="self-start rounded bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-50"
          >
            {saving ? "Salvando..." : "Salvar"}
          </button>
        </form>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="font-medium">2. Conectar Instagram</h2>

        {igConnectedFlag && (
          <p className="text-sm text-green-600 dark:text-green-400">
            Instagram conectado com sucesso.
          </p>
        )}
        {igError && (
          <p className="text-sm text-red-600 dark:text-red-400">{igError}</p>
        )}

        {igUsername ? (
          <p className="text-sm">
            Conectado como <strong>@{igUsername}</strong>.
          </p>
        ) : (
          <p className="text-sm text-black/60 dark:text-white/60">
            Nenhuma conta conectada ainda. Durante o beta fechado, sua conta precisa
            ter sido adicionada como &quot;Instagram Tester&quot; no nosso App da Meta antes
            de conseguir concluir essa etapa.
          </p>
        )}

        <a
          href="/api/instagram/connect"
          className="self-start rounded border border-black/20 px-4 py-2 text-sm font-medium dark:border-white/30"
        >
          {igUsername ? "Reconectar Instagram" : "Conectar Instagram"}
        </a>
      </section>
    </div>
  );
}
