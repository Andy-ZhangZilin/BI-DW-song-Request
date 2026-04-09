"""Story 1.2 单元测试：凭证管理器 get_credentials() 和 mask_credential()"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ── 辅助：构造完整测试环境变量 ──────────────────────────────────────────
ALL_VALID_ENV = {
    "TRIPLEWHALE_API_KEY": "tw_key_123",
    "TIKTOK_APP_KEY": "tiktok_app_key",
    "TIKTOK_APP_SECRET": "tiktok_app_secret",
    "DINGTALK_APP_KEY": "dingtalk_app_key",
    "DINGTALK_APP_SECRET": "dingtalk_app_secret",
    "DINGTALK_WORKBOOK_ID": "test_workbook_id",
    "YOUTUBE_API_KEY": "youtube_key_xyz",
    "AWIN_API_TOKEN": "test_awin_api_token",
    "AWIN_ADVERTISER_ID": "89509",
    "CARTSEE_USERNAME": "cartsee@example.com",
    "CARTSEE_PASSWORD": "cartsee_pass",
    "PARTNERBOOST_USERNAME": "pb@example.com",
    "PARTNERBOOST_PASSWORD": "pb_pass",
    "FACEBOOK_USERNAME": "fb@example.com",
    "FACEBOOK_PASSWORD": "fb_pass",
    "YOUTUBE_STUDIO_EMAIL": "yt_studio@example.com",
    "YOUTUBE_STUDIO_PASSWORD": "yt_studio_pass",
}


class TestGetCredentialsSuccess:
    """AC #1：全量凭证存在时正确返回字典"""

    def test_returns_dict_when_all_keys_present(self, monkeypatch):
        for key, val in ALL_VALID_ENV.items():
            monkeypatch.setenv(key, val)
        with patch("config.credentials.load_dotenv", MagicMock()):
            from config.credentials import get_credentials
            result = get_credentials()
        assert isinstance(result, dict)

    def test_all_13_keys_present_in_result(self, monkeypatch):
        for key, val in ALL_VALID_ENV.items():
            monkeypatch.setenv(key, val)
        with patch("config.credentials.load_dotenv", MagicMock()):
            from config.credentials import get_credentials, _REQUIRED_KEYS
            result = get_credentials()
        assert set(result.keys()) == set(_REQUIRED_KEYS)

    def test_values_match_env(self, monkeypatch):
        for key, val in ALL_VALID_ENV.items():
            monkeypatch.setenv(key, val)
        with patch("config.credentials.load_dotenv", MagicMock()):
            from config.credentials import get_credentials
            result = get_credentials()
        assert result["TRIPLEWHALE_API_KEY"] == "tw_key_123"
        assert result["YOUTUBE_API_KEY"] == "youtube_key_xyz"


class TestGetCredentialsMissing:
    """AC #2：缺少凭证时抛出 ValueError 并列出缺失键名"""

    def test_single_missing_key_raises_value_error(self, monkeypatch):
        env = dict(ALL_VALID_ENV)
        env.pop("TRIPLEWHALE_API_KEY")
        for key, val in env.items():
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("TRIPLEWHALE_API_KEY", raising=False)
        with patch("config.credentials.load_dotenv", MagicMock()):
            from config.credentials import get_credentials
            with pytest.raises(ValueError):
                get_credentials()

    def test_error_message_contains_missing_key_name(self, monkeypatch):
        env = dict(ALL_VALID_ENV)
        env.pop("YOUTUBE_API_KEY")
        for key, val in env.items():
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        with patch("config.credentials.load_dotenv", MagicMock()):
            from config.credentials import get_credentials
            with pytest.raises(ValueError, match="YOUTUBE_API_KEY"):
                get_credentials()

    def test_multiple_missing_keys_all_listed_in_error(self, monkeypatch):
        missing_keys = ["TRIPLEWHALE_API_KEY", "TIKTOK_APP_KEY", "YOUTUBE_API_KEY"]
        for key in missing_keys:
            monkeypatch.delenv(key, raising=False)
        remaining = {k: v for k, v in ALL_VALID_ENV.items() if k not in missing_keys}
        for key, val in remaining.items():
            monkeypatch.setenv(key, val)
        with patch("config.credentials.load_dotenv", MagicMock()):
            from config.credentials import get_credentials
            with pytest.raises(ValueError) as exc_info:
                get_credentials()
        error_msg = str(exc_info.value)
        assert "TRIPLEWHALE_API_KEY" in error_msg
        assert "TIKTOK_APP_KEY" in error_msg
        assert "YOUTUBE_API_KEY" in error_msg

    def test_empty_string_treated_as_missing(self, monkeypatch):
        """空字符串凭证不得视为有效（if not value 逻辑）"""
        for key, val in ALL_VALID_ENV.items():
            monkeypatch.setenv(key, val)
        monkeypatch.setenv("TRIPLEWHALE_API_KEY", "")  # 覆盖为空字符串
        with patch("config.credentials.load_dotenv", MagicMock()):
            from config.credentials import get_credentials
            with pytest.raises(ValueError, match="TRIPLEWHALE_API_KEY"):
                get_credentials()


class TestNoDirectEnvAccess:
    """AC #3：验证 sources/ 目录无直接 os.getenv() 调用"""

    def test_sources_has_no_direct_os_getenv(self):
        sources_dir = Path(__file__).parent.parent / "sources"
        for py_file in sources_dir.rglob("*.py"):
            content = py_file.read_text()
            assert "os.getenv(" not in content, (
                f"{py_file.name} 直接调用了 os.getenv()，"
                f"必须改用 from config.credentials import get_credentials"
            )


class TestMaskCredential:
    """AC #4：mask_credential() 日志脱敏函数行为验证"""

    def test_long_credential_shows_first_4_chars(self):
        from config.credentials import mask_credential
        result = mask_credential("abcd1234xyz")
        assert result == "abcd****"

    def test_mask_appends_four_stars(self):
        from config.credentials import mask_credential
        result = mask_credential("XYZW9876")
        assert result.endswith("****")
        assert result == "XYZW****"

    def test_short_value_under_4_chars(self):
        from config.credentials import mask_credential
        result = mask_credential("ab")
        assert result == "ab****"

    def test_empty_string_returns_only_stars(self):
        from config.credentials import mask_credential
        result = mask_credential("")
        assert result == "****"

    def test_exactly_4_chars(self):
        from config.credentials import mask_credential
        result = mask_credential("1234")
        assert result == "1234****"

    def test_mask_credential_is_exported(self):
        import config.credentials
        assert hasattr(config.credentials, "mask_credential")
        assert callable(config.credentials.mask_credential)


class TestMockCredentialsFixture:
    """AC #5：mock_credentials fixture 验证"""

    def test_fixture_yields_test_credentials_dict(self, mock_credentials):
        from tests.conftest import TEST_CREDENTIALS
        assert mock_credentials == TEST_CREDENTIALS

    def test_fixture_contains_all_required_keys(self, mock_credentials):
        from config.credentials import _REQUIRED_KEYS
        assert set(mock_credentials.keys()) == set(_REQUIRED_KEYS)

    def test_get_credentials_returns_mock_via_patch(self, mock_credentials):
        """验证 patch("config.credentials.get_credentials") 生效"""
        import config.credentials
        result = config.credentials.get_credentials()
        assert result == mock_credentials
