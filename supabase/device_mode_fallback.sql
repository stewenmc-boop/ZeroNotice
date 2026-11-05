-- Optional fallback when Supabase anonymous sign-ins stay disabled.
-- Run this only if Authentication → Anonymous sign-ins cannot be enabled.
--
-- It lets each installation act as itself using a random device key that the
-- app generates locally (data/identity.json) and sends as `x-device-key`.
-- Isolation is then "secret per install" instead of JWT-based; the key is a
-- 128-bit random value and never leaves the machine except in this header.

alter table public.profiles      add column if not exists device_key text;
alter table public.subscriptions add column if not exists device_key text;
alter table public.user_settings add column if not exists device_key text;

create unique index if not exists profiles_device_key_idx
    on public.profiles (device_key) where device_key is not null;
create index if not exists subscriptions_device_key_idx
    on public.subscriptions (device_key);
create unique index if not exists user_settings_device_key_idx
    on public.user_settings (device_key) where device_key is not null;

-- helper: read the header PostgREST exposes to RLS
create or replace function public.current_device_key() returns text as $$
    select nullif(current_setting('request.headers', true)::json ->> 'x-device-key', '')
$$ language sql stable;

drop policy if exists device_rows on public.profiles;
drop policy if exists device_rows on public.subscriptions;
drop policy if exists device_rows on public.user_settings;

create policy device_rows on public.profiles
    for all using (device_key = public.current_device_key())
    with check (device_key = public.current_device_key());

create policy device_rows on public.subscriptions
    for all using (device_key = public.current_device_key())
    with check (device_key = public.current_device_key());

create policy device_rows on public.user_settings
    for all using (device_key = public.current_device_key())
    with check (device_key = public.current_device_key());

alter table public.assistant_messages add column if not exists device_key text;
create index if not exists assistant_messages_device_idx on public.assistant_messages (device_key, created_at desc);
drop policy if exists device_rows on public.assistant_messages;
create policy device_rows on public.assistant_messages
    for all using (device_key = public.current_device_key())
    with check (device_key = public.current_device_key());
