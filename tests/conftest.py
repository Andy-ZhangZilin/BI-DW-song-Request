"""pytest 全局 fixtures：mock_credentials 供所有单元测试使用"""
import pytest
from unittest.mock import patch, MagicMock


TEST_CREDENTIALS: dict[str, str] = {
    "TRIPLEWHALE_API_KEY": "test_tw_key",
    "TIKTOK_APP_KEY": "test_tiktok_app_key",
    "TIKTOK_APP_SECRET": "test_tiktok_app_secret",
    "DINGTALK_APP_KEY": "test_dingtalk_app_key",
    "DINGTALK_APP_SECRET": "test_dingtalk_app_secret",
    "DINGTALK_WORKBOOK_ID": "test_workbook_id",
    "YOUTUBE_API_KEY": "test_youtube_key",
    "AWIN_API_TOKEN": "test_awin_api_token",
    "AWIN_ADVERTISER_ID": "89509",
    "CARTSEE_USERNAME": "test_cartsee_user",
    "CARTSEE_PASSWORD": "test_cartsee_pass",
    "PARTNERBOOST_USERNAME": "test_pb_user",
    "PARTNERBOOST_PASSWORD": "test_pb_pass",
    "FACEBOOK_USERNAME": "test_fb_user",
    "FACEBOOK_PASSWORD": "test_fb_pass",
    "YOUTUBE_STUDIO_EMAIL": "test_yt_studio_email",
    "YOUTUBE_STUDIO_PASSWORD": "test_yt_studio_pass",
}


@pytest.fixture
def mock_credentials():
    """Mock get_credentials() 返回测试凭证字典，无需真实 .env 文件。

    同时 patch load_dotenv 防止真实 .env 文件在 import 时污染测试环境。

    用法：
        def test_something(mock_credentials):
            # get_credentials() 已被 mock，返回 TEST_CREDENTIALS
            pass
    """
    with patch("config.credentials.load_dotenv", MagicMock()), \
         patch("config.credentials.get_credentials", return_value=TEST_CREDENTIALS):
        yield TEST_CREDENTIALS
