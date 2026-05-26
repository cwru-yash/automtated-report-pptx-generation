from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class WaveDataProvider(ABC):
    @abstractmethod
    def get_wave_data(self, wave_id: str) -> dict:
        pass

    @abstractmethod
    def get_latest_wave_id(self) -> str:
        pass

def get_provider(config) -> WaveDataProvider:
    provider_type = getattr(config, "WAVE_DATA_PROVIDER", "mock")
    supabase_url = getattr(config, "SUPABASE_URL", "")
    supabase_secret_key = getattr(config, "SUPABASE_SECRET_KEY", "")

    if provider_type == "supabase" and supabase_url and supabase_secret_key:
        logger.info("Selected SupabaseWaveDataProvider (Option A → B fallback)")
        from app.data.supabase_provider import SupabaseWaveDataProvider
        return SupabaseWaveDataProvider(config)
    elif provider_type == "supabase" and not supabase_secret_key:
        logger.warning(
            "WAVE_DATA_PROVIDER=supabase but SUPABASE_SECRET_KEY is not set. "
            "Falling back to MockWaveDataProvider. "
            "Set SUPABASE_SECRET_KEY (service-role key) in .env to use live data."
        )
    elif provider_type != "mock":
        logger.warning("Unknown WAVE_DATA_PROVIDER=%r — falling back to mock.", provider_type)

    logger.info("Selected MockWaveDataProvider")
    from app.data.mock_provider import MockWaveDataProvider
    return MockWaveDataProvider()
