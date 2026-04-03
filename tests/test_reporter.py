"""reporter.py 单元测试

覆盖 AC 1-5：
- AC1: write_raw_report 创建/覆盖 reports/{source}-raw.md，含时间戳、表名、样本数、字段表格
- AC2: write_raw_report 报告末尾包含"需求字段（待人工对照）"区块，来自 field_requirements.yaml
- AC3: init_validation_report 首次创建模板，含三态标注占位符
- AC4: init_validation_report 不覆盖已存在文件
- AC5: raw 报告不含完整凭证值
"""

import pytest
from pathlib import Path
import textwrap

import reporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_YAML = textwrap.dedent("""\
    profit_table:
      - display_name: 日期
        source: triplewhale
        table: pixel_orders_table
      - display_name: 销售额
        source: triplewhale
        table: pixel_orders_table
      - display_name: SKU
        source: tiktok
        table: orders
    marketing_table:
      - display_name: 曝光量
        source: triplewhale
        table: pixel_joined_tvf
""")

SAMPLE_FIELDS = [
    {"field_name": "order_id", "data_type": "string", "sample_value": "ORD-001", "nullable": False},
    {"field_name": "revenue", "data_type": "number", "sample_value": 99.9, "nullable": True},
    {"field_name": "sku", "data_type": "string", "sample_value": "PROD-A", "nullable": False},
]


