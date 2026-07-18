-- ============================================================
-- KhataAI — Week 4 Schema Additions
-- Owner: Aaima
--
-- Run this in Supabase SQL Editor AFTER schema.sql from Week 3.
-- All statements are safe to run multiple times.
-- ============================================================


-- ============================================================
-- RPC: get active users for monthly digest
-- Used by Younas's digest_trigger.py to find who gets the digest.
-- "Active" = at least one ledger entry in the past 30 days.
-- ============================================================
create or replace function get_active_users_for_digest()
returns table(id uuid, phone_number text)
language plpgsql
as $$
begin
  return query
    select distinct u.id, u.phone_number
    from users u
    inner join ledger_entries le on le.user_id = u.id
    where u.is_active = true
      and le.created_at >= now() - interval '30 days';
end;
$$;


-- ============================================================
-- pg_cron: monthly digest on 1st of every month at 4am UTC (9am PKT)
--
-- BEFORE enabling: replace the two placeholders below:
--   YOUR-RAILWAY-URL -> your actual Railway app URL
--   YOUR-CRON-SECRET -> same value as CRON_SECRET in your .env
--
-- Run this AFTER deploying to Railway so you have the real URL.
-- ============================================================
select cron.schedule(
  'khataai-monthly-digest',
  '0 4 1 * *',
  $$
  select net.http_post(
    url     := 'https://YOUR-RAILWAY-URL.up.railway.app/internal/run-digest',
    headers := '{"Content-Type": "application/json", "x-cron-secret": "YOUR-CRON-SECRET"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);
