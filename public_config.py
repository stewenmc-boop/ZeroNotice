"""Publishable defaults so the app works even when env vars are missing.

Supabase URL + anon (publishable) key are safe to ship in a client: row access is
enforced by RLS, and these keys can only read what policies allow. Secrets
(service_role, SMTP auth code, LLM key) are NEVER placed here.
"""

SUPABASE_URL = "https://jfuwxssmutnbdvareugp.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_lCtcsZL3P9ul98lu7PMoeQ_YCJD6RmS"
SUPABASE_BUCKET = "attachments"
