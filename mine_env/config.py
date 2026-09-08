"""Load network settings from YAML before parsing command-line overrides."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def parse_network_args(
    parser: argparse.ArgumentParser, role: str, argv: list[str] | None = None,
) -> argparse.Namespace:
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument("--config", default=parser.get_default("config"))
    config_args, _ = config_parser.parse_known_args(argv)
    if config_args.config:
        try:
            with Path(config_args.config).open(encoding="utf-8") as file:
                settings = yaml.safe_load(file)
        except (OSError, yaml.YAMLError) as exc:
            parser.error(f"无法读取配置 {config_args.config}: {exc}")

        if not isinstance(settings, dict):
            parser.error("YAML 配置必须是包含 host、port 的映射")
        # 共享配置按角色分组；仍支持 --config 指定原来的独立配置。
        if "sender" in settings or "receiver" in settings:
            settings = settings.get(role)
            if not isinstance(settings, dict):
                parser.error(f"YAML 配置必须包含 {role} 映射")
        if settings.keys() - {"host", "port"}:
            parser.error("网络配置仅支持 host 和 port")
        if "host" in settings and (
            not isinstance(settings["host"], str) or not settings["host"].strip()
        ):
            parser.error("配置 host 必须是非空字符串")
        if "port" in settings and (
            type(settings["port"]) is not int or not 1 <= settings["port"] <= 65535
        ):
            parser.error("配置 port 必须是 1-65535 的整数")
        parser.set_defaults(**settings)

    return parser.parse_args(argv)
