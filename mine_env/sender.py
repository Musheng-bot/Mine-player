"""Capture and send screen frames."""

from __future__ import annotations

import argparse
import socket
import time

import cv2
import numpy as np

from .capture import CaptureRegion, create_screen, find_window_region, parse_region
from .config import parse_network_args
from .protocol import send_frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把屏幕区域或窗口画面发送到接收端")
    parser.add_argument("--config", default="config/env.yaml", help="YAML 配置路径")
    return parser


def run(args: argparse.Namespace) -> None:
    if type(args.quality) is not int or not 1 <= args.quality <= 100:
        raise ValueError("quality 必须是 1-100 的整数")
    if (
        not isinstance(args.fps, (int, float)) or isinstance(args.fps, bool)
        or args.fps <= 0
        or not isinstance(args.refresh_window, (int, float))
        or isinstance(args.refresh_window, bool)
        or args.refresh_window <= 0
    ):
        raise ValueError("fps 和 refresh_window 必须是大于 0 的数字")
    if args.window is not None and not isinstance(args.window, str):
        raise ValueError("window 必须是字符串或 null")
    if args.region is not None and not isinstance(args.region, str):
        raise ValueError("region 必须是 left,top,width,height 格式的字符串或 null")
    if bool(args.window) == bool(args.region):
        raise ValueError("sender 必须且只能配置 window 或 region 之一")

    region: CaptureRegion | None = parse_region(args.region) if args.region else None
    next_window_refresh = 0.0
    interval = 1.0 / args.fps
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), args.quality]

    print(f"连接接收端 {args.host}:{args.port} ...")
    with socket.create_connection((args.host, args.port)) as connection, create_screen() as screen:
        print("已连接，开始发送。按 Ctrl+C 停止。")
        try:
            while True:
                started = time.monotonic()
                if args.window and started >= next_window_refresh:
                    region = find_window_region(args.window)
                    next_window_refresh = started + args.refresh_window

                assert region is not None
                raw = np.asarray(screen.grab({
                    "left": region.left,
                    "top": region.top,
                    "width": region.width,
                    "height": region.height,
                }))
                captured_at_ns = time.time_ns()
                bgr = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
                ok, encoded = cv2.imencode(".jpg", bgr, encode_params)
                if ok:
                    send_frame(connection, encoded.tobytes(), captured_at_ns)

                remaining = interval - (time.monotonic() - started)
                if remaining > 0:
                    time.sleep(remaining)
        except (KeyboardInterrupt, BrokenPipeError, ConnectionResetError):
            print("发送已停止。")


def main() -> None:
    args = parse_network_args(build_parser(), "sender", {
        "host": "127.0.0.1",
        "port": 5000,
        "window": None,
        "region": None,
        "fps": 15,
        "quality": 80,
        "refresh_window": 1.0,
    })
    try:
        run(args)
    except (argparse.ArgumentTypeError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
