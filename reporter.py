"""报告渲染器：负责 raw.md 写入和 validation.md 首次创建"""
from pathlib import Path


def write_raw_report(
    source_name: str,
    fields: list[dict],
    table_name: str | None = None,
    sample_count: int = 0,
) -> None:
    """写入 reports/{source_name}-raw.md，每次覆盖。

    Args:
        source_name: 数据源名称（如 triplewhale）
        fields: FieldInfo 列表，每条含 field_name/data_type/sample_value/nullable
        table_name: 数据表名称（可选）
        sample_count: 实际抓取的样本记录数
    """
    # TODO: Story 1.4 实现
    pass


def init_validation_report(source_name: str) -> None:
    """首次创建 reports/{source_name}-validation.md，已存在则不覆盖。

    Args:
        source_name: 数据源名称（如 triplewhale）
    """
    # TODO: Story 1.4 实现
    pass
