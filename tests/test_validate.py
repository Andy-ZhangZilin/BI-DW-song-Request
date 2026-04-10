"""test_validate.py — validate.py CLI 入口与调度器单元测试

覆盖 AC：
AC1 - --source triplewhale：仅 triplewhale 被调用，退出码 0
AC2 - --all：所有 source 被调用，退出码 0（全部成功时）
AC3 - 单源 fetch_sample 抛出异常：该源标记失败，其余继续
AC4 - 全部成功 → exit 0；任一失败 → exit 1
AC5 - --help：argparse 输出含 --source 和 --all
AC6 - get_credentials 抛 ValueError → sys.exit(1)，不进入调度循环
AC7 - social_media 抛 NotImplementedError：被捕获，其余继续，退出码 1
AC8 - --all 模式生成聚合结论文档
"""
import sys
from unittest.mock import MagicMock, patch, call

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


# 真实 SOURCES 注册表（字符串值）
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
    """创建全部 10 个 source 的 mock 模块映射（module_path -> mock_module）。"""
    modules = {}
    for name, path in REAL_SOURCES.items():
        mock = _make_mock_source()
        if name == "triplewhale":
            mock.TABLES = ["default_table"]
            mock.fetch_data_profile.return_value = {
                "table_name": "default_table",
                "date_column": None,
                "earliest_date": None,
                "total_rows": 0,
            }
        elif name == "tiktok":
            mock.TABLES = ["default_table"]
        modules[path] = mock
    if override:
        for name, mock_src in override.items():
            modules[REAL_SOURCES[name]] = mock_src
    return modules


def _make_import_patcher(mock_modules: dict):
    """创建一个 import_module 的 side_effect 函数。"""
    def _import(module_path):
        if module_path in mock_modules:
            return mock_modules[module_path]
        raise ImportError(f"No mock for {module_path}")
    return _import


# ---------------------------------------------------------------------------
# AC5 — --help 输出包含 --source 和 --all
# ---------------------------------------------------------------------------

class TestHelpOutput:

    def test_help_contains_source_and_all(self, capsys: pytest.CaptureFixture) -> None:
        import validate
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["validate.py", "--help"]):
                validate.main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--source" in captured.out
        assert "--all" in captured.out

    def test_sources_registry_has_10_entries(self) -> None:
        import validate
        assert "triplewhale" in validate.SOURCES
        assert "social_media" in validate.SOURCES
        assert len(validate.SOURCES) == 10


# ---------------------------------------------------------------------------
# AC6 — get_credentials 失败 → 快速退出
# ---------------------------------------------------------------------------

class TestCredentialsFastFail:

    def test_credentials_failure_exits_with_code_1(self) -> None:
        import validate
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch(
                "validate.get_credentials",
                side_effect=ValueError("缺少以下必需凭证"),
            ),
            patch("validate.reporter"),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()
        assert exc_info.value.code == 1

    def test_credentials_failure_no_import(self) -> None:
        """凭证失败时，不应尝试导入任何 source 模块。"""
        import validate
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch(
                "validate.get_credentials",
                side_effect=ValueError("缺少凭证"),
            ),
            patch("validate.reporter"),
            patch("validate.importlib.import_module") as mock_import,
            pytest.raises(SystemExit),
        ):
            validate.main()

        mock_import.assert_not_called()


# ---------------------------------------------------------------------------
# AC1 — --source 单源运行
# ---------------------------------------------------------------------------

class TestSingleSource:

    def test_source_tiktok_exit_0(self) -> None:
        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--source", "tiktok"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 0
        mock_modules["sources.tiktok"].authenticate.assert_called_once()
        mock_modules["sources.triplewhale"].authenticate.assert_not_called()

    def test_unknown_source_exits_1(self) -> None:
        with (
            patch("sys.argv", ["validate.py", "--source", "unknown_source"]),
            patch("validate.get_credentials", return_value={}),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1

    def test_single_source_no_aggregate(self) -> None:
        """--source 模式不生成聚合文档（不调用 write_aggregate_report）。"""
        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--source", "youtube"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter") as mock_reporter,
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit),
        ):
            import validate
            validate.main()

        mock_reporter.write_aggregate_report.assert_not_called()

    def test_single_source_calls_update_aggregate(self) -> None:
        """--source 模式成功后调用 update_aggregate_source 更新聚合文档。"""
        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--source", "youtube_url"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter") as mock_reporter,
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit),
        ):
            import validate
            validate.main()

        mock_reporter.update_aggregate_source.assert_called_once()
        call_args = mock_reporter.update_aggregate_source.call_args
        assert call_args[0][0] == "youtube_url"


# ---------------------------------------------------------------------------
# AC2 / AC4 — --all 全部成功，退出码 0
# ---------------------------------------------------------------------------

class TestAllSources:

    def test_all_sources_called_on_all_flag(self) -> None:
        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 0
        for path, mock_src in mock_modules.items():
            mock_src.authenticate.assert_called_once(), f"{path}.authenticate 应被调用"


# ---------------------------------------------------------------------------
# AC8 — --all 模式生成聚合结论文档
# ---------------------------------------------------------------------------

class TestAggregateReport:

    def test_all_mode_generates_aggregate(self) -> None:
        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter") as mock_reporter,
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit),
        ):
            import validate
            validate.main()

        mock_reporter.write_aggregate_report.assert_called_once()

    def test_aggregate_receives_all_source_keys(self) -> None:
        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter") as mock_reporter,
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit),
        ):
            import validate
            validate.main()

        args = mock_reporter.write_aggregate_report.call_args[0][0]
        assert isinstance(args, dict)
        assert len(args) == len(REAL_SOURCES)
        for source_name in REAL_SOURCES:
            assert source_name in args


