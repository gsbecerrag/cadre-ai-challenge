"""Configuration loading and fail-fast behaviour — seam S2."""

import pytest

from core.config import REQUIRED_VARIABLES, MissingConfigurationError, load_settings


def test_settings_fall_back_to_the_documented_defaults(
    clean_environment: pytest.MonkeyPatch,
) -> None:
    settings = load_settings()

    assert settings.env == "development"
    assert settings.port == 8080
    assert settings.loglevel == "INFO"
    assert settings.service_name == "cadre-support-agent"
    assert settings.app_version == "0.1.0"


def test_settings_are_read_from_the_environment_and_typed(
    clean_environment: pytest.MonkeyPatch,
) -> None:
    clean_environment.setenv("ENV", "production")
    clean_environment.setenv("PORT", "9090")
    clean_environment.setenv("LOGLEVEL", "DEBUG")
    clean_environment.setenv("APP_VERSION", "abc1234")

    settings = load_settings()

    assert settings.env == "production"
    assert settings.port == 9090
    assert settings.loglevel == "DEBUG"
    assert settings.app_version == "abc1234"


def test_an_unknown_log_level_is_rejected(clean_environment: pytest.MonkeyPatch) -> None:
    clean_environment.setenv("LOGLEVEL", "CHATTY")

    with pytest.raises(ValueError):
        load_settings()


def test_nothing_is_required_yet(clean_environment: pytest.MonkeyPatch) -> None:
    assert REQUIRED_VARIABLES == ()


def test_a_missing_required_variable_fails_fast_with_a_clear_message(
    clean_environment: pytest.MonkeyPatch,
) -> None:
    clean_environment.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(MissingConfigurationError) as failure:
        load_settings(required=("OPENROUTER_API_KEY",))

    message = str(failure.value)
    assert "OPENROUTER_API_KEY" in message
    assert ".env.example" in message


def test_a_blank_required_variable_counts_as_missing(
    clean_environment: pytest.MonkeyPatch,
) -> None:
    clean_environment.setenv("OPENROUTER_API_KEY", "   ")

    with pytest.raises(MissingConfigurationError):
        load_settings(required=("OPENROUTER_API_KEY",))


def test_a_present_required_variable_loads(clean_environment: pytest.MonkeyPatch) -> None:
    clean_environment.setenv("OPENROUTER_API_KEY", "sk-or-not-a-real-key")

    settings = load_settings(required=("OPENROUTER_API_KEY",))

    assert settings.service_name == "cadre-support-agent"
