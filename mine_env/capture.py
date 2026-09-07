"""Screen and window capture helpers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int


def parse_region(value: str) -> CaptureRegion:
    try:
        left, top, width, height = (int(item.strip()) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("区域格式必须是 left,top,width,height") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("区域宽度和高度必须大于 0")
    return CaptureRegion(left, top, width, height)


def find_window_region(title: str) -> CaptureRegion:
    try:
        import pygetwindow as gw
    except (ImportError, NotImplementedError) as exc:
        raise RuntimeError("当前平台不支持 PyGetWindow 窗口模式，请改用 --region") from exc

    windows = gw.getWindowsWithTitle(title)
    if not windows:
        raise RuntimeError(f"找不到标题包含 {title!r} 的窗口")
    window = next((item for item in windows if item.width > 0 and item.height > 0), windows[0])
    return CaptureRegion(int(window.left), int(window.top), int(window.width), int(window.height))


def create_screen():
    try:
        import mss
    except ImportError as exc:
        raise RuntimeError("发送端需要 mss，请先安装项目依赖") from exc
    return mss.MSS()
