from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_reasoning_model: str = "gpt-4o"
    openai_fast_model: str = "gpt-4o-mini"

    tavily_api_key: str = ""
    deep_research_url: str = "http://deep-research:8771"
    deep_research_cycles: int = 1  # 1 cycle = faster for the demo (~25s vs ~60s)
    deep_research_container: str = "gtmagent-deep-research-1"

    apify_token: str = ""
    apify_posts_actor: str = "harvestapi/linkedin-profile-posts"
    apify_profile_actor: str = "dev_fusion/Linkedin-Profile-Scraper"

    composio_api_key: str = ""
    composio_entity_id: str = "default"
    send_mode: str = "draft"  # draft | send | mock
    allowlist_emails: str = ""

    database_url: str = "sqlite:////app/data/gtm.db"
    cors_origins: str = "http://localhost:3000"

    brain_path: str = "/app/data/company_brain.yaml"
    brain_seed_path: str = "/app/company_brain.yaml"  # baked-in defaults from image

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowlist(self) -> list[str]:
        return [e.strip().lower() for e in self.allowlist_emails.split(",") if e.strip()]


settings = Settings()