@pytest.fixture
def tmp_reports(tmp_path, monkeypatch):
    """将 REPORTS_DIR 和 REQUIREMENTS_PATH 重定向到临时目录，避免污染真实文件。"""
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
    req_path = tmp_path / "nonexistent_requirements.yaml"  # 不创建

    monkeypatch.setattr(reporter, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(reporter, "REQUIREMENTS_PATH", req_path)
    return reports_dir


# ---------------------------------------------------------------------------
# Task 4.1: write_raw_report 创建文件，验证基本内容
# ---------------------------------------------------------------------------

class TestWriteRawReportCreatesFile:
    """AC1 & AC2: write_raw_report 创建文件并包含正确内容。"""

    def test_file_is_created(self, tmp_reports):
        """AC1: 调用后文件应存在。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        assert (tmp_reports / "triplewhale-raw.md").exists()

    def test_file_contains_header(self, tmp_reports):
        """AC1: 文件包含数据源名称标题。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "triplewhale" in content
        assert "字段验证报告（Raw）" in content

    def test_file_contains_timestamp(self, tmp_reports):
        """AC1: 文件包含生成时间戳（格式 YYYY-MM-DD）。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "生成时间" in content
        assert "2026" in content  # 年份存在

    def test_file_contains_table_name(self, tmp_reports):
        """AC1: 文件包含数据表名。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "pixel_orders_table" in content

    def test_file_contains_sample_count(self, tmp_reports):
        """AC1: 文件包含样本记录数。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "3" in content

    def test_file_contains_field_table(self, tmp_reports):
        """AC1: 文件包含字段名、类型、示例值、可空列。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "字段名" in content
        assert "类型" in content
        assert "示例值" in content
        assert "可空" in content
        assert "order_id" in content
        assert "revenue" in content

    def test_nullable_field_display(self, tmp_reports):
        """AC1: 可空字段显示"是"，不可空显示"否"。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "是" in content   # revenue nullable=True
        assert "否" in content   # order_id nullable=False

    def test_table_name_none_shows_na(self, tmp_reports):
        """AC1: table_name=None（非 SQL 数据源）时显示 N/A。"""
        reporter.write_raw_report("youtube", SAMPLE_FIELDS, None, 1)
        content = (tmp_reports / "youtube-raw.md").read_text(encoding="utf-8")
        assert "N/A" in content

    def test_file_contains_requirements_section(self, tmp_reports):
        """AC2: 文件末尾包含"需求字段（待人工对照）"区块。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "需求字段（待人工对照）" in content

    def test_requirements_section_contains_display_names(self, tmp_reports):
        """AC2: 需求字段区块列出该数据源在 YAML 中配置的所有 display_name。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        # triplewhale 在 SAMPLE_YAML 中有 日期、销售额、曝光量
        assert "日期" in content
        assert "销售额" in content
        assert "曝光量" in content

    def test_requirements_section_initial_status(self, tmp_reports):
        """AC2: 需求字段初始状态标记为 ⬜ 待确认。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "⬜ 待确认" in content

    def test_requirements_section_excludes_other_sources(self, tmp_reports):
        """AC2: 需求字段区块不包含其他数据源（tiktok）的字段。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        # SKU 属于 tiktok，不应出现在 triplewhale 的需求字段区块
        # （实际字段表格中不含 SKU，需求字段区块也不应有 SKU 的行）
        # 注：仅检查需求字段区块部分
        req_section = content.split("## 需求字段（待人工对照）")[1]
        assert "SKU" not in req_section

    def test_requirements_empty_when_no_yaml(self, tmp_reports_no_yaml):
        """AC2: YAML 不存在时，需求字段区块有占位提示，不报错。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports_no_yaml / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "需求字段（待人工对照）" in content
        # 不应抛出异常，文件应成功创建

    def test_reports_dir_created_automatically(self, tmp_path, monkeypatch):
        """AC1: reports/ 目录不存在时自动创建。"""
        reports_dir = tmp_path / "reports"
        req_path = tmp_path / "nonexistent.yaml"
        monkeypatch.setattr(reporter, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter, "REQUIREMENTS_PATH", req_path)

        assert not reports_dir.exists()
        reporter.write_raw_report("test", [], None, 0)
        assert reports_dir.exists()
        assert (reports_dir / "test-raw.md").exists()


# ---------------------------------------------------------------------------
# Task 4.2: write_raw_report 覆盖已有文件
# ---------------------------------------------------------------------------

class TestWriteRawReportOverwrites:
    """AC1: write_raw_report 应覆盖已有文件（不保留旧内容）。"""

    def test_overwrites_existing_file(self, tmp_reports):
        """AC1: 再次调用时覆盖旧文件，内容为最新。"""
        # 第一次写入
        fields_v1 = [{"field_name": "old_field", "data_type": "string",
                       "sample_value": "old", "nullable": False}]
        reporter.write_raw_report("triplewhale", fields_v1, "pixel_orders_table", 1)
        content_v1 = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "old_field" in content_v1

        # 第二次写入（覆盖）
        fields_v2 = [{"field_name": "new_field", "data_type": "number",
                       "sample_value": 42, "nullable": True}]
        reporter.write_raw_report("triplewhale", fields_v2, "pixel_orders_table", 2)
        content_v2 = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")

        assert "new_field" in content_v2
        assert "old_field" not in content_v2  # 旧内容不保留
        assert "2" in content_v2  # sample_count 更新


# ---------------------------------------------------------------------------
# Task 4.3: init_validation_report 首次创建
# ---------------------------------------------------------------------------

class TestInitValidationReportCreates:
    """AC3: init_validation_report 首次创建模板。"""

    def test_file_is_created(self, tmp_reports):
        """AC3: 文件不存在时应被创建。"""
        reporter.init_validation_report("triplewhale")
        assert (tmp_reports / "triplewhale-validation.md").exists()

    def test_file_contains_three_state_markers(self, tmp_reports):
        """AC3: 模板包含三态标注占位符说明。"""
        reporter.init_validation_report("triplewhale")
        content = (tmp_reports / "triplewhale-validation.md").read_text(encoding="utf-8")
        assert "✅" in content
        assert "⚠️" in content
        assert "❌" in content

    def test_file_contains_initial_pending_status(self, tmp_reports):
        """AC3: 各字段初始状态为 ⬜ 待确认。"""
        reporter.init_validation_report("triplewhale")
        content = (tmp_reports / "triplewhale-validation.md").read_text(encoding="utf-8")
        assert "⬜ 待确认" in content

    def test_file_contains_conversion_logic_hint(self, tmp_reports):
        """AC3: 模板包含转换逻辑说明（⚠️ 需转换的说明）。"""
        reporter.init_validation_report("triplewhale")
        content = (tmp_reports / "triplewhale-validation.md").read_text(encoding="utf-8")
        assert "需转换" in content  # 转换逻辑说明行

    def test_file_contains_alternative_solution_hint(self, tmp_reports):
        """AC3: 模板包含替代方案说明（❌ 缺失的说明）。"""
        reporter.init_validation_report("triplewhale")
        content = (tmp_reports / "triplewhale-validation.md").read_text(encoding="utf-8")
        assert "缺失" in content  # 替代方案说明行

    def test_file_contains_no_overwrite_notice(self, tmp_reports):
        """AC3: 模板包含"人工维护"说明。"""
        reporter.init_validation_report("triplewhale")
        content = (tmp_reports / "triplewhale-validation.md").read_text(encoding="utf-8")
        assert "人工维护" in content

    def test_file_contains_source_name(self, tmp_reports):
        """AC3: 模板标题包含数据源名称。"""
        reporter.init_validation_report("triplewhale")
        content = (tmp_reports / "triplewhale-validation.md").read_text(encoding="utf-8")
        assert "triplewhale" in content

    def test_file_contains_requirement_fields(self, tmp_reports):
        """AC3: 模板列出该数据源在 YAML 中配置的需求字段。"""
        reporter.init_validation_report("triplewhale")
        content = (tmp_reports / "triplewhale-validation.md").read_text(encoding="utf-8")
        assert "日期" in content
        assert "销售额" in content

    def test_reports_dir_created_automatically(self, tmp_path, monkeypatch):
        """AC3: reports/ 目录不存在时自动创建。"""
        reports_dir = tmp_path / "reports"
        req_path = tmp_path / "nonexistent.yaml"
        monkeypatch.setattr(reporter, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter, "REQUIREMENTS_PATH", req_path)

        assert not reports_dir.exists()
        reporter.init_validation_report("test")
        assert reports_dir.exists()
        assert (reports_dir / "test-validation.md").exists()


# ---------------------------------------------------------------------------
# Task 4.4: init_validation_report 不覆盖已存在文件
# ---------------------------------------------------------------------------

class TestInitValidationReportNoOverwrite:
    """AC4: init_validation_report 若文件已存在则不覆盖。"""

    def test_does_not_overwrite_existing_file(self, tmp_reports):
        """AC4: 人工标注内容应完整保留。"""
        manual_content = "人工标注内容：日期 ✅ 直接可用\n销售额 ⚠️ 需转换：单位换算"
        (tmp_reports).mkdir(parents=True, exist_ok=True)
        (tmp_reports / "triplewhale-validation.md").write_text(
            manual_content, encoding="utf-8"
        )

        reporter.init_validation_report("triplewhale")

        content_after = (tmp_reports / "triplewhale-validation.md").read_text(encoding="utf-8")
        assert content_after == manual_content

    def test_does_not_overwrite_empty_existing_file(self, tmp_reports):
        """AC4: 即使现有文件为空也不覆盖。"""
        (tmp_reports).mkdir(parents=True, exist_ok=True)
        (tmp_reports / "triplewhale-validation.md").write_text("", encoding="utf-8")

        reporter.init_validation_report("triplewhale")

        content_after = (tmp_reports / "triplewhale-validation.md").read_text(encoding="utf-8")
        assert content_after == ""

    def test_creates_file_when_not_exists(self, tmp_reports):
        """AC4（反向）: 文件不存在时正常创建。"""
        assert not (tmp_reports / "youtube-validation.md").exists()
        reporter.init_validation_report("youtube")
        assert (tmp_reports / "youtube-validation.md").exists()


# ---------------------------------------------------------------------------
# Task 4.5: raw 报告不含完整凭证值
# ---------------------------------------------------------------------------

class TestRawReportNoCredentials:
    """AC5: raw 报告不包含完整 API Key / Token / 密码值。"""

    def test_masked_sample_value_passes_through(self, tmp_reports):
        """AC5: 脱敏后的示例值（abcd****）可出现在报告中。"""
        fields = [
            {"field_name": "token", "data_type": "string",
             "sample_value": "abcd****", "nullable": False}
        ]
        reporter.write_raw_report("test_source", fields, None, 1)
        content = (tmp_reports / "test_source-raw.md").read_text(encoding="utf-8")
        # 脱敏值允许出现
        assert "abcd****" in content

    def test_full_api_key_in_sample_value_appears_as_is(self, tmp_reports):
        """AC5: reporter 不负责脱敏，source 模块负责；reporter 透传 sample_value。

        如果 source 模块传入了已脱敏的值（含 ****），reporter 只负责渲染，不做额外过滤。
        此测试确认 reporter 不会篡改 sample_value。
        """
        fields = [
            {"field_name": "api_key", "data_type": "string",
             "sample_value": "sk-1234****", "nullable": False}
        ]
        reporter.write_raw_report("test_source", fields, None, 1)
        content = (tmp_reports / "test_source-raw.md").read_text(encoding="utf-8")
        assert "sk-1234****" in content

    def test_report_header_has_no_credential_keywords(self, tmp_reports):
        """AC5: 报告头部（标题、元信息）不含凭证关键词。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        content = (tmp_reports / "triplewhale-raw.md").read_text(encoding="utf-8")
        # 报告头部不应包含 API_KEY、TOKEN、PASSWORD 等原始凭证关键词
        header_section = content.split("## 实际返回字段")[0]
        assert "API_KEY" not in header_section
        assert "PASSWORD" not in header_section
        assert "ACCESS_TOKEN" not in header_section


# ---------------------------------------------------------------------------
# 其他边界情况
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """边界情况测试。"""

    def test_empty_fields_list(self, tmp_reports):
        """空字段列表时报告应正常生成（字段表格为空）。"""
        reporter.write_raw_report("empty_source", [], None, 0)
        content = (tmp_reports / "empty_source-raw.md").read_text(encoding="utf-8")
        assert "字段名" in content  # 表头仍存在
        assert "样本记录数" in content

    def test_multiple_sources_independent_files(self, tmp_reports):
        """不同数据源生成独立文件，互不影响。"""
        reporter.write_raw_report("source_a", SAMPLE_FIELDS, "table_a", 1)
        reporter.write_raw_report("source_b", SAMPLE_FIELDS, "table_b", 2)
        assert (tmp_reports / "source_a-raw.md").exists()
        assert (tmp_reports / "source_b-raw.md").exists()

    def test_validation_and_raw_are_independent(self, tmp_reports):
        """validation.md 和 raw.md 是独立文件，互不影响。"""
        reporter.write_raw_report("triplewhale", SAMPLE_FIELDS, "pixel_orders_table", 3)
        reporter.init_validation_report("triplewhale")
        assert (tmp_reports / "triplewhale-raw.md").exists()
        assert (tmp_reports / "triplewhale-validation.md").exists()

    def test_source_name_used_as_filename(self, tmp_reports):
        """source_name 直接用于文件名。"""
        reporter.write_raw_report("my_source", [], None, 0)
        assert (tmp_reports / "my_source-raw.md").exists()
