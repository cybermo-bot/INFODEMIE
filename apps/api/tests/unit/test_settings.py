import pytest
from pydantic import SecretStr, ValidationError

from pnsi.settings import AIMode, AppEnv, IntegrationState, Settings


def make(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


def test_defaults_start_without_any_optional_key():
    settings = make()
    status = settings.integration_status()
    assert status["gemini"] == IntegrationState.NOT_CONFIGURED
    assert status["youtube"] == IntegrationState.NOT_CONFIGURED
    assert status["telegram_client"] == IntegrationState.NOT_CONFIGURED


def test_key_present_marks_integration_configured():
    settings = make(gemini_api_key="abc123", telegram_api_id="1", telegram_api_hash="h4sh")
    status = settings.integration_status()
    assert status["gemini"] == IntegrationState.CONFIGURED
    assert status["telegram_client"] == IntegrationState.CONFIGURED


def test_partial_pair_is_not_configured():
    status = make(reddit_client_id="id-only").integration_status()
    assert status["reddit"] == IntegrationState.NOT_CONFIGURED


def test_local_ai_mode_disables_hosted_models():
    status = make(ai_mode=AIMode.LOCAL, gemini_api_key="abc123").integration_status()
    assert status["gemini"] == IntegrationState.DISABLED
    assert status["groq"] == IntegrationState.DISABLED


def test_empty_env_value_means_not_set(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("AI_DAILY_BUDGET_GROQ_REQUESTS", "")
    settings = make()
    assert settings.gemini_api_key is None
    assert settings.ai_daily_budget_groq_requests is None


def test_example_env_file_loads(tmp_path):
    from pnsi.settings import REPO_ROOT

    settings = Settings(_env_file=REPO_ROOT / ".env.example")
    assert settings.ai_mode == AIMode.HYBRID
    assert settings.default_locale == "fr"


def test_weak_secret_rejected_outside_dev():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make(app_env=AppEnv.DEMO, secret_key="change-me")
    make(app_env=AppEnv.DEMO, secret_key="x" * 40)


def test_auto_publish_cannot_be_enabled():
    with pytest.raises(ValidationError, match="AUTO_PUBLISH_ENABLED"):
        make(auto_publish_enabled=True)


def test_non_postgres_database_rejected():
    with pytest.raises(ValidationError, match="PostgreSQL"):
        make(database_url="sqlite:///x.db")


def test_unsupported_locale_rejected():
    with pytest.raises(ValidationError):
        make(default_locale="it")


def test_secret_values_lists_only_real_secrets():
    settings = make(gemini_api_key="gem-secret-value", secret_key=SecretStr("change-me"))
    assert settings.secret_values() == ["gem-secret-value"]


def test_secure_cookies_default_by_environment():
    assert make(app_env=AppEnv.DEV).secure_cookies is False
    assert make(app_env=AppEnv.PILOT, secret_key="y" * 40).secure_cookies is True
