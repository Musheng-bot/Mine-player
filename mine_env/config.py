"""Load component settings from YAML."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def parse_network_args(
    parser: argparse.ArgumentParser,
    role: str,
    defaults: dict[str, object],
    argv: list[str] | None = None,
) -> argparse.Namespace:
    args = parser.parse_args(argv)
    try:
        with Path(args.config).open(encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as exc:
        parser.error(f"无法读取配置 {args.config}: {exc}")

    if not isinstance(config, dict) or not isinstance(config.get(role), dict):
        parser.error(f"YAML 配置必须包含 {role} 映射")

    settings = config[role]
    unknown = settings.keys() - defaults.keys()
    if unknown:
        parser.error(f"{role} 包含未知配置：{', '.join(sorted(unknown))}")

    values = defaults | settings
    if not isinstance(values["host"], str) or not values["host"].strip():
        parser.error(f"{role}.host 必须是非空字符串")
    if type(values["port"]) is not int or not 1 <= values["port"] <= 65535:
        parser.error(f"{role}.port 必须是 1-65535 的整数")
    return argparse.Namespace(config=args.config, **values)
