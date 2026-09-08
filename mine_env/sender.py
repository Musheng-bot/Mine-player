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
    parser.add_argument("--config", default="config/env.yaml", help="网络 YAML 配置路径（默认：config/env.yaml）；命令行参数优先")
    parser.add_argument("--host", default="127.0.0.1", help="接收端 IP")
    parser.add_argument("--port", type=int, default=5000)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--region", type=parse_region, help="区域：left,top,width,height")
    source.add_argument("--window", help="窗口标题关键字")
    parser.add_argument("--fps", type=float, default=15, help="发送帧率")
    parser.add_argument("--quality", type=int, default=80, help="JPEG 质量 1-100")
    parser.add_argument("--refresh-window", type=float, default=1.0, help="窗口重新定位间隔（秒）")
    return parser


def run(args: argparse.Namespace) -> None:
    if not 1 <= args.quality <= 100 or args.fps <= 0:
        raise ValueError("--quality 必须在 1-100 之间，--fps 必须大于 0")

    region: CaptureRegion | None = args.region
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
    args = parse_network_args(build_parser(), "sender")
    try:
        run(args)
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
