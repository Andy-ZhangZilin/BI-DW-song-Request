"""社媒后台数据源 Stub 模块

此模块为占位实现（stub），三个接口均抛出 NotImplementedError。
当社媒后台凭证就绪后，只需在此文件中填充实现，无需修改框架其他部分。

接口契约（ARCH2）：
    authenticate() -> bool
    fetch_sample(table_name: Optional[str] = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]

将来实现时，每个 FieldInfo 记录应包含：
    {"field_name": str, "data_type": str, "sample_value": Any, "nullable": bool}
"""

from typing import Optional


def authenticate() -> bool:
    """社媒后台认证（暂未实现）。

    凭证就绪后，在此实现浏览器自动化登录或 API 认证逻辑。

    Raises:
        NotImplementedError: 凭证未就绪时始终抛出。
    """
    raise NotImplementedError("social_media: 凭证未就绪，暂未实现")


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """抓取社媒后台样本数据（暂未实现）。

    凭证就绪后，在此实现数据抓取逻辑，返回至少一条原始记录。

    Args:
        table_name: 数据表名（可选）。

    Raises:
        NotImplementedError: 凭证未就绪时始终抛出。
    """
    raise NotImplementedError("social_media: 凭证未就绪，暂未实现")


def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取字段列表（暂未实现）。

    凭证就绪后，在此实现字段提取逻辑，返回符合 FieldInfo 结构的列表。

    Args:
        sample: fetch_sample() 返回的原始样本数据。

    Raises:
        NotImplementedError: 凭证未就绪时始终抛出。
    """
    raise NotImplementedError("social_media: 凭证未就绪，暂未实现")
