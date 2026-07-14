from app.core.config import Settings


def test_cors_origins_accept_comma_separated_values():
    settings = Settings(cors_origins="http://localhost:5173, https://app.example.com")

    assert settings.cors_origin_list == ["http://localhost:5173", "https://app.example.com"]


def test_cors_origins_accept_json_array_string():
    settings = Settings(cors_origins='["http://localhost:5173","https://app.example.com"]')

    assert settings.cors_origin_list == ["http://localhost:5173", "https://app.example.com"]


def test_default_database_is_local_sqlite():
    settings = Settings()

    assert settings.database_url.startswith("sqlite:///")
