"""凭证加载器：唯一允许读取 .env 的位置。

所有 source 模块必须从此模块导入凭证，禁止直接调用 os.getenv()。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

_REQUIRED_KEYS: list[str] = [
    "TRIPLEWHALE_API_KEY",
    "TIKTOK_REFRESH_TOKEN",
    "TIKTOK_APP_KEY",
    "TIKTOK_APP_SECRET",
    "DINGTALK_APP_KEY",
    "DINGTALK_APP_SECRET",
    "YOUTUBE_API_KEY",
    "AWIN_USERNAME",
    "AWIN_PASSWORD",
    "CARTSEE_USERNAME",
    "CARTSEE_PASSWORD",
    "PARTNERBOOST_USERNAME",
    "PARTNERBOOST_PASSWORD",
]


def get_credentials() -> dict[str, str]:
    """加载并校验所有必需凭证，缺失时抛出 ValueError。

    Returns:
        包含所有凭证键值的字典

    Raises:
        ValueError: 当一个或多个必需凭证键缺失时
    """
    creds: dict[str, str] = {}
    missing: list[str] = []

    for key in _REQUIRED_KEYS:
        value = os.getenv(key)
        if not value:
            missing.append(key)
        else:
            creds[key] = value

    if missing:
        raise ValueError(f"缺少以下必需凭证：{', '.join(missing)}")

    return creds
