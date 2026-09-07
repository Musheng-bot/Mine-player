"""Receive, display, and measure screen frames."""

from __future__ import annotations

import argparse
import socket
import time

import cv2
import numpy as np

from .protocol import receive_frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="接收并显示发送端画面")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--save", help="保存接收到的最新画面到 JPEG 文件")
    return parser


def run(args: argparse.Namespace) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.host, args.port))
        server.listen(1)
        print(f"监听 {args.host}:{args.port}，等待发送端连接...")
        connection, address = server.accept()
        with connection:
            print(f"已连接：{address}。按 q 或 Esc 退出。")
            frame_count = 0
            delay_total_ms = 0.0
            while True:
                received = receive_frame(connection)
                if received is None:
                    break
                payload, captured_at_ns = received
                image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
                if image is None:
                    continue

                delay_ms = max(0.0, (time.time_ns() - captured_at_ns) / 1_000_000)
                frame_count += 1
                delay_total_ms += delay_ms
                average_delay_ms = delay_total_ms / frame_count
                cv2.putText(
                    image,
                    f"delay: {delay_ms:.1f} ms | avg: {average_delay_ms:.1f} ms",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA,
                )
                if frame_count % 30 == 0:
                    print(f"帧数: {frame_count}, 当前延迟: {delay_ms:.1f} ms, 平均: {average_delay_ms:.1f} ms")
                if args.save:
                    cv2.imwrite(args.save, image)
                cv2.imshow("Received", image)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break

    cv2.destroyAllWindows()
    print("接收已停止。")


def main() -> None:
    try:
        run(build_parser().parse_args())
    except KeyboardInterrupt:
        print("\n接收已停止。")


if __name__ == "__main__":
    main()
