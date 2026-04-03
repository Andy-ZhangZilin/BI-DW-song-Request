# Story 4.4: 社媒后台 Stub 模块

Status: done

## Story

作为操作者，
我希望社媒后台数据源以占位模块形式存在，在凭证就绪前提供明确的未实现提示，
以便工具的模块结构完整，且在未来凭证就绪时只需填充实现而无需修改框架。

## Acceptance Criteria

1. `sources/social_media.py` 存在，调用 `social_media.authenticate()` 抛出 `NotImplementedError("social_media: 凭证未就绪，暂未实现")`
2. `sources/social_media.py` 存在，调用 `social_media.fetch_sample()` 抛出 `NotImplementedError`
3. `sources/social_media.py` 存在，调用 `social_media.extract_fields([])` 抛出 `NotImplementedError`
4. 单元测试 `tests/test_social_media.py` 验证三个接口均正确抛出 `NotImplementedError`，测试全部通过

## Tasks / Subtasks

- [x] 创建 `sources/social_media.py` stub 模块 (AC: #1 #2 #3)
  - [x] 实现 `authenticate()` → `raise NotImplementedError("social_media: 凭证未就绪，暂未实现")`
  - [x] 实现 `fetch_sample(table_name: str = None)` → `raise NotImplementedError`
  - [x] 实现 `extract_fields(sample: list[dict])` → `raise NotImplementedError`
  - [x] 添加模块文档字符串，说明 stub 用途及填充方式
- [x] 创建 `tests/test_social_media.py` 单元测试 (AC: #4)
  - [x] 测试 `authenticate()` 抛出 `NotImplementedError`
  - [x] 测试 `fetch_sample()` 抛出 `NotImplementedError`
  - [x] 测试 `extract_fields([])` 抛出 `NotImplementedError`
  - [x] 验证 `pytest tests/ -m "not integration"` 全部通过

### Review Findings

- [x] [Review][Patch] `fetch_sample` docstring 繁体错字"始終"应改为"始终" [sources/social_media.py:36] — 文件已为简体，无需修改
- [x] [Review][Patch] `table_name: str = None` 应改为 `Optional[str] = None` [sources/social_media.py:28] — 已修复，添加 `from typing import Optional`
- [x] [Review][Defer] 测试仅验证 stub 行为，未来实现替换时测试需同步更新 [tests/test_social_media.py] — deferred, pre-existing
- [x] [Review][Defer] `extract_fields`/`fetch_sample` 未覆盖非空/非标准输入参数的测试 [tests/test_social_media.py] — deferred, pre-existing

## Dev Notes

### 核心实现要求

**`sources/social_media.py` 接口契约（必须与 ARCH2 规定的 source 统一接口一致）：**

```python
def authenticate() -> bool:
    raise NotImplementedError("social_media: 凭证未就绪，暂未实现")

def fetch_sample(table_name: str = None) -> list[dict]:
    raise NotImplementedError("social_media: 凭证未就绪，暂未实现")

def extract_fields(sample: list[dict]) -> list[dict]:
    raise NotImplementedError("social_media: 凭证未就绪，暂未实现")
```

**重要：此模块是纯 stub，不调用 `get_credentials()`，不导入任何外部库。**

### 接口契约参照（ARCH2）

所有 source 模块统一接口：
- `authenticate() -> bool`
- `fetch_sample(table_name: str = None) -> list[dict]`
- `extract_fields(sample: list[dict]) -> list[dict]`

FieldInfo 标准结构（供将来实现时参考）：
```python
{"field_name": str, "data_type": str, "sample_value": Any, "nullable": bool}
```

### 测试说明

- 此 stub **不调用** `get_credentials()`，测试无需使用 `mock_credentials` fixture
- 无浏览器自动化，无需 `@pytest.mark.integration`
- 测试只需验证 `NotImplementedError` 被抛出，无需检查 message 内容（除非 AC 1 明确要求 authenticate 的 message 文本）

**AC 1 要求 authenticate 的 message 为：`"social_media: 凭证未就绪，暂未实现"`，测试中应检查此文本。**

### 既有代码模式参照（来自 Epic 1 已完成 Story）

**`conftest.py` 中的 `mock_credentials` fixture：**
```python
@pytest.fixture
def mock_credentials():
    with patch("config.credentials.load_dotenv", MagicMock()), \
         patch("config.credentials.get_credentials", return_value=TEST_CREDENTIALS):
        yield TEST_CREDENTIALS
```
**说明：此 story 的测试不需要使用该 fixture，因为 social_media stub 不调用 get_credentials。**

**现有测试文件参照结构（`tests/test_reporter.py`）：**
- 顶部 docstring 说明覆盖的 AC 编号
- 按 AC 分组写测试，命名格式 `test_xxx_ac_N_描述`

**现有 `sources/__init__.py`：** 空文件（仅用于标记 package），新 `social_media.py` 直接添加到 `sources/` 目录即可，不需要修改 `__init__.py`。

### Project Structure Notes

- 新增文件：`sources/social_media.py`（stub 模块）
- 新增文件：`tests/test_social_media.py`（单元测试）
- **不修改**：`sources/__init__.py`、`config/credentials.py`、`reporter.py`、`validate.py`、`tests/conftest.py`
- 文件路径规范与 sources/ 目录现有结构完全一致

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4: 社媒后台 Stub 模块]
- [Source: _bmad-output/planning-artifacts/epics.md#ARCH11] — social_media.py 作为 stub 模块，三个接口均 raise NotImplementedError
- [Source: _bmad-output/planning-artifacts/epics.md#ARCH2] — 统一 source 接口契约
- [Source: _bmad-output/planning-artifacts/epics.md#ARCH12] — tests/conftest.py fixture 说明

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

无调试问题，实现一次通过。

### Completion Notes List

- 创建 `sources/social_media.py`：三个接口均 raise NotImplementedError，含完整模块文档字符串及将来实现指引
- 创建 `tests/test_social_media.py`：4 个测试用例，覆盖全部 AC（含 authenticate message 文本验证、fetch_sample 含/不含 table_name 参数两种调用方式）
- 4 个新测试全部通过；5 个预存失败（来自其他 Story）未新增回归
- 实现不依赖任何外部库，不调用 get_credentials()，符合 ARCH11 pure stub 约束

### File List

- sources/social_media.py（新增）
- tests/test_social_media.py（新增）
