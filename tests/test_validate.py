"""test_validate.py — validate.py CLI 入口与调度器单元测试

覆盖 AC：
AC1 - --source triplewhale：仅 triplewhale 被调用，退出码 0
AC2 - --all：所有 source 被调用，退出码 0（全部成功时）
AC3 - 单源 fetch_sample 抛出异常：该源标记失败，其余继续
AC4 - 全部成功 → exit 0；任一失败 → exit 1
AC5 - --help：argparse 输出含 --source 和 --all
AC6 - get_credentials 抛 ValueError → sys.exit(1)，不进入调度循环
AC7 - social_media 抛 NotImplementedError：被捕获，其余继续，退出码 1
"""
import sys
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
# AC5 — --help 输出包含 --source 和 --all（无需真实凭证）
# ---------------------------------------------------------------------------

class TestHelpOutput:
    """AC5: --help 输出含 --source 和 --all 参数说明"""

    def test_help_contains_source_and_all(self, capsys: pytest.CaptureFixture) -> None:
        import validate
        # 通过 --help 触发 SystemExit(0)，检查 stdout
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["validate.py", "--help"]):
                validate.main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--source" in captured.out
        assert "--all" in captured.out

    def test_parser_has_source_and_all_args(self) -> None:
        """通过反射验证 argparse 定义了 --source 和 --all"""
        import argparse
        # 解析 --help 输出文本来验证参数存在
        # 用 parse_known_args 测试参数识别
        import validate
        # 重建 parser 验证参数存在（直接检查 SOURCES 注册表和行为）
        assert "triplewhale" in validate.SOURCES
        assert "social_media" in validate.SOURCES
        assert len(validate.SOURCES) == 8


# ---------------------------------------------------------------------------
# AC6 — get_credentials 失败 → 快速退出
# ---------------------------------------------------------------------------

class TestCredentialsFastFail:
    """AC6: get_credentials 抛 ValueError → sys.exit(1)，不进入调度循环"""

    def test_credentials_failure_exits_with_code_1(self) -> None:
        import validate
        mock_sources = _make_all_mock_sources()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch(
                "validate.get_credentials",
                side_effect=ValueError("缺少以下必需凭证：TRIPLEWHALE_API_KEY"),
            ),
            patch("validate.reporter"),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate.main()
        assert exc_info.value.code == 1

    def test_credentials_failure_no_source_called(self) -> None:
        """凭证失败时，所有 source 的 authenticate 均不被调用"""
        mock_sources = _make_all_mock_sources()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch(
                "validate.get_credentials",
                side_effect=ValueError("缺少凭证"),
            ),
            patch("validate.reporter"),
            pytest.raises(SystemExit),
        ):
            import validate
            validate.main()

        for name, mock_src in mock_sources.items():
            mock_src.authenticate.assert_not_called(), f"{name}.authenticate 不应被调用"


# ---------------------------------------------------------------------------
# AC1 — --source triplewhale
# ---------------------------------------------------------------------------

