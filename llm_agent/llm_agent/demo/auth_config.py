from __future__ import annotations

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore", env_prefix="DEMO_AUTH_", populate_by_name=True, hide_input_in_errors=True
    )

    enabled: bool = Field(default=False, validation_alias="DEMO_AUTH_ENABLED")
    username: SecretStr | None = Field(default=None, validation_alias="DEMO_AUTH_USERNAME")
    password: SecretStr | None = Field(default=None, validation_alias="DEMO_AUTH_PASSWORD")

    @model_validator(mode="after")
    def require_explicit_credentials(self) -> DemoAuthSettings:
        if self.enabled:
            for secret, limit in ((self.username, 256), (self.password, 1024)):
                if secret is None or not secret.get_secret_value().strip() or len(secret.get_secret_value()) > limit:
                    raise ValueError("Enabled demo authentication requires nonblank, bounded username and password")
        return self
