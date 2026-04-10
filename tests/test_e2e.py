"""test_e2e.py — Story 5.2 端到端集成验证测试

与 test_validate.py 的关键区别：
- test_validate.py：reporter 完全 mock（无文件 I/O），只验证 validate.py 调度逻辑
- test_e2e.py：使用真实 reporter（patch REPORTS_DIR 到 tmp_path），验证完整 validate → reporter → 文件 全链路

覆盖 AC：
AC1 - 完整 --all 流水线：10 个 mock source 均生成 raw.md，并生成聚合文档
AC2 - authenticate() 返回 False：跳过 fetch_sample，标记失败，其余继续，退出码 1
AC3 - fetch_sample() 抛出异常：标记失败，其余继续，退出码 1
AC4 - raw.md 每次覆盖更新
AC5 - pytest tests/ -m "not integration" 全部通过，无需真实凭证
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 辅助工厂
# ---------------------------------------------------------------------------

def _make_mock_source(
    auth_result: bool = True,
    sample: list | None = None,
    fields: list | None = None,
    fetch_exception: Exception | None = None,
    auth_exception: Exception | None = None,
) -> MagicMock:
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


# 真实 SOURCES 注册表
REAL_SOURCES = {
    "triplewhale": "sources.triplewhale",
    "tiktok": "sources.tiktok",
    "dingtalk": "sources.dingtalk",
    "youtube": "sources.youtube",
    "youtube_url": "sources.youtube_url",
    "awin": "sources.awin",
    "cartsee": "sources.cartsee",
    "partnerboost": "sources.partnerboost",
    "social_media": "sources.social_media",
    "youtube_studio": "sources.youtube_studio",
}


def _make_mock_modules(override: dict | None = None) -> dict:
    """module_path -> mock_module 映射。"""
    modules = {}
    for name, path in REAL_SOURCES.items():
        mock = _make_mock_source()
        # triplewhale / tiktok 走多表分支，需要 TABLES 属性
        if name == "triplewhale":
            mock.TABLES = ["default_table"]
            mock.fetch_data_profile.return_value = {
                "table_name": "default_table",
                "date_column": None,
                "earliest_date": None,
                "total_rows": 0,
                "rate_limit_rpm": None,
                "max_rows_per_request": None,
                "estimated_pull_minutes": None,
            }
        elif name == "tiktok":
            mock.TABLES = ["default_table"]
        modules[path] = mock
    if override:
        for name, mock_src in override.items():
            modules[REAL_SOURCES[name]] = mock_src
    return modules


def _make_import_patcher(mock_modules: dict):
    def _import(module_path):
        if module_path in mock_modules:
            return mock_modules[module_path]
        raise ImportError(f"No mock for {module_path}")
    return _import


# ---------------------------------------------------------------------------
# AC1 — 完整 --all 流水线，使用真实 reporter，验证文件生成
# ---------------------------------------------------------------------------

class TestFullPipeline:

    def test_all_sources_generate_raw_md(self, tmp_path: Path, monkeypatch) -> None:
        """10 个 mock source 运行完成后，每个 source 的 raw.md 均已创建"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 0
        for source_name in REAL_SOURCES:
            assert (reports_dir / f"{source_name}-raw.md").exists(), \
                f"{source_name}-raw.md 未生成"

    def test_all_generates_aggregate_doc(self, tmp_path: Path, monkeypatch) -> None:
        """--all 模式生成聚合结论文档"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit),
        ):
            validate.main()

        aggregate_path = reports_dir / "all-sources-aggregate.md"
        assert aggregate_path.exists(), "聚合结论文档未生成"
        content = aggregate_path.read_text(encoding="utf-8")
        assert "Part 1" in content
        assert "Part 2" in content
        assert "Part 3" in content
        assert "Part 4" in content

    def test_raw_md_contains_field_table(self, tmp_path: Path, monkeypatch) -> None:
        """raw.md 包含 extract_fields 返回的字段信息"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_youtube = _make_mock_source(
            fields=[{
                "field_name": "videoId",
                "data_type": "string",
                "sample_value": "dQw4w9WgXcQ",
                "nullable": False,
            }]
        )
        mock_modules = {"sources.youtube": mock_youtube}
        with (
            patch("sys.argv", ["validate.py", "--source", "youtube"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 0
        raw_content = (reports_dir / "youtube-raw.md").read_text(encoding="utf-8")
        assert "videoId" in raw_content
        assert "dQw4w9WgXcQ" in raw_content

    def test_triplewhale_generates_report_with_table_name(self, tmp_path: Path, monkeypatch) -> None:
        """triplewhale 多表路由：raw.md 包含表名信息"""
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_tw = _make_mock_source()
        mock_tw.TABLES = ["pixel_orders_table"]
        mock_tw.fetch_data_profile.return_value = {
            "table_name": "pixel_orders_table",
            "date_column": None,
            "earliest_date": None,
            "total_rows": 0,
            "rate_limit_rpm": None,
            "max_rows_per_request": None,
            "estimated_pull_minutes": None,
        }
        mock_modules = {"sources.triplewhale": mock_tw}
        with (
            patch("sys.argv", ["validate.py", "--source", "triplewhale"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 0
        raw_content = (reports_dir / "triplewhale-raw.md").read_text(encoding="utf-8")
        assert "pixel_orders_table" in raw_content


# ---------------------------------------------------------------------------
# AC2 — authenticate() 返回 False
# ---------------------------------------------------------------------------

class TestAuthFailureIsolation:

    def test_auth_false_skips_fetch_and_marks_failed(self, tmp_path: Path, monkeypatch) -> None:
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")
        # 切换到空目录，确保无历史 raw 文件触发回退逻辑
        monkeypatch.chdir(tmp_path)

        mock_modules = _make_mock_modules(
            override={"dingtalk": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 1
        mock_modules["sources.dingtalk"].fetch_sample.assert_not_called()
        assert not (reports_dir / "dingtalk-raw.md").exists()
        assert (reports_dir / "triplewhale-raw.md").exists()

    def test_sources_after_auth_failure_continue(self, tmp_path: Path, monkeypatch) -> None:
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_modules = _make_mock_modules(
            override={"dingtalk": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit),
        ):
            validate.main()

        for source_name in ["youtube", "awin", "cartsee", "partnerboost", "social_media"]:
            assert (reports_dir / f"{source_name}-raw.md").exists(), \
                f"{source_name} 应在 dingtalk 失败后继续生成报告"


# ---------------------------------------------------------------------------
# AC3 — fetch_sample() 抛异常
# ---------------------------------------------------------------------------

class TestFetchExceptionIsolation:

    def test_fetch_exception_marks_source_failed(
        self, tmp_path: Path, monkeypatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")
        # 切换到空目录，确保无历史 raw 文件触发回退逻辑
        monkeypatch.chdir(tmp_path)

        mock_modules = _make_mock_modules(
            override={"awin": _make_mock_source(fetch_exception=RuntimeError("连接超时"))}
        )
        with caplog.at_level(logging.ERROR):
            with (
                patch("sys.argv", ["validate.py", "--all"]),
                patch("validate.get_credentials", return_value={}),
                patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
                pytest.raises(SystemExit) as exc_info,
            ):
                validate.main()

        assert exc_info.value.code == 1
        assert not (reports_dir / "awin-raw.md").exists()
        error_logs = [r.message for r in caplog.records if r.levelno >= logging.ERROR]
        assert any("awin" in msg and "连接超时" in msg for msg in error_logs)

    def test_sources_after_fetch_exception_continue(self, tmp_path: Path, monkeypatch) -> None:
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_modules = _make_mock_modules(
            override={"awin": _make_mock_source(fetch_exception=ConnectionError("网络错误"))}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit),
        ):
            validate.main()

        assert (reports_dir / "cartsee-raw.md").exists()
        assert (reports_dir / "partnerboost-raw.md").exists()


# ---------------------------------------------------------------------------
# AC4 — raw.md 每次覆盖更新
# ---------------------------------------------------------------------------

class TestRawReportOverwrite:

    def test_raw_md_overwritten_on_second_run(self, tmp_path: Path, monkeypatch) -> None:
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_v1 = _make_mock_source(
            fields=[{"field_name": "field_v1", "data_type": "string",
                     "sample_value": "val_one", "nullable": False}]
        )
        mock_v1.TABLES = ["default_table"]
        mock_modules_v1 = {"sources.tiktok": mock_v1}
        with (
            patch("sys.argv", ["validate.py", "--source", "tiktok"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules_v1)),
            pytest.raises(SystemExit),
        ):
            validate.main()

        first_content = (reports_dir / "tiktok-raw.md").read_text(encoding="utf-8")
        assert "field_v1" in first_content

        mock_v2 = _make_mock_source(
            fields=[{"field_name": "field_v2", "data_type": "number",
                     "sample_value": 9527, "nullable": True}]
        )
        mock_v2.TABLES = ["default_table"]
        mock_modules_v2 = {"sources.tiktok": mock_v2}
        with (
            patch("sys.argv", ["validate.py", "--source", "tiktok"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules_v2)),
            pytest.raises(SystemExit),
        ):
            validate.main()

        second_content = (reports_dir / "tiktok-raw.md").read_text(encoding="utf-8")
        assert "field_v2" in second_content
        assert "field_v1" not in second_content


# ---------------------------------------------------------------------------
# AC5 — 无需真实凭证
# ---------------------------------------------------------------------------

class TestNoRealCredentialsRequired:

    def test_full_all_pipeline_no_real_credentials(self, tmp_path: Path, monkeypatch) -> None:
        import reporter as reporter_module
        import validate

        reports_dir = tmp_path / "reports"
        monkeypatch.setattr(reporter_module, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(reporter_module, "REQUIREMENTS_PATH", tmp_path / "nonexistent.yaml")

        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()

        assert exc_info.value.code == 0
        assert (reports_dir / "triplewhale-raw.md").exists()
        assert (reports_dir / "tiktok-raw.md").exists()
        assert (reports_dir / "all-sources-aggregate.md").exists()
