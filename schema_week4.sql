-- ============================================================
-- KhataAI — Week 4 Schema Update
-- Owner: Aaima
--
-- Run this in Supabase → SQL Editor AFTER schema.sql from Week 3.
-- Adds the pg_cron job for the monthly digest.
--
-- IMPORTANT: Before running, replace the two placeholders:
--   YOUR-RAILWAY-URL → your actual Railway app URL
--   YOUR-CRON-SECRET → same value as CRON_SECRET in your .env
-- ============================================================


-- ============================================================
-- pg_cron: monthly digest — fires on 1st of every month at 4am UTC
-- (9am PKT — a good time, sellers have started their day)
--
-- This calls Younas's /internal/run-digest endpoint which loops
-- through all active users and sends each one the digest message.
-- ============================================================
select cron.schedule(
  'khataai-monthly-digest',
  '0 4 1 * *',
  $$
  select net.http_post(
    url     := 'https://YOUR-RAILWAY-URL.up.railway.app/internal/run-digest',
    headers := '{"x-cron-secret": "YOUR-CRON-SECRET", "Content-Type": "application/json"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);


-- ============================================================
-- Enable pg_net extension (required for http_post in pg_cron)
-- Go to Supabase Dashboard → Database → Extensions → pg_net → Enable
-- Then run this:
-- ============================================================
create extension if not exists pg_net;


-- ============================================================
-- Verify cron jobs are set up correctly
-- Run this query to see all scheduled jobs:
-- ============================================================
-- select jobname, schedule, command from cron.job;
