import httpx

from app.config import settings


class SupabaseRESTClient:
    """
    Async REST client for Supabase using httpx.
    Avoids wrapper library friction and allows full async control.
    """

    def __init__(self):
        self.base_url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.key)

    def get_client(self) -> httpx.AsyncClient:
        if not self.is_configured:
            raise RuntimeError(
                "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY in .env."
            )
        headers = {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
            "Content-Type": "application/json",
        }
        return httpx.AsyncClient(base_url=self.base_url, headers=headers)
