"""CartSee 数据源单元测试。

单元测试：仅测试 extract_fields()，不启动浏览器。
集成测试：标注 @pytest.mark.integration，不在普通 pytest 运行中执行。
"""
import json
import pytest
from pathlib import Path


def test_extract_fields_returns_field_info_structure(mock_credentials):
    """extract_fields() 返回正确的 FieldInfo 结构。"""
    from sources.cartsee import extract_fields
    fixture_path = Path(__file__).parent / "fixtures/cartsee_sample.json"
    sample = json.loads(fixture_path.read_text(encoding="utf-8"))
    fields = extract_fields(sample)

    assert len(fields) > 0
    for f in fields:
        assert "field_name" in f
        assert "data_type" in f
        assert "sample_value" in f
        assert "nullable" in f
        assert isinstance(f["field_name"], str)
        assert f["data_type"] in {"string", "number", "boolean", "array", "object", "null"}
        assert isinstance(f["nullable"], bool)


def test_extract_fields_empty_sample(mock_credentials):
    """extract_fields() 对空样本返回空列表。"""
    from sources.cartsee import extract_fields
    assert extract_fields([]) == []


def test_extract_fields_correct_types(mock_credentials):
    """extract_fields() 正确推断各字段数据类型。"""
    from sources.cartsee import extract_fields
    fixture_path = Path(__file__).parent / "fixtures/cartsee_sample.json"
    sample = json.loads(fixture_path.read_text(encoding="utf-8"))
    fields = extract_fields(sample)

    field_map = {f["field_name"]: f for f in fields}

    # 字符串字段
    assert field_map["campaign_name"]["data_type"] == "string"
    assert field_map["status"]["data_type"] == "string"
    assert field_map["created_at"]["data_type"] == "string"

    # 数值字段
    assert field_map["sent"]["data_type"] == "number"
    assert field_map["opened"]["data_type"] == "number"
    assert field_map["open_rate"]["data_type"] == "number"
    assert field_map["revenue"]["data_type"] in {"number", "null"}  # 含 null 值时可能推断为 null


def test_extract_fields_nullable_detection(mock_credentials):
    """extract_fields() 正确检测可空字段。"""
    from sources.cartsee import extract_fields
    fixture_path = Path(__file__).parent / "fixtures/cartsee_sample.json"
    sample = json.loads(fixture_path.read_text(encoding="utf-8"))
    fields = extract_fields(sample)

    field_map = {f["field_name"]: f for f in fields}

    # revenue 在第三条记录中为 null，应标记为可空
    assert field_map["revenue"]["nullable"] is True

    # campaign_name 所有记录均有值，不可空
    assert field_map["campaign_name"]["nullable"] is False


def test_extract_fields_all_four_keys_present(mock_credentials):
    """每个 FieldInfo 条目包含全部 4 个必需键。"""
    from sources.cartsee import extract_fields
    sample = [{"name": "Test", "count": 5, "active": True, "data": None}]
    fields = extract_fields(sample)

    assert len(fields) == 4
    for f in fields:
        assert set(f.keys()) == {"field_name", "data_type", "sample_value", "nullable"}


# 集成测试：标注 integration，不在普通 pytest 运行中执行
@pytest.mark.integration
def test_authenticate_with_real_credentials():
    from sources.cartsee import authenticate
    result = authenticate()
    assert isinstance(result, bool)


@pytest.mark.integration
def test_fetch_sample_returns_records():
    from sources.cartsee import fetch_sample
    records = fetch_sample()
    assert len(records) >= 1
