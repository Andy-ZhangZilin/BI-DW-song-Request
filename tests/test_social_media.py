"""sources/social_media.py 单元测试

覆盖 AC：
- AC1: authenticate() 抛出 NotImplementedError，message 为 "social_media: 凭证未就绪，暂未实现"
- AC2: fetch_sample() 抛出 NotImplementedError
- AC3: extract_fields([]) 抛出 NotImplementedError
"""

import pytest
import sources.social_media as social_media


def test_authenticate_ac1_raises_not_implemented():
    """AC1: authenticate() 应抛出 NotImplementedError，含指定 message。"""
    with pytest.raises(NotImplementedError) as exc_info:
        social_media.authenticate()
    assert "social_media: 凭证未就绪，暂未实现" in str(exc_info.value)


def test_fetch_sample_ac2_raises_not_implemented():
    """AC2: fetch_sample() 应抛出 NotImplementedError。"""
    with pytest.raises(NotImplementedError):
        social_media.fetch_sample()


def test_fetch_sample_ac2_raises_not_implemented_with_table_name():
    """AC2: fetch_sample(table_name=...) 也应抛出 NotImplementedError。"""
    with pytest.raises(NotImplementedError):
        social_media.fetch_sample(table_name="some_table")


def test_extract_fields_ac3_raises_not_implemented():
    """AC3: extract_fields([]) 应抛出 NotImplementedError。"""
    with pytest.raises(NotImplementedError):
        social_media.extract_fields([])
