-- Schema for the closed-beta multi-tenant Shopee -> Instagram Stories app.
-- Run this in the Supabase SQL editor of your project.

create table if not exists public.store_connections (
  user_id uuid primary key references auth.users (id) on delete cascade,
  shopee_app_id text,
  shopee_app_secret_encrypted text,
  shopee_store_link text,
  manual_products jsonb,
  ig_business_account_id text,
  ig_username text,
  ig_access_token_encrypted text,
  ig_token_expires_at timestamptz,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.posting_state (
  user_id uuid primary key references auth.users (id) on delete cascade,
  last_product_id text,
  last_product_index integer not null default 0,
  last_posted_at timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists public.posts_log (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  product_id text,
  product_name text,
  ig_media_id text,
  status text not null,
  error_message text,
  created_at timestamptz not null default now()
);

alter table public.store_connections enable row level security;
alter table public.posting_state enable row level security;
alter table public.posts_log enable row level security;

-- Users can only ever see/manage their own row.
-- The worker (GitHub Actions) uses the service role key, which bypasses RLS entirely,
-- so it can iterate over every active user.
create policy "select own store_connection" on public.store_connections
  for select using (auth.uid() = user_id);
create policy "insert own store_connection" on public.store_connections
  for insert with check (auth.uid() = user_id);
create policy "update own store_connection" on public.store_connections
  for update using (auth.uid() = user_id);

create policy "select own posting_state" on public.posting_state
  for select using (auth.uid() = user_id);

create policy "select own posts_log" on public.posts_log
  for select using (auth.uid() = user_id);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_store_connections_updated_at on public.store_connections;
create trigger trg_store_connections_updated_at
before update on public.store_connections
for each row execute function public.set_updated_at();

drop trigger if exists trg_posting_state_updated_at on public.posting_state;
create trigger trg_posting_state_updated_at
before update on public.posting_state
for each row execute function public.set_updated_at();
