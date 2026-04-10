"""凭证加载器：唯一允许读取 .env 的位置。

所有 source 模块必须从此模块导入凭证，禁止直接调用 os.getenv()。

公开接口：
    get_credentials(source_name=None) -> dict[str, str] — 加载并校验凭证（按源或全量）
    get_optional_config(key, default) -> str — 读取可选配置项（不在必需列表中）
    mask_credential(value: str) -> str       — 日志脱敏唯一入口，凭证显示前 4 位 + ****
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

_REQUIRED_KEYS: List[str] = [
    "TRIPLEWHALE_API_KEY",
    "TIKTOK_APP_KEY",
    "TIKTOK_APP_SECRET",
    "DINGTALK_APP_KEY",
    "DINGTALK_APP_SECRET",
    "YOUTUBE_API_KEY",
    "AWIN_API_TOKEN",
    "AWIN_ADVERTISER_ID",
    "CARTSEE_USERNAME",
    "CARTSEE_PASSWORD",
    "PARTNERBOOST_USERNAME",
    "PARTNERBOOST_PASSWORD",
    "FACEBOOK_USERNAME",
    "FACEBOOK_PASSWORD",
    "YOUTUBE_STUDIO_EMAIL",
    "YOUTUBE_STUDIO_PASSWORD",
]

# 每个数据源所需的凭证 key 映射表
_SOURCE_CREDENTIALS: Dict[str, List[str]] = {
    "triplewhale": ["TRIPLEWHALE_API_KEY"],
    "tiktok": ["TIKTOK_APP_KEY", "TIKTOK_APP_SECRET"],
    # 钉钉多维表格（workbook IDs 已内置于 sources/dingtalk.py TABLES 中）
    "dingtalk": ["DINGTALK_APP_KEY", "DINGTALK_APP_SECRET"],
    # 钉钉普通表格（workbook ID 已内置于 sources/dingtalk_sheet.py 中）
    "dingtalk_sheet": ["DINGTALK_APP_KEY", "DINGTALK_APP_SECRET"],
    "youtube": ["YOUTUBE_API_KEY"],
    "youtube_url": ["YOUTUBE_API_KEY"],
    "awin": ["AWIN_API_TOKEN", "AWIN_ADVERTISER_ID"],
    "cartsee": ["CARTSEE_USERNAME", "CARTSEE_PASSWORD"],
    "partnerboost": ["PARTNERBOOST_USERNAME", "PARTNERBOOST_PASSWORD"],
    "social_media": ["FACEBOOK_USERNAME", "FACEBOOK_PASSWORD"],
    "youtube_studio": ["YOUTUBE_STUDIO_EMAIL", "YOUTUBE_STUDIO_PASSWORD"],
}


def get_credentials(source_name: Optional[str] = None) -> Dict[str, str]:
    """加载并校验凭证，缺失时抛出 ValueError。

    Args:
        source_name: 数据源名称。为 None 时全量校验（--all 模式）；
                     有值时只校验该源所需凭证（--source 模式）。

    Returns:
        包含凭证键值的字典

    Raises:
        ValueError: 当一个或多个必需凭证键缺失时
    """
    if source_name is not None:
        keys_to_check = _SOURCE_CREDENTIALS.get(source_name, [])
    else:
        keys_to_check = _REQUIRED_KEYS

    creds: Dict[str, str] = {}
    missing: List[str] = []

    for key in keys_to_check:
        value = os.getenv(key)
        if not value:
            missing.append(key)
        else:
            creds[key] = value

    if missing:
        raise ValueError(f"缺少以下必需凭证：{', '.join(missing)}")

    return creds


def get_optional_config(key: str, default: str = "") -> str:
    """读取可选配置项（.env 中存在但不在必需凭证列表中的值）。

    与 get_credentials() 不同，此函数不校验、不抛异常，key 不存在时返回 default。
    source 模块需要读取可选路径参数（如 TIKTOK_PRODUCT_ID）时使用此函数，
    而非直接调用 os.getenv()。

    Args:
        key: 环境变量名
        default: 键不存在或值为空时返回的默认值

    Returns:
        环境变量的值，或 default
    """
    return os.getenv(key, default)


def mask_credential(value: str) -> str:
    """遮蔽凭证值用于日志输出：保留前 4 位，其余替换为 ****。

    这是项目中凭证脱敏的唯一实现，所有 source 模块日志输出凭证时必须使用此函数。
    禁止在其他位置重复实现脱敏逻辑。

    用法示例：
        from config.credentials import get_credentials, mask_credential
        creds = get_credentials()
        print(f"[triplewhale] 使用 API Key: {mask_credential(creds['TRIPLEWHALE_API_KEY'])}")
        # 输出：[triplewhale] 使用 API Key: abcd****

    Args:
        value: 需要遮蔽的凭证值

    Returns:
        前 4 位明文 + "****"，若值长度 < 4 则明文部分按实际长度截取
    """
    return value[:4] + "****"