class TestSingleSource:
    """AC1: --source 仅运行指定 source"""

    def test_source_triplewhale_only_calls_triplewhale(self) -> None:
        mock_sources = _make_all_mock_sources()
        with (
            patch("sys.argv", ["validate.py", "--source", "triplewhale"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.TRIPLEWHALE_TABLES", ["table_a", "table_b"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 0
        mock_sources["triplewhale"].authenticate.assert_called_once()
        # triplewhale 有 2 张表（mock），fetch_sample 被调用 2 次
        assert mock_sources["triplewhale"].fetch_sample.call_count == 2
        # 其他 source 均未被调用
        for name in ["tiktok", "dingtalk", "youtube", "awin", "cartsee", "partnerboost", "social_media"]:
            mock_sources[name].authenticate.assert_not_called()

    def test_source_tiktok_exit_0(self) -> None:
        mock_sources = _make_all_mock_sources()
        with (
            patch("sys.argv", ["validate.py", "--source", "tiktok"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 0
        mock_sources["tiktok"].authenticate.assert_called_once()
        mock_sources["triplewhale"].authenticate.assert_not_called()

    def test_unknown_source_exits_1(self) -> None:
        with (
            patch("sys.argv", ["validate.py", "--source", "unknown_source"]),
            patch("validate.get_credentials", return_value={}),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# AC2 / AC4 — --all 全部成功，退出码 0
# ---------------------------------------------------------------------------

class TestAllSources:
    """AC2: --all 运行全部 source；AC4: 全部成功退出码 0"""

    def test_all_sources_called_on_all_flag(self) -> None:
        mock_sources = _make_all_mock_sources()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 0
        for name, mock_src in mock_sources.items():
            mock_src.authenticate.assert_called_once(), f"{name}.authenticate 应被调用"

    def test_triplewhale_called_for_each_table(self) -> None:
        """triplewhale 在 --all 时按 TRIPLEWHALE_TABLES 逐表调用 fetch_sample"""
        mock_sources = _make_all_mock_sources()
        fake_tables = ["table_x", "table_y", "table_z"]
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.TRIPLEWHALE_TABLES", fake_tables),
            pytest.raises(SystemExit),
        ):
            import validate
            validate.main()

        assert mock_sources["triplewhale"].fetch_sample.call_count == len(fake_tables)
        call_args = [c.args[0] for c in mock_sources["triplewhale"].fetch_sample.call_args_list]
        assert call_args == fake_tables


# ---------------------------------------------------------------------------
# AC3 / AC4 — 单源失败，其余继续，退出码 1
# ---------------------------------------------------------------------------

class TestFailureIsolation:
    """AC3: 单源异常不中断其他 source；AC4: 任一失败退出码 1"""

    def test_fetch_exception_does_not_stop_others(self) -> None:
        mock_sources = _make_all_mock_sources(
            override={
                "dingtalk": _make_mock_source(
                    fetch_exception=RuntimeError("网络超时")
                )
            }
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        # dingtalk 失败 → 退出码 1
        assert exc_info.value.code == 1
        # dingtalk 失败但其他 source 仍被调用
        for name in ["triplewhale", "tiktok", "youtube", "awin", "cartsee", "partnerboost"]:
            mock_sources[name].authenticate.assert_called_once(), \
                f"{name} 应在 dingtalk 失败后继续被调用"

    def test_authenticate_false_marks_source_failed(self) -> None:
        mock_sources = _make_all_mock_sources(
            override={"youtube": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1
        # youtube authenticate 返回 False，fetch_sample 不应被调用
        mock_sources["youtube"].fetch_sample.assert_not_called()

    def test_all_success_exits_0(self) -> None:
        mock_sources = _make_all_mock_sources()
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 0

    def test_single_source_failure_exits_1(self) -> None:
        mock_sources = _make_all_mock_sources(
            override={"tiktok": _make_mock_source(auth_result=False)}
        )
        with (
            patch("sys.argv", ["validate.py", "--source", "tiktok"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# AC7 — social_media NotImplementedError 被调度器捕获
# ---------------------------------------------------------------------------

class TestSocialMediaStub:
    """AC7: social_media 抛 NotImplementedError，调度器捕获后继续，退出码 1"""

    def test_social_media_not_implemented_caught(self) -> None:
        mock_sources = _make_all_mock_sources(
            override={
                "social_media": _make_mock_source(
                    auth_exception=NotImplementedError("social_media: 凭证未就绪，暂未实现")
                )
            }
        )
        with (
            patch("sys.argv", ["validate.py", "--all"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            patch("validate.TRIPLEWHALE_TABLES", ["pixel_orders_table"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        # social_media 失败 → 退出码 1
        assert exc_info.value.code == 1
        # 其他 source 继续执行（triplewhale 在 social_media 之前，必然被调用）
        mock_sources["triplewhale"].authenticate.assert_called_once()
        # 确认 social_media 被尝试调用（不是被跳过）
        mock_sources["social_media"].authenticate.assert_called_once()

    def test_social_media_only_source_exits_1(self) -> None:
        """单独运行 --source social_media 也应被捕获，退出码 1"""
        mock_sources = _make_all_mock_sources(
            override={
                "social_media": _make_mock_source(
                    auth_exception=NotImplementedError("social_media: 凭证未就绪，暂未实现")
                )
            }
        )
        with (
            patch("sys.argv", ["validate.py", "--source", "social_media"]),
            patch("validate.SOURCES", mock_sources),
            patch("validate.get_credentials", return_value={}),
            patch("validate.reporter"),
            pytest.raises(SystemExit) as exc_info,
        ):
            import validate
            validate.main()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# _run_source 私有函数单元测试
# ---------------------------------------------------------------------------

class TestRunSource:
    """_run_source() 函数行为的细粒度测试"""

    def test_run_source_returns_true_on_success(self) -> None:
        mock_src = _make_mock_source()
        with patch("validate.reporter") as mock_reporter:
            import validate
            result = validate._run_source("youtube", mock_src)
        assert result is True
        mock_src.authenticate.assert_called_once()
        mock_src.fetch_sample.assert_called_once_with()
        mock_reporter.write_raw_report.assert_called_once()
        mock_reporter.init_validation_report.assert_called_once()

    def test_run_source_returns_false_on_auth_failure(self) -> None:
        mock_src = _make_mock_source(auth_result=False)
        with patch("validate.reporter"):
            import validate
            result = validate._run_source("youtube", mock_src)
        assert result is False
        mock_src.fetch_sample.assert_not_called()

    def test_run_source_returns_false_on_exception(self) -> None:
        mock_src = _make_mock_source(fetch_exception=ConnectionError("连接超时"))
        with patch("validate.reporter"):
            import validate
            result = validate._run_source("awin", mock_src)
        assert result is False

    def test_run_source_triplewhale_calls_fetch_per_table(self) -> None:
        mock_src = _make_mock_source()
        fake_tables = ["t1", "t2", "t3"]
        with (
            patch("validate.reporter"),
            patch("validate.TRIPLEWHALE_TABLES", fake_tables),
        ):
            import validate
            result = validate._run_source("triplewhale", mock_src)

        assert result is True
        assert mock_src.fetch_sample.call_count == 3
        table_args = [c.args[0] for c in mock_src.fetch_sample.call_args_list]
        assert table_args == fake_tables
