"""outdoor-data-validator — 统一 CLI 验证入口"""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="outdoor-data-validator: 验证各数据源 API 接入与字段发现"
    )
    parser.add_argument("--source", type=str, help="指定单个数据源名称（如 triplewhale）")
    parser.add_argument("--all", action="store_true", help="运行全部数据源的验证")
    args = parser.parse_args()

    if not args.source and not args.all:
        parser.print_help()
        sys.exit(1)

    # TODO: Story 5.1 实现调度逻辑


if __name__ == "__main__":
    main()
