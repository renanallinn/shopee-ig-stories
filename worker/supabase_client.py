import os

from supabase import Client, create_client


def get_service_client() -> Client:
    """Client authenticated with the service role key — bypasses RLS so the
    worker can read/update every tenant's row. Never expose this key to the
    Next.js frontend; it only belongs in GitHub Actions secrets.
    """
    url = os.environ["SUPABASE_URL"]
    service_role_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, service_role_key)
