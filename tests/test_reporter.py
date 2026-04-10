"""reporter.py 单元测试

覆盖：
- AC1: write_raw_report 创建/覆盖 reports/{source}-raw.md，含时间戳、表名、样本数、字段表格
- AC2: raw 报告不含"需求字段（待人工对照）"区块（已废弃）
- AC3: raw 报告不含完整凭证值
- AC4: write_aggregate_report 生成聚合结论文档，含 Part 1~4
"""

import pytest
from pathlib import Path
import textwrap

import reporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_YAML = textwrap.dedent("""\
    reports:
      - report_name: 利润表
        dashboard: 销售表现、利润表
        deadline: "2026-04-08"
        launch_date: "2026-04-24"
        notes: 费用科目需要到四级
        fields:
          - 日期
          - 渠道
          - 店铺
      - report_name: 营销表现表
        dashboard: 营销推广-渠道效果
        deadline: "2026-04-20"
        launch_date: "2026-05-18"
        notes: 归因逻辑处理
        fields:
          - 日期
          - 曝光量
          - 花费
        source_hints:
          - "DTC 流量/订单量：均来自 TW pixel_joined_tvf()"
          - "DTC-硬广 曝光量：TW"
""")

SAMPLE_FIELDS = [
    {"field_name": "order_id", "data_type": "string", "sample_value": "ORD-001", "nullable": False},
    {"field_name": "revenue", "data_type": "number", "sample_value": 99.9, "nullable": True},
    {"field_name": "sku", "data_type": "string", "sample_value": "PROD-A", "nullable": False},
]


