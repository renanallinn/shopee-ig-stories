# Shopee Stories

Site onde um afiliado Shopee conecta a própria loja (via Shopee Affiliate Open
API, ou uma lista manual como alternativa) e a própria conta do Instagram, para
publicar Stories automaticamente todos os dias — sem precisar de PC ligado.

Este projeto está na fase **beta fechado** (ver `~/.claude/plans/soft-squishing-turing.md`
para o plano completo): funciona apenas com contas Instagram cadastradas
manualmente como "Instagram Tester" no nosso App da Meta, até passarmos pelo
processo de App Review + Verificação de Negócio necessário para abrir
cadastro público.

## Arquitetura

- **Site** (`src/`) — Next.js + Supabase Auth, hospedado no Vercel. Onde o
  usuário faz login, cola as credenciais da Shopee e conecta o Instagram.
- **Banco de dados** — Supabase (Postgres). Guarda uma linha por usuário em
  `store_connections` (credenciais criptografadas) e `posting_state` (rotação
  de produtos).
- **Worker** (`worker/`) — script Python que roda a cada hora via GitHub
  Actions, iterando por todos os usuários ativos: busca produtos, gera a
  imagem do Story, publica no Instagram, renova tokens quando necessário.

## Limitações importantes (por design)

- **Sem sticker de link clicável**: a API do Instagram não permite anexar um
  link "arraste pra cima" a um Story publicado via API. Cada imagem já inclui
  uma chamada para "link na bio" — o Instagram do usuário precisa ter esse
  link configurado manualmente no perfil.
- **Beta fechado**: só contas adicionadas como "Instagram Tester" no App da
  Meta conseguem concluir a conexão, enquanto não fizermos o App Review
  completo.
- **~24 publicações/dia por usuário** (a cada hora), bem abaixo do limite de
  100/24h da API do Instagram.

## Configuração inicial (passo a passo manual)

### 1. Supabase

1. Crie um projeto gratuito em [supabase.com](https://supabase.com).
2. No SQL Editor do projeto, rode o conteúdo de `supabase/schema.sql`.
3. Em Project Settings → API, copie: `Project URL`, `anon public key` e
   `service_role key` (este último é secreto — só vai para o GitHub Actions,
   nunca para o Vercel/frontend).

### 2. App no Meta for Developers

Usamos o fluxo **"Instagram API with Instagram Login" (Business Login)** — o
usuário autoriza direto com a conta Instagram dele, sem precisar de Página do
Facebook vinculada.

1. Crie um app em [developers.facebook.com/apps](https://developers.facebook.com/apps),
   tipo "Empresa".
2. Em "Adicionar casos de uso", filtre por **"Gerenciamento de conteúdo"** e
   marque **"Gerenciar mensagens e conteúdo no Instagram"**. Não é necessário
   vincular a um portfólio empresarial nessa fase (beta fechado).
3. Clique em "Personalizar o caso de uso 'Gerenciar mensagens e conteúdo no
   Instagram'" (no Painel) → aba **"Configuração da API com login do
   Instagram"**. Copie o **Instagram App ID** e o **Instagram App Secret**
   mostrados ali — são diferentes do App ID principal do app (esse detalhe
   nos custou uma sessão de debug inteira; a API do Instagram exige
   especificamente essas credenciais, não as de "Configurações do app →
   Básico").
4. Ainda nessa tela (ou em **Login do Facebook para Empresas →
   Configurações**), no campo "URIs de redirecionamento do OAuth válidos",
   adicione:
   - `https://SEU-DOMINIO/api/instagram/callback` (produção)
   - `http://localhost:3000/api/instagram/callback` (dev local)
5. **Enquanto o app estiver em modo de desenvolvimento** (antes do App
   Review): vá em Funções do app → Funções, adicione cada beta tester como
   Administrador/Desenvolvedor/Testador do app, com o e-mail da conta Meta
   dela. A pessoa precisa aceitar o convite.
6. A conta Instagram de cada tester precisa ser Business ou Creator (não
   precisa mais de Página do Facebook vinculada).
7. Escopos usados pelo app (já configurados no código):
   `instagram_business_basic`, `instagram_business_content_publish`.

### 3. Variáveis de ambiente do site (Vercel)

Copie `.env.local.example` para `.env.local` e preencha:

- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` — do passo 1.
- `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET` — do passo 2.
- `CREDENTIALS_ENCRYPTION_KEY` — gere com:
  ```bash
  node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
  ```

Configure as mesmas variáveis como Environment Variables no projeto Vercel.

### 4. Secrets do GitHub Actions (worker)

No repositório GitHub, em Settings → Secrets and variables → Actions, crie:

- `SUPABASE_URL` — mesmo valor de `NEXT_PUBLIC_SUPABASE_URL`.
- `SUPABASE_SERVICE_ROLE_KEY` — a `service_role key` do passo 1 (nunca exponha
  essa chave no site).
- `CREDENTIALS_ENCRYPTION_KEY` — mesmo valor gerado no passo 3 (**tem que ser
  idêntico** ao usado no site, senão o worker não consegue descriptografar as
  credenciais salvas).

O repositório precisa ser **público** para que
`raw.githubusercontent.com` sirva as imagens geradas com uma URL que a API do
Instagram consiga acessar (as imagens não contêm nada sensível — só o produto
em destaque).

### 5. Testando

1. Rode o site localmente: `npm run dev`, faça login, cole um App ID/Secret
   da Shopee (ou uma lista manual em `worker/fallback_products.example.json`
   como formato de referência) e clique em "Conectar Instagram" (só funciona
   se sua conta já foi adicionada como Instagram Tester, passo 2.5).
2. No GitHub, rode o workflow manualmente (Actions → Post Instagram Stories →
   Run workflow) com `dry_run: true` — ele gera a imagem e loga o que
   publicaria, sem commitar nem chamar a API do Instagram de verdade.
3. Confira a imagem gerada e os logs do job antes de rodar com `dry_run:
   false` (ou deixar o cron horário automático assumir).

## Observação sobre a API de afiliados da Shopee

A integração em `worker/shopee_client.py` foi construída a partir da
documentação pública disponível (não uma fonte oficial `shopee.com.br`
verificada por mim de ponta a ponta) — confirme os nomes de campos da query
`productOfferV2` contra o que aparecer no seu próprio painel de afiliados
antes de confiar 100% nela em produção. Enquanto isso, use a lista manual de
produtos no dashboard como alternativa confiável.

## Fase 2 (fora do escopo atual)

- Verificação de Negócio + App Review completo da Meta, para permitir
  cadastro público sem convite manual como tester.
- Cobrança/assinatura.
