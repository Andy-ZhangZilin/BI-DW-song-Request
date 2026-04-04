"""outdoor-data-validator — 统一 CLI 验证入口

职责：
- CLI 参数解析（--source / --all）
- 启动阶段凭证快速失败
- 调度各数据源执行完整验证流程（authenticate → fetch_sample → extract_fields → report）
- 汇总结果输出与退出码管理

不包含报告渲染逻辑（reporter.py 负责）、凭证加载逻辑（credentials.py 负责）。
"""
import argparse
import logging
import sys
from typing import Any, Dict

import reporter
from config.credentials import get_credentials
from sources import (
    awin,
    cartsee,
    dingtalk,
    partnerboost,
    social_media,
    tiktok,
    triplewhale,
    youtube,
)
from sources.triplewhale import TABLES as TRIPLEWHALE_TABLES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 数据源注册表（有序，按推荐运行顺序）
# social_media 是 stub，--all 时也纳入（调度器统一捕获 NotImplementedError）
# ---------------------------------------------------------------------------
SOURCES: Dict[str, Any] = {
    "triplewhale": triplewhale,
    "tiktok": tiktok,
    "dingtalk": dingtalk,
    "youtube": youtube,
    "awin": awin,
    "cartsee": cartsee,
    "partnerboost": partnerboost,
    "social_media": social_media,
}


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _run_source(source_name: str, module: Any) -> bool:
    """执行单个数据源的完整验证流程，返回是否成功。

    流程：authenticate → fetch_sample → extract_fields → write_raw_report → init_validation_report
    triplewhale 特殊处理：循环执行 4 张表。

    Args:
        source_name: 数据源名称，与 SOURCES 注册表 key 一致。
        module: 对应的 source 模块对象。

    Returns:
        True 表示全部步骤成功；False 表示认证失败或捕获到异常。
    """
    logger.info(f"[{source_name}] 开始验证 ...")
    try:
        ok = module.authenticate()
        if not ok:
            logger.error(f"[{source_name}] 认证 ... 失败")
            return False
        logger.info(f"[{source_name}] 认证 ... 成功")

        if source_name == "triplewhale":
            # triplewhale 多表路由：每张表独立执行一遍完整流程
            for table_name in TRIPLEWHALE_TABLES:
                logger.info(f"[{source_name}] 获取 {table_name} 样本 ...")
                sample = module.fetch_sample(table_name)
                fields = module.extract_fields(sample)
                reporter.write_raw_report(source_name, fields, table_name, len(sample))
                logger.info(f"[{source_name}] {table_name} ... 成功")
            reporter.init_validation_report(source_name)
        else:
            logger.info(f"[{source_name}] 获取样本 ...")
            sample = module.fetch_sample()
            fields = module.extract_fields(sample)
            reporter.write_raw_report(source_name, fields, None, len(sample))
            reporter.init_validation_report(source_name)

        logger.info(f"[{source_name}] 验证完成 ... 成功")
        return True

    except Exception as e:
        logger.error(f"[{source_name}] 执行失败：{type(e).__name__}: {e}")
        return False


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="outdoor-data-validator: 验证各数据源 API 接入与字段发现",
        epilog=(
            "示例：\n"
            "  python validate.py --source triplewhale\n"
            "  python validate.py --all\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        type=str,
        metavar="SOURCE",
        help=(
            "指定单个数据源名称运行验证。"
            f"可选值：{', '.join(SOURCES.keys())}"
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "运行全部数据源的验证。"
            f"执行顺序：{', '.join(SOURCES.keys())}"
        ),
    )
    args = parser.parse_args()

    if not args.source and not args.all:
        parser.print_help()
        sys.exit(1)

    # --- 启动阶段凭证快速失败 ---
    try:
        get_credentials()
    except ValueError as e:
        logger.error(f"凭证校验失败，请检查 .env 文件：{e}")
        sys.exit(1)

    # --- 确定要运行的数据源列表 ---
    if args.source:
        if args.source not in SOURCES:
            logger.error(
                f"未知数据源：{args.source}，可用数据源：{list(SOURCES.keys())}"
            )
            sys.exit(1)
        sources_to_run: Dict[str, Any] = {args.source: SOURCES[args.source]}
    else:  # --all
        sources_to_run = SOURCES

    # --- 调度循环 ---
    results: Dict[str, str] = {}
    for source_name, module in sources_to_run.items():
        success = _run_source(source_name, module)
        results[source_name] = "成功" if success else "失败"

    # --- 汇总输出 ---
    logger.info("=" * 50)
    logger.info("验证汇总：")
    for name, status in results.items():
        logger.info(f"  {name}: {status}")
    logger.info("=" * 50)

    failed = [name for name, status in results.items() if status != "成功"]
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