@pytest.fixture
def tmp_reports(tmp_path, monkeypatch):
    """将 REPORTS_DIR 和 REQUIREMENTS_PATH 重定向到临时目录。"""
    reports_dir = tmp_path / "reports"
    req_path = tmp_path / "field_requirements.yaml"
    req_path.write_text(SAMPLE_YAML, encoding="utf-8")

    monkeypatch.setattr(reporter, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(reporter, "REQUIREMENTS_PATH", req_path)
    return reports_dir


@pytest.fixture
def tmp_reports_no_yaml(tmp_path, monkeypatch):
    """REQUIREMENTS_PATH 指向不存在的文件（测试容错）。"""
    reports_dir = tmp_path / "reports"
    req_path = tmp_path / "nonexistent_requirements.yaml"

    monkeypatch.setattr(reporter, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(reporter, "REQUIREMENTS_PATH", req_path)
    return reports_dir


# ---------------------------------------------------------------------------
# write_raw_report 基本功能
# ---------------------------------------------------------------------------

class TestWriteRawReportCreatesFile:
    """AC1: write_raw_report 创建文件并包含正确内容。"""

    def test_file_is_created(self, tmp_reports):
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        assert (tmp_reports / "triplewhale-raw.md").exists()

    def test_file_contains_header(self, tmp_reports):
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "triplewhale" in content
        assert "字段验证报告（Raw）" in content

    def test_file_contains_timestamp(self, tmp_reports):
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "生成时间" in content

    def test_file_contains_table_name(self, tmp_reports):
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "pixel_orders_table" in content

    def test_file_contains_sample_count(self, tmp_reports):
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "3" in content

    def test_file_contains_field_table(self, tmp_reports):
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "字段名" in content
        assert "类型" in content
        assert "order_id" in content
        assert "revenue" in content

    def test_nullable_field_display(self, tmp_reports):
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "是" in content   # revenue nullable=True
        assert "否" in content   # order_id nullable=False

    def test_table_name_none_shows_na(self, tmp_reports):
        reporter.write_raw_report("youtube", SAMPLE_FIELDS, None, 1)
        content = (tmp_reports / "youtube-raw.md").read_text(encoding="utf-8")
        assert "N/A" in content

    def test_no_requirements_section(self, tmp_reports):
        """AC2: raw 报告不再包含"需求字段（待人工对照）"区块。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "需求字段（待人工对照）" not in content
        assert "⬜ 待确认" not in content

    def test_reports_dir_created_automatically(self, tmp_path, monkeypatch):
        reports_dir = tmp_path / "reports"
        req_path = tmp_path / "nonexistent.yaml"
        monkeypatch.setattr(reporter, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter, "REQUIREMENTS_PATH", req_path)

        assert not reports_dir.exists()
        reporter.write_raw_report("test", [], None, 0)
        assert reports_dir.exists()
        assert (reports_dir / "test-raw.md").exists()


# ---------------------------------------------------------------------------
# write_raw_report 覆盖已有文件
# ---------------------------------------------------------------------------

class TestWriteRawReportOverwrites:

    def test_overwrites_existing_file(self, tmp_reports):
        fields_v1 = [{"field_name": "old_field", "data_type": "string",
                       "sample_value": "old", "nullable": False}]
        reporter.write_raw_report("triplewhale", fields_v1, "pixel_orders_table", 1)

        fields_v2 = [{"field_name": "new_field", "data_type": "number",
                       "sample_value": 42, "nullable": True}]
        reporter.write_raw_report("triplewhale", fields_v2, "pixel_orders_table", 2)
        content_v2 = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")

        assert "new_field" in content_v2
        assert "old_field" not in content_v2


# ---------------------------------------------------------------------------
# raw 报告不含完整凭证值
# ---------------------------------------------------------------------------

class TestRawReportNoCredentials:
    """AC3: raw 报告不包含完整 API Key / Token / 密码值。"""

    def test_masked_sample_value_passes_through(self, tmp_reports):
        fields = [
            {"field_name": "token", "data_type": "string",
             "sample_value": "abcd****", "nullable": False}
        ]
        reporter.write_raw_report("test_source", fields, None, 1)
        content = (tmp_reports / "test_source-raw.md").read_text(encoding="utf-8")
        assert "abcd****" in content

    def test_report_header_has_no_credential_keywords(self, tmp_reports):
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "API_KEY" not in content
        assert "PASSWORD" not in content


# ---------------------------------------------------------------------------
# write_aggregate_report 聚合结论文档
# ---------------------------------------------------------------------------

class TestWriteAggregateReport:
    """AC4: write_aggregate_report 生成聚合结论文档。"""

    def _make_source_results(self):
        return {
            "triplewhale": {
                "success": True,
                "status": "已生成",
                "error": None,
                "fields": {
                    "pixel_orders_table": [
                        {"field_name": "order_id", "data_type": "string", "sample_value": "ORD-001", "nullable": False},
                        {"field_name": "revenue", "data_type": "number", "sample_value": 99.9, "nullable": True},
                    ],
                    "pixel_joined_tvf": [
                        {"field_name": "impressions", "data_type": "number", "sample_value": 1234, "nullable": False},
                    ],
                },
            },
            "social_media": {
                "success": False,
                "status": "NotImplementedError",
                "error": "凭证未就绪，暂未实现",
                "fields": {},
            },
            "youtube": {
                "success": True,
                "status": "已生成",
                "error": None,
                "fields": {
                    None: [
                        {"field_name": "title", "data_type": "string", "sample_value": "测试视频", "nullable": False},
                        {"field_name": "viewCount", "data_type": "number", "sample_value": 5000, "nullable": False},
                    ],
                },
            },
        }

    def test_aggregate_file_created(self, tmp_reports):
        reporter.write_aggregate_report(self._make_source_results())
        assert (tmp_reports / "all-sources-aggregate.md").exists()

    def test_aggregate_contains_part1_header(self, tmp_reports):
        reporter.write_aggregate_report(self._make_source_results())
        content = (tmp_reports / "all-sources-aggregate.md").read_text(encoding="utf-8")
        assert "Part 1：数据源采集结论汇总" in content

    def test_aggregate_part1_shows_source_status(self, tmp_reports):
        reporter.write_aggregate_report(self._make_source_results())
        content = (tmp_reports / "all-sources-aggregate.md").read_text(encoding="utf-8")
        assert "triplewhale" in content
        assert "已生成" in content
        assert "social_media" in content
        assert "NotImplementedError" in content

    def test_aggregate_contains_part2_fields(self, tmp_reports):
        reporter.write_aggregate_report(self._make_source_results())
        content = (tmp_reports / "all-sources-aggregate.md").read_text(encoding="utf-8")
        assert "Part 2：各数据源实际字段清单" in content
        assert "order_id" in content
        assert "impressions" in content
        assert "viewCount" in content

    def test_aggregate_contains_part3_report_templates(self, tmp_reports):
        reporter.write_aggregate_report(self._make_source_results())
        content = (tmp_reports / "all-sources-aggregate.md").read_text(encoding="utf-8")
        assert "Part 3：报表字段映射分析" in content
        assert "利润表" in content
        assert "营销表现表" in content
        assert "待分析" in content

    def test_aggregate_contains_part3_all_fields(self, tmp_reports):
        reporter.write_aggregate_report(self._make_source_results())
        content = (tmp_reports / "all-sources-aggregate.md").read_text(encoding="utf-8")
        # 利润表字段
        assert "日期" in content
        assert "渠道" in content
        assert "店铺" in content
        # 营销表现表字段
        assert "曝光量" in content
        assert "花费" in content

    def test_aggregate_contains_part4_prompt(self, tmp_reports):
        reporter.write_aggregate_report(self._make_source_results())
        content = (tmp_reports / "all-sources-aggregate.md").read_text(encoding="utf-8")
        assert "Part 4：AI 分析提示语" in content
        assert "来源字段必须真实" in content
        assert "可映射" in content
        assert "需转换" in content
        assert "缺失" in content

    def test_aggregate_no_requirements_yaml_graceful(self, tmp_reports_no_yaml):
        """field_requirements.yaml 不存在时 Part 3 降级但不报错。"""
        results = {"test": {"success": True, "status": "已生成", "error": None, "fields": {}}}
        reporter.write_aggregate_report(results)
        content = (tmp_reports_no_yaml / "all-sources-aggregate.md").read_text(encoding="utf-8")
        assert "未找到报表定义配置" in content

    def test_aggregate_overwrites_on_rerun(self, tmp_reports):
        """每次 --all 覆盖更新。"""
        results_v1 = {"source_a": {"success": True, "status": "已生成", "error": None, "fields": {}}}
        reporter.write_aggregate_report(results_v1)

        results_v2 = {"source_b": {"success": True, "status": "已生成", "error": None, "fields": {}}}
        reporter.write_aggregate_report(results_v2)

        content = (tmp_reports / "all-sources-aggregate.md").read_text(encoding="utf-8")
        assert "source_b" in content
        assert "source_a" not in content

    def test_aggregate_contains_part3_source_hints(self, tmp_reports):
        """Part 3 渲染 source_hints 数据来源提示。"""
        reporter.write_aggregate_report(self._make_source_results())
        content = (tmp_reports / "all-sources-aggregate.md").read_text(encoding="utf-8")
        assert "数据来源提示" in content

    def test_aggregate_failed_source_no_fields(self, tmp_reports):
        """失败的数据源在 Part 2 中标注无字段数据。"""
        results = {
            "failed_src": {
                "success": False,
                "status": "人机验证超时",
                "error": "TimeoutError",
                "fields": {},
            }
        }
        reporter.write_aggregate_report(results)
        content = (tmp_reports / "all-sources-aggregate.md").read_text(encoding="utf-8")
        assert "failed_src" in content
        assert "人机验证超时" in content
        assert "无字段数据" in content


# ---------------------------------------------------------------------------
# 边界情况
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_fields_list(self, tmp_reports):
        reporter.write_raw_report("empty_source", [], None, 0)
        content = (tmp_reports / "empty_source-raw.md").read_text(encoding="utf-8")
        assert "字段名" in content

    def test_multiple_sources_independent_files(self, tmp_reports):
        reporter.write_raw_report("source_a", SAMPLE_FIELDS, "table_a", 1)
        reporter.write_raw_report("source_b", SAMPLE_FIELDS, "table_b", 2)
        assert (tmp_reports / "source_a-raw.md").exists()
        assert (tmp_reports / "source_b-raw.md").exists()

    def test_source_name_used_as_filename(self, tmp_reports):
        reporter.write_raw_report("my_source", [], None, 0)
        assert (tmp_reports / "my_source-raw.md").exists()
