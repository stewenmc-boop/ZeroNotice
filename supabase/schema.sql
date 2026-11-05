-- ZeroNotice · Supabase schema (multi-user, 30-day retention)
-- Run in the Supabase SQL editor.
--
-- Design
--   shared   : notices, notice_fields, notice_images, attachments  (read for everyone)
--   per-user : profiles, subscriptions, user_settings               (RLS: auth.uid())
--
-- Package target (.exe/.dmg) ships only the ANON key and signs each install in
-- anonymously, so one student can never read another student's rows.
-- The sync script (owner machine) uses the service_role key to write shared data.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- shared: announcements
-- ---------------------------------------------------------------------------
create table if not exists public.notices (
    id          text primary key,
    category    text,
    campus      text,
    title_ko    text,
    deadline    timestamptz,
    posted_date date,
    source_url  text,
    payload     jsonb not null,
    verified_at timestamptz,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);
create index if not exists notices_deadline_idx on public.notices (deadline);
create index if not exists notices_posted_idx   on public.notices (posted_date);

create table if not exists public.notice_fields (
    notice_id  text primary key references public.notices(id) on delete cascade,
    payload    jsonb not null,
    engine     text,
    updated_at timestamptz not null default now()
);

create table if not exists public.notice_images (
    notice_id  text primary key references public.notices(id) on delete cascade,
    payload    jsonb not null,
    checked_at timestamptz,
    updated_at timestamptz not null default now()
);

create table if not exists public.attachments (
    id           bigserial primary key,
    notice_id    text references public.notices(id) on delete cascade,
    name         text not null,
    storage_path text not null,
    mime         text,
    bytes        bigint,
    created_at   timestamptz not null default now(),
    unique (notice_id, name)
);

-- ---------------------------------------------------------------------------
-- per-user data
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
    user_id    uuid primary key default auth.uid(),
    payload    jsonb not null,
    email      text,
    student_id text,
    updated_at timestamptz not null default now()
);

create table if not exists public.subscriptions (
    user_id     uuid not null default auth.uid(),
    notice_id   text not null,
    created_at  timestamptz not null default now(),
    reminded_at timestamptz,
    last_ok     boolean,
    primary key (user_id, notice_id)
);

-- AI provider settings per user (key stored as-is; see README warning)
create table if not exists public.user_settings (
    user_id    uuid primary key default auth.uid(),
    payload    jsonb not null,
    updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- triggers
-- ---------------------------------------------------------------------------
create or replace function public.touch_updated_at() returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

do $$
declare t text;
begin
    foreach t in array array['notices', 'notice_fields', 'notice_images', 'profiles', 'user_settings'] loop
        execute format('drop trigger if exists %I_touch on public.%I', t, t);
        execute format('create trigger %I_touch before update on public.%I
                        for each row execute function public.touch_updated_at()', t, t);
    end loop;
end $$;

-- ---------------------------------------------------------------------------
-- 30-day retention for shared notices (cascade removes fields/images/attachments rows)
-- ---------------------------------------------------------------------------
create or replace function public.purge_expired_notices(days int default 30)
returns integer as $$
declare removed integer;
begin
    with gone as (
        delete from public.notices
        where coalesce(posted_date::timestamptz, created_at) < now() - make_interval(days => days)
        returning 1
    )
    select count(*) into removed from gone;
    return removed;
end;
$$ language plpgsql;

-- nightly: needs pg_cron
-- select cron.schedule('zeronotice-purge', '10 3 * * *', $$select public.purge_expired_notices(30)$$);

-- ---------------------------------------------------------------------------
-- storage
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('attachments', 'attachments', true)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- RLS
-- ---------------------------------------------------------------------------
alter table public.notices       enable row level security;
alter table public.notice_fields enable row level security;
alter table public.notice_images enable row level security;
alter table public.attachments   enable row level security;
alter table public.profiles      enable row level security;
alter table public.subscriptions enable row level security;
alter table public.user_settings enable row level security;

do $$
begin
    if not exists (select 1 from pg_policies where tablename = 'notices' and policyname = 'shared_read') then
        create policy shared_read on public.notices       for select using (true);
        create policy shared_read on public.notice_fields for select using (true);
        create policy shared_read on public.notice_images for select using (true);
        create policy shared_read on public.attachments   for select using (true);
    end if;

    if not exists (select 1 from pg_policies where tablename = 'profiles' and policyname = 'own_rows') then
        create policy own_rows on public.profiles      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
        create policy own_rows on public.subscriptions for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
        create policy own_rows on public.user_settings for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
    end if;
end $$;
