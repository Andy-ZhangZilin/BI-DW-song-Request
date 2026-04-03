"""test_e2e.py — Story 5.2 端到端集成验证测试

与 test_validate.py 的关键区别：
- test_validate.py：reporter 完全 mock（无文件 I/O），只验证 validate.py 调度逻辑
- test_e2e.py：使用真实 reporter（patch REPORTS_DIR 到 tmp_path），验证完整 validate → reporter → 文件 全链路

覆盖 AC：
AC1 - 完整 --all 流水线：8 个 mock source 均生成 raw.md 和 validation.md
AC2 - authenticate() 返回 False：跳过 fetch_sample，标记失败，其余继续，退出码 1
AC3 - fetch_sample() 抛出异常：标记失败，其余继续，退出码 1
AC4 - validation.md 已存在（人工标注）：raw.md 覆盖更新，validation.md 内容保持不变
AC5 - pytest tests/ -m "not integration" 全部通过，无需真实凭证
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 辅助工厂（与 test_validate.py 保持一致的结构）
# ---------------------------------------------------------------------------

def _make_mock_source(
    auth_result: bool = True,
    sample: list | None = None,
    fields: list | None = None,
    fetch_exception: Exception | None = None,
    auth_exception: Exception | None = None,
) -> MagicMock:
    """创建一个预设行为的 mock source 模块。"""
    m = MagicMock()
    if auth_exception is not None:
        m.authenticate.side_effect = auth_exception
    else:
        m.authenticate.return_value = auth_result
    if fetch_exception is not None:
        m.fetch_sample.side_effect = fetch_exception
    else:
        m.fetch_sample.return_value = sample or [{"field": "value"}]
    m.extract_fields.return_value = fields or [
        {"field_name": "f", "data_type": "string", "sample_value": "v", "nullable": False}
    ]
    return m


def _make_all_mock_sources(override: dict | None = None) -> dict:
    """创建全部 8 个 source 的 mock 注册表，可通过 override 替换特定 source。"""
    sources = {
        "triplewhale": _make_mock_source(),
        "tiktok": _make_mock_source(),
        "dingtalk": _make_mock_source(),
        "youtube": _make_mock_source(),
        "awin": _make_mock_source(),
        "cartsee": _make_mock_source(),
        "partnerboost": _make_mock_source(),
        "social_media": _make_mock_source(),
    }
    if override:
        sources.update(override)
    return sources


# ---------------------------------------------------------------------------
# AC1 — 完整 --all 流水线，使用真实 reporter，验证文件生成
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """AC1: 完整 --all 流水线，所有 mock source 均生成 raw.md 和 validation.md"""

    def test_all_sources_generate_report_files(self, tmp_path: Path, monkeypatch) -> None:
        """8 个 mock source 运行完成后，每个 source 的 raw.md 和 validation.md 均已创建"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_sources = _make_all_mock_sources()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 0
        for source_name in mock_sources:
            assert (reports_dir / f"{source_name}-raw.md").exists(), \
                f"{source_name}-raw.md 未生成"
            assert (reports_dir / f"{source_name}-validation.md").exists(), \
                f"{source_name}-validation.md 未生成"

    def test_raw_md_contains_field_table(self, tmp_path: Path, monkeypatch) -> None:
        """raw.md 包含 extract_fields 返回的字段信息"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_sources = {
            "youtube": _make_mock_source(
                fields=[{
                    "field_name": "videoId",
                    "data_type": "string",
                    "sample_value": "dQw4w9WgXcQ",
                    "nullable": False,
                }]
            )
        }
        with (
            patch("sys.argv", ["validate.py", "--source", "youtube"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 0
        raw_content = (reports_dir / "youtube-raw.md").read_text(encoding="utf-8")
        assert "videoId" in raw_content
        assert "dQw4w9WgXcQ" in raw_content
        assert "实际返回字段" in raw_content

    def test_triplewhale_generates_report_with_table_name(self, tmp_path: Path, monkeypatch) -> None:
        """triplewhale 多表路由：raw.md 包含表名信息"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_sources = {"triplewhale": _make_mock_source()}
        with (
            patch("sys.argv", ["validate.py", "--source", "triplewhale"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 0
        raw_content = (reports_dir / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "pixel_orders_table" in raw_content
        assert (reports_dir / "triplewhale-validation.md").exists()


# ---------------------------------------------------------------------------
# AC2 — authenticate() 返回 False：跳过 fetch_sample，其余继续，退出码 1
# ---------------------------------------------------------------------------

class TestAuthFailureIsolation:
    """AC2: authenticate() 返回 False → 跳过 fetch_sample，标记失败，其余继续，退出码 1"""

    def test_auth_false_skips_fetch_and_marks_failed(self, tmp_path: Path, monkeypatch) -> None:
        """authenticate 失败的 source 不生成报告，其余正常生成"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_sources = _make_all_mock_sources(
            override={"dingtalk": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 1
        # dingtalk authenticate 失败，fetch_sample 不应被调用
        mock_sources["dingtalk"].fetch_sample.assert_not_called()
        # dingtalk 未生成任何报告文件（raw.md 和 validation.md 均不应存在）
        assert not (reports_dir / "dingtalk-raw.md").exists()
        assert not (reports_dir / "dingtalk-validation.md").exists()
        # triplewhale（dingtalk 之前）报告应正常生成
        assert (reports_dir / "triplewhale-raw.md").exists()

    def test_sources_after_auth_failure_continue(self, tmp_path: Path, monkeypatch) -> None:
        """dingtalk auth 失败后，其后的 source（youtube、awin 等）仍继续执行"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_sources = _make_all_mock_sources(
            override={"dingtalk": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit),
        ):
            validate.main()

        # dingtalk 之后的所有 source 应正常生成报告
        for source_name in ["youtube", "awin", "cartsee", "partnerboost", "social_media"]:
            assert (reports_dir / f"{source_name}-raw.md").exists(), \
                f"{source_name} 应在 dingtalk 失败后继续生成报告"


# ---------------------------------------------------------------------------
# AC3 — fetch_sample() 抛异常：标记失败，其余不受影响，退出码 1
# ---------------------------------------------------------------------------

class TestFetchExceptionIsolation:
    """AC3: fetch_sample() 抛异常 → 标记失败，其余继续，退出码 1"""

    def test_fetch_exception_marks_source_failed(
        self, tmp_path: Path, monkeypatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """fetch_sample 抛异常的 source 不生成报告，退出码 1，且错误信息被记录到日志"""
        import logging

        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_sources = _make_all_mock_sources(
            override={"awin": _make_mock_source(fetch_exception=RuntimeError("连接超时"))}
        )
        with caplog.at_level(logging.ERROR):
            with (
                patch("sys.argv", ["validate.py", "--all"]),
                patch("validate.SOURCES", mock_sources),
                patch("validate.get_credentials", return_value={}),
                patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
                pytest.raises(SystemExit) as exc_info,
            ):
                validate.main()

        assert exc_info.value.code == 1
        # awin 未生成报告
        assert not (reports_dir / "awin-raw.md").exists()
        # AC3: 完整错误信息（含异常类型和消息）被记录到日志
        error_logs = [r.message for r in caplog.records if r.levelno >= logging.ERROR]
        assert any("awin" in msg and "连接超时" in msg for msg in error_logs), \
            f"日志中未找到 awin 的完整错误信息，实际日志：{error_logs}"

    def test_sources_after_fetch_exception_continue(self, tmp_path: Path, monkeypatch) -> None:
        """awin fetch_sample 抛异常后，cartsee 和 partnerboost 仍正常执行"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_sources = _make_all_mock_sources(
            override={"awin": _make_mock_source(fetch_exception=ConnectionError("网络错误"))}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit),
        ):
            validate.main()

        # awin 之后的 source 应正常生成报告
        assert (reports_dir / "cartsee-raw.md").exists(), "cartsee 应在 awin 异常后继续"
        assert (reports_dir / "partnerboost-raw.md").exists(), "partnerboost 应在 awin 异常后继续"


# ---------------------------------------------------------------------------
# AC4 — validation.md 人工标注保护：raw.md 覆盖，validation.md 不变
# ---------------------------------------------------------------------------

class TestValidationReportProtection:
    """AC4: validation.md 已存在时不被覆盖，raw.md 每次覆盖更新"""

    def test_existing_validation_md_not_overwritten(self, tmp_path: Path, monkeypatch) -> None:
        """已有人工标注的 validation.md 在再次运行后内容保持不变"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        # 预先创建含人工标注内容的 validation.md
        human_annotation = "# 人工已完成对标\n\n| 字段 | 状态 |\n|------|------|\n| test_field | ✅ 直接可用 |\n"
        validation_path = reports_dir / "youtube-validation.md"
        validation_path.write_text(human_annotation, encoding="utf-8")

        mock_sources = {"youtube": _make_mock_source()}
        with (
            patch("sys.argv", ["validate.py", "--source", "youtube"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 0
        # validation.md 内容完整保留（人工标注未被覆盖）
        assert validation_path.read_text(encoding="utf-8") == human_annotation, \
            "validation.md 人工标注被覆盖！"
        # raw.md 已生成
        assert (reports_dir / "youtube-raw.md").exists()

    def test_raw_md_overwritten_on_second_run(self, tmp_path: Path, monkeypatch) -> None:
        """同一 source 运行两次，raw.md 内容为最新字段数据（旧内容被覆盖）"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        # 第一次运行
        mock_src_v1 = _make_mock_source(
            fields=[{"field_name": "field_v1", "data_type": "string",
                     "sample_value": "val_one", "nullable": False}]
        )
        with (
            patch("sys.argv", ["validate.py", "--source", "tiktok"]),
            patch("validate.SOURCES", {"tiktok": mock_src_v1}),
            patch("validate.get_credentials", return_value={}),
            pytest.raises(SystemExit),
        ):
            validate.main()

        first_content = (reports_dir / "tiktok-raw.md").read_text(encoding="utf-8")
        assert "field_v1" in first_content

        # 第二次运行，返回不同字段
        mock_src_v2 = _make_mock_source(
            fields=[{"field_name": "field_v2", "data_type": "number",
                     "sample_value": 9527, "nullable": True}]
        )
        with (
            patch("sys.argv", ["validate.py", "--source", "tiktok"]),
            patch("validate.SOURCES", {"tiktok": mock_src_v2}),
            patch("validate.get_credentials", return_value={}),
            pytest.raises(SystemExit),
        ):
            validate.main()

        second_content = (reports_dir / "tiktok-raw.md").read_text(encoding="utf-8")
        assert "field_v2" in second_content
        assert "field_v1" not in second_content, "第一次运行的旧字段不应出现在第二次报告中"


# ---------------------------------------------------------------------------
# AC5 — 无需真实凭证（本文件所有测试均不带 integration marker）
# ---------------------------------------------------------------------------

class TestNoRealCredentialsRequired:
    """AC5: 全部测试无需真实 API 凭证或网络连接"""

    def test_full_all_pipeline_no_real_credentials(self, tmp_path: Path, monkeypatch) -> None:
        """完整 --all 流水线在 mock 环境下正常运行，不需要真实 .env 文件"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_sources = _make_all_mock_sources()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        # 无需真实凭证，全部 source 均成功
        assert exc_info.value.code == 0
        assert (reports_dir / "triplewhale-raw.md").exists()
        assert (reports_dir / "tiktok-raw.md").exists()