# ---------------------------------------------------------------------------
# AC3 / AC4 — 单源失败，其余继续，退出码 1
# ---------------------------------------------------------------------------

class TestFailureIsolation:

    def test_fetch_exception_does_not_stop_others(self, tmp_path, monkeypatch) -> None:
        # 切换到空目录，确保无历史 raw 文件触发回退逻辑
        monkeypatch.chdir(tmp_path)
        mock_modules = _make_mock_modules(
            override={"dingtalk": _make_mock_source(fetch_exception=RuntimeError("网络超时"))}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1
        for name in ["triplewhale", "tiktok", "youtube", "awin"]:
            mock_modules[REAL_SOURCES[name]].authenticate.assert_called_once(), \
                f"{name} 应在 dingtalk 失败后继续被调用"

    def test_authenticate_false_marks_source_failed(self, tmp_path, monkeypatch) -> None:
        # 切换到空目录，确保无历史 raw 文件触发回退逻辑
        monkeypatch.chdir(tmp_path)
        mock_modules = _make_mock_modules(
            override={"youtube": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1
        mock_modules["sources.youtube"].fetch_sample.assert_not_called()

    def test_all_success_exits_0(self) -> None:
        mock_modules = _make_mock_modules()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 0

    def test_single_source_failure_exits_1(self) -> None:
        mock_modules = _make_mock_modules(
            override={"tiktok": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--source", "tiktok"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# AC7 — social_media NotImplementedError 被捕获
# ---------------------------------------------------------------------------

class TestSocialMediaStub:

    def test_social_media_not_implemented_caught(self) -> None:
        mock_modules = _make_mock_modules(
            override={
                "social_media": _make_mock_source(
                    auth_exception=NotImplementedError("social_media: 暂未实现")
                )
            }
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1
        mock_modules["sources.triplewhale"].authenticate.assert_called_once()
        mock_modules["sources.social_media"].authenticate.assert_called_once()


# ---------------------------------------------------------------------------
# 优化2 — --all 模式下失败时检查历史 raw 文件
# ---------------------------------------------------------------------------

class TestRawFileFallback:

    def test_failed_source_with_raw_file_marked_success(self, tmp_path, monkeypatch) -> None:
        """--all 模式下，source 失败但存在历史 raw 文件时，采集状态标记为已生成（历史数据）。"""
        # validate.py 用 Path("reports")/{source}-raw.md 检查文件；切换工作目录并预置文件
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "dingtalk-raw.md").write_text("# dingtalk raw", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        mock_modules = _make_mock_modules(
            override={"dingtalk": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        # dingtalk 失败但有 raw 文件，整体 exit 应为 0
        assert exc_info.value.code == 0

    def test_failed_source_without_raw_file_stays_failed(self, tmp_path, monkeypatch) -> None:
        """--all 模式下，source 失败且无历史 raw 文件时，采集状态仍为失败，退出码 1。"""
        reports = tmp_path / "reports"
        reports.mkdir()
        # 不创建 dingtalk-raw.md
        monkeypatch.chdir(tmp_path)

        mock_modules = _make_mock_modules(
            override={"dingtalk": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1

    def test_single_source_no_raw_fallback(self) -> None:
        """--source 模式下，失败时不检查历史 raw 文件（该优化仅针对 --all）。"""
        mock_modules = _make_mock_modules(
            override={"youtube_url": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--source", "youtube_url"]),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.importlib.import_module", side_effect=_make_import_patcher(mock_modules)),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# _run_source 私有函数单元测试
# ---------------------------------------------------------------------------

class TestRunSource:

    def test_run_source_returns_success_dict(self) -> None:
        mock_src = _make_mock_source()
        with (
            patch("validate.reporter"),
            patch("validate.importlib.import_module", return_value=mock_src),
        ):
            import validate
            result = validate._run_source("youtube", "sources.youtube")
        assert result["success"] is True
        assert result["status"] == "已生成"
        assert result["error"] is None
        assert "youtube" in result["fields"]

    def test_run_source_returns_failure_on_auth(self) -> None:
        mock_src = _make_mock_source(auth_result=False)
        with (
            patch("validate.reporter"),
            patch("validate.importlib.import_module", return_value=mock_src),
        ):
            import validate
            result = validate._run_source("youtube", "sources.youtube")
        assert result["success"] is False
        assert result["status"] == "认证失败"
        mock_src.fetch_sample.assert_not_called()

    def test_run_source_returns_failure_on_exception(self) -> None:
        mock_src = _make_mock_source(fetch_exception=ConnectionError("连接超时"))
        with (
            patch("validate.reporter"),
            patch("validate.importlib.import_module", return_value=mock_src),
        ):
            import validate
            result = validate._run_source("awin", "sources.awin")
        assert result["success"] is False
        assert "ConnectionError" in result["status"]

    def test_run_source_collects_fields(self) -> None:
        expected_fields = [
            {"field_name": "f1", "data_type": "string", "sample_value": "v1", "nullable": False}
        ]
        mock_src = _make_mock_source(fields=expected_fields)
        with (
            patch("validate.reporter"),
            patch("validate.importlib.import_module", return_value=mock_src),
        ):
            import validate
            result = validate._run_source("dingtalk", "sources.dingtalk")
        assert result["fields"]["dingtalk"] == expected_fields
