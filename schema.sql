-- ============================================================
-- KhataAI — Week 3 | Supabase Schema
-- Owner: Aaima
--
-- Run this ONCE in Supabase → SQL Editor → New query.
-- It is safe to run multiple times (all statements use IF NOT EXISTS).
-- ============================================================


-- ============================================================
-- Table: users
-- Stores every seller who has messaged the bot.
-- is_active = false until they opt in (Phase 5, Week 5).
-- For Week 3, is_active defaults to true so testing works immediately.
-- ============================================================
create table if not exists users (
  id                   uuid        primary key default gen_random_uuid(),
  phone_number         text        unique not null,
  name                 text,
  is_active            boolean     not null default true,
  daily_message_count  integer     not null default 0,
  last_reset_date      date        not null default current_date,
  created_at           timestamptz not null default now()
);


-- ============================================================
-- Table: beta_users
-- Whitelist of approved beta testers.
-- FIRST CHECK on every incoming message — nothing else runs
-- until the sender's number is found in this table.
-- ============================================================
create table if not exists beta_users (
  id           uuid        primary key default gen_random_uuid(),
  phone_number text        unique not null,
  name         text,
  added_by     text,
  added_at     timestamptz not null default now()
);


-- ============================================================
-- Table: ledger_entries
-- One row per receipt scanned.
-- is_paid = true by default. Set to false via "udhaar" caption keyword.
-- ============================================================
create table if not exists ledger_entries (
  id         uuid        primary key default gen_random_uuid(),
  user_id    uuid        not null references users(id) on delete cascade,
  date       date        not null,
  amount     decimal     not null,
  vendor     text,
  type       text        not null check (type in ('income', 'expense')),
  image_url  text,
  raw_text   text,
  is_paid    boolean     not null default true,
  created_at timestamptz not null default now()
);

-- Index for fast per-user, per-month ledger queries
create index if not exists idx_ledger_user_date
  on ledger_entries(user_id, date);


-- ============================================================
-- Storage: private bucket for permanent receipt images
-- Meta CDN URLs expire — we store our own copy here.
-- ============================================================
insert into storage.buckets (id, name, public)
values ('receipts', 'receipts', false)
on conflict (id) do nothing;


-- ============================================================
-- Row Level Security
-- The backend uses the SERVICE ROLE key which bypasses RLS.
-- These policies protect against any accidental anon-key access.
-- No public read/write policies are intentionally created.
-- ============================================================
alter table users           enable row level security;
alter table beta_users      enable row level security;
alter table ledger_entries  enable row level security;


-- ============================================================
-- RPC: atomic daily count increment
-- Used by Younas's rate_limit.py to avoid race conditions when
-- two messages from the same user arrive at the same time.
-- ============================================================
create or replace function increment_daily_count(target_phone text)
returns void
language plpgsql
as $$
begin
  update users
  set daily_message_count = daily_message_count + 1
  where phone_number = target_phone;
end;
$$;


-- ============================================================
-- pg_cron: daily reset at midnight UTC (5am PKT)
-- Resets every user's daily_message_count back to 0.
-- Requires: Extensions → Enable pg_cron in Supabase dashboard first.
-- ============================================================
create extension if not exists pg_cron;

select cron.schedule(
  'khataai-daily-limit-reset',
  '0 0 * * *',
  $$
    update users
    set daily_message_count = 0,
        last_reset_date      = current_date;
  $$
);


-- ============================================================
-- Seed: add yourself as the first beta user for testing.
-- Replace +92XXXXXXXXXX with your actual WhatsApp number.
-- Add team members here too so everyone can test.
-- ============================================================
insert into beta_users (phone_number, name, added_by)
values
  ('+92XXXXXXXXXX', 'Younas',   'aaima'),
  ('+92XXXXXXXXXX', 'Aaima',    'aaima'),
  ('+92XXXXXXXXXX', 'Muhammad', 'aaima'),
  ('+92XXXXXXXXXX', 'Zain',     'aaima')
on conflict (phone_number) do nothing;
