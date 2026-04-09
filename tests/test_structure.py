"""Story 1.1 结构验证测试：验证所有骨架文件和目录均已正确创建。"""
import importlib
import subprocess
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent.parent


class TestRequiredFilesExist:
    """AC#2：验证所有必需文件/目录存在"""

    def test_validate_py_exists(self):
        assert (ROOT / "validate.py").exists()

    def test_reporter_py_exists(self):
        assert (ROOT / "reporter.py").exists()

    def test_requirements_txt_exists(self):
        assert (ROOT / "requirements.txt").exists()

    def test_env_example_exists(self):
        assert (ROOT / ".env.example").exists()

    def test_gitignore_exists(self):
        assert (ROOT / ".gitignore").exists()

    def test_readme_exists(self):
        assert (ROOT / "README.md").exists()

    def test_config_init_exists(self):
        assert (ROOT / "config" / "__init__.py").exists()

    def test_config_credentials_exists(self):
        assert (ROOT / "config" / "credentials.py").exists()

    def test_config_field_requirements_yaml_exists(self):
        # 注意：下划线命名，不是连字符
        assert (ROOT / "config" / "field_requirements.yaml").exists()

    def test_sources_init_exists(self):
        assert (ROOT / "sources" / "__init__.py").exists()

    def test_reports_dir_exists(self):
        assert (ROOT / "reports").is_dir()

    def test_tests_init_exists(self):
        assert (ROOT / "tests" / "__init__.py").exists()

    def test_tests_conftest_exists(self):
        assert (ROOT / "tests" / "conftest.py").exists()

    def test_tests_fixtures_dir_exists(self):
        assert (ROOT / "tests" / "fixtures").is_dir()


class TestGitignore:
    """AC#3：验证 .gitignore 包含必要的排除项"""

    def _read_gitignore(self) -> str:
        return (ROOT / ".gitignore").read_text()

    def test_gitignore_excludes_dotenv(self):
        assert ".env" in self._read_gitignore()

    def test_gitignore_excludes_pycache(self):
        assert "__pycache__" in self._read_gitignore()

    def test_gitignore_excludes_pyc(self):
        assert "*.pyc" in self._read_gitignore()

    def test_gitignore_excludes_pytest_cache(self):
        assert ".pytest_cache" in self._read_gitignore()


class TestRequirementsTxt:
    """验证 requirements.txt 包含所有必要依赖"""

    def _read_requirements(self) -> str:
        return (ROOT / "requirements.txt").read_text().lower()

    def test_has_python_dotenv(self):
        assert "python-dotenv" in self._read_requirements()

    def test_has_requests(self):
        assert "requests" in self._read_requirements()

    def test_has_playwright(self):
        assert "playwright" in self._read_requirements()

    def test_has_pyyaml(self):
        assert "pyyaml" in self._read_requirements()

    def test_has_pytest(self):
        assert "pytest" in self._read_requirements()


class TestModuleImports:
    """验证核心模块可正常导入"""

    def test_config_credentials_importable(self):
        # 需要 sys.path 包含项目根目录
        import config.credentials  # noqa: F401

    def test_config_credentials_has_get_credentials(self):
        import config.credentials
        assert hasattr(config.credentials, "get_credentials")
        assert callable(config.credentials.get_credentials)

    def test_reporter_importable(self):
        import reporter  # noqa: F401

    def test_reporter_has_write_raw_report(self):
        import reporter
        assert hasattr(reporter, "write_raw_report")
        assert callable(reporter.write_raw_report)

    def test_reporter_has_write_aggregate_report(self):
        import reporter
        assert hasattr(reporter, "write_aggregate_report")
        assert callable(reporter.write_aggregate_report)


class TestValidateCLI:
    """AC#1：验证 validate.py --help 可正常执行"""

    def test_validate_help_exits_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "validate.py"), "--help"],
            capture_output=True,
            text=True,
        )
        # argparse --help 正常退出码为 0
        assert result.returncode == 0

    def test_validate_help_shows_source_option(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "validate.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert "--source" in result.stdout

    def test_validate_help_shows_all_option(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "validate.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert "--all" in result.stdout


class TestEnvExample:
    """验证 .env.example 包含所有必需凭证键名"""

    def _read_env_example(self) -> str:
        return (ROOT / ".env.example").read_text()

    def test_has_triplewhale_key(self):
        assert "TRIPLEWHALE_API_KEY" in self._read_env_example()

    def test_has_tiktok_app_key(self):
        assert "TIKTOK_APP_KEY" in self._read_env_example()

    def test_has_dingtalk_keys(self):
        content = self._read_env_example()
        assert "DINGTALK_APP_KEY" in content
        assert "DINGTALK_APP_SECRET" in content

    def test_has_youtube_key(self):
        assert "YOUTUBE_API_KEY" in self._read_env_example()


class TestCredentialKeysSync:
    """验证 _REQUIRED_KEYS 与 TEST_CREDENTIALS 键集保持同步"""

    def test_test_credentials_keys_match_required_keys(self):
        """防止新增凭证时 fixture 静默漏掉对应键。"""
        from config.credentials import _REQUIRED_KEYS
        from tests.conftest import TEST_CREDENTIALS
        assert set(TEST_CREDENTIALS.keys()) == set(_REQUIRED_KEYS), (
            f"TEST_CREDENTIALS 与 _REQUIRED_KEYS 不同步。\n"
            f"缺少: {set(_REQUIRED_KEYS) - set(TEST_CREDENTIALS)}\n"
            f"多余: {set(TEST_CREDENTIALS) - set(_REQUIRED_KEYS)}"
        )


class TestReadme:
    """AC#4：验证 README.md 包含必要安装步骤"""

    def _read_readme(self) -> str:
        return (ROOT / "README.md").read_text()

    def test_readme_mentions_playwright_install(self):
        assert "playwright install chromium" in self._read_readme()

    def test_readme_mentions_pip_install(self):
        assert "pip install -r requirements.txt" in self._read_readme()

    def test_readme_mentions_validate_all(self):
        assert "validate.py" in self._read_readme()
