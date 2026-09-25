"""Run Minecraft locally and read observations through CraftGround."""

from __future__ import annotations

import argparse
import time
from typing import Any

import cv2
import numpy as np
from craftground import ActionSpaceVersion, InitialEnvironmentConfig, make
from craftground.environment.action_space import no_op_v2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="本机启动并读取 CraftGround 环境")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--render-distance", type=int, default=6)
    parser.add_argument("--status-interval", type=float, default=1.0)
    parser.add_argument("--no-viewer", action="store_true", help="不显示本地画面窗口")
    return parser.parse_args()


def frame_to_bgr(frame: Any) -> np.ndarray:
    """Convert a CraftGround RGB observation to an OpenCV image."""
    if hasattr(frame, "detach"):
        frame = frame.detach().cpu().numpy()

    image = np.asarray(frame)
    if image.ndim != 3:
        raise ValueError(f"无法识别画面形状：{image.shape}")
    if image.shape[0] in (3, 4) and image.shape[-1] not in (3, 4):
        image = np.moveaxis(image, 0, -1)
    if image.shape[-1] == 4:
        return cv2.cvtColor(image, cv2.COLOR_RGBA2BGRA)
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


def print_status(observation: dict[str, Any]) -> None:
    state = observation["full"]
    print(
        "位置 "
        f"({state.x:.1f}, {state.y:.1f}, {state.z:.1f}) | "
        f"视角 yaw={state.yaw:.1f}, pitch={state.pitch:.1f} | "
        f"生命={state.health:.1f} | 饥饿={state.food_level} | "
        f"背包物品栈={len(state.inventory)}"
    )


def action_from_key(key: int) -> dict[str, bool | float]:
    action = no_op_v2()
    key_actions = {
        ord("w"): "forward",
        ord("s"): "back",
        ord("a"): "left",
        ord("d"): "right",
        ord(" "): "jump",
        ord("f"): "attack",
        ord("e"): "use",
    }
    if key in key_actions:
        action[key_actions[key]] = True
    elif key == ord("j"):
        action["camera_yaw"] = -10.0
    elif key == ord("l"):
        action["camera_yaw"] = 10.0
    elif key == ord("i"):
        action["camera_pitch"] = -10.0
    elif key == ord("k"):
        action["camera_pitch"] = 10.0
    return action


def run(args: argparse.Namespace) -> None:
    if args.width <= 0 or args.height <= 0 or args.render_distance <= 0:
        raise SystemExit("width、height 和 render-distance 必须大于 0")
    if args.status_interval <= 0:
        raise SystemExit("status-interval 必须大于 0")

    config = InitialEnvironmentConfig(
        image_width=args.width,
        image_height=args.height,
        hud_hidden=False,
        render_distance=args.render_distance,
    )
    env = make(
        port=args.port,
        initial_env_config=config,
        action_space_version=ActionSpaceVersion.V2_MINERL_HUMAN,
    )

    print("正在启动 CraftGround 和 Minecraft，首次启动可能需要几分钟……")
    try:
        observation, _ = env.reset()
        print("环境已连接。画面窗口按 Esc 退出；WASD/空格移动，F 攻击，E 使用，IJKL 转动视角。")
        next_status_at = 0.0

        while True:
            now = time.monotonic()
            if now >= next_status_at:
                print_status(observation)
                next_status_at = now + args.status_interval

            key = -1
            if not args.no_viewer:
                cv2.imshow("CraftGround", frame_to_bgr(observation["pov"]))
                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    break

            observation, _, terminated, truncated, _ = env.step(action_from_key(key))
            if terminated or truncated:
                observation, _ = env.reset()
    except KeyboardInterrupt:
        print("\n正在退出……")
    finally:
        env.close()
        cv2.destroyAllWindows()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
