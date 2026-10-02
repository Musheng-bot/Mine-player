"""观察 Agent 在做什么：开一个实时窗口显示第一人称画面 + 打印状态。

用法：
    conda activate mcio
    cd D:\\codes\\Mine-player
    python mcio_observe.py                    # 默认跟随游戏的模式
    python mcio_observe.py --mode sync        # 强制 SYNC（不等待 tick，全速）
    python mcio_observe.py --mode async       # 强制 ASYNC（真实 20 TPS）

窗口里会显示 Minecraft 的第一人称画面（Python 侧收到的原始帧）。
按 Esc 或 Ctrl+C 退出。

注意：ASYNC 模式下游戏不等你，观测可能被丢弃（只保留最新一帧）。
SYNC 模式下游戏暂停等你，每一步都是确定的一个 tick。
"""

from __future__ import annotations

import argparse
import time

import numpy as np

import mcio_ctrl as mcio
from mcio_ctrl import types
from mcio_ctrl.envs import mcio_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="实时观察 Agent 的画面与状态")
    p.add_argument(
        "--mode",
        choices=["sync", "async", "auto"],
        default="auto",
        help="sync=全速一步一 tick；async=真实 20 TPS；auto=跟随游戏设置",
    )
    p.add_argument("--width", type=int, default=854)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--no-window", action="store_true", help="不开窗口，只打印状态")
    p.add_argument("--log-every", type=int, default=20, help="每多少步打印一次（0=不打印）")
    p.add_argument("--max-steps", type=int, default=0, help="最多多少步（0=不限）")
    p.add_argument("--save-every", type=int, default=0, help="每多少步存一张图（0=不存）")
    return p.parse_args()


def build_options(args: argparse.Namespace) -> types.RunOptions:
    """自己构造 RunOptions —— for_connect() 会把模式写死成 SYNC。"""
    kwargs: dict = {"width": args.width, "height": args.height}
    if args.mode == "sync":
        kwargs["mcio_mode"] = types.MCioMode.SYNC
    elif args.mode == "async":
        kwargs["mcio_mode"] = types.MCioMode.ASYNC
    # auto: 不传 mcio_mode，让它读 MCIO_MODE 环境变量，否则用默认值
    return types.RunOptions(**kwargs)


def main() -> None:
    args = parse_args()
    opts = build_options(args)

    render_mode = None if args.no_window else "human"
    env = mcio_env.MCioEnv(opts, render_mode=render_mode)
    keys = list(env.action_space.spaces.keys())

    print(f"模式选项 mcio_mode = {opts.mcio_mode}")
    print(f"窗口 = {'关闭' if args.no_window else '开启（GLFW）'}")
    print("连接中……（SYNC 模式下游戏是暂停的，这是正常的）")

    try:
        obs, _info = env.reset()
    except Exception as exc:
        print(f"\n连接失败：{type(exc).__name__}: {exc}")
        print("检查：游戏是否在运行并已进入世界；模式是否和游戏一致；cbor2 是否 <6")
        env.close()
        return

    print(f"已连接。画面 {obs['frame'].shape} {obs['frame'].dtype}  位置 {np.round(obs['pos'], 2)}")
    print("开始观察（关窗口或 Ctrl+C 退出）……\n")

    noop = {k: np.int64(0) for k in keys}
    noop["cursor_delta"] = np.array((0, 0), dtype=np.int32)

    step = 0
    started = time.monotonic()
    last_log = started

    try:
        while True:
            obs, _r, terminated, truncated, _info = env.step(noop)
            step += 1

            # 渲染到窗口
            if not args.no_window:
                env.render()

            now = time.monotonic()
            if args.log_every and step % args.log_every == 0:
                f = obs["frame"]
                p = obs["pos"]
                sps = step / max(now - started, 1e-6)
                print(
                    f"  步 {step:6d} | 位置 ({p[0]:8.2f},{p[1]:7.2f},{p[2]:8.2f}) | "
                    f"生命 {env.health:4.1f} | yaw {float(obs['yaw'][0]):6.1f} "
                    f"pitch {float(obs['pitch'][0]):5.1f} | "
                    f"帧 mean {f.mean():5.1f} | {sps:6.1f} 步/秒"
                )
                last_log = now

            if args.save_every and step % args.save_every == 0:
                try:
                    from PIL import Image

                    name = f"observe_{step:06d}.png"
                    Image.fromarray(obs["frame"]).save(name)
                    print(f"          已存 {name}")
                except ImportError:
                    pass

            if terminated:
                print(f"  步 {step}: 玩家死亡，推进重生……")
                for _ in range(100):
                    obs, _r, terminated, _t, _i = env.step(noop)
                    if not terminated:
                        break

            if args.max_steps and step >= args.max_steps:
                print(f"\n达到 --max-steps={args.max_steps}。")
                break

    except KeyboardInterrupt:
        print("\n收到 Ctrl+C。")
    except Exception as exc:
        print(f"\n中断：{type(exc).__name__}: {exc}")
    finally:
        env.close()

    elapsed = time.monotonic() - started
    print(f"结束：{step} 步，用时 {elapsed:.1f} 秒，平均 {step / max(elapsed, 1e-6):.1f} 步/秒")


if __name__ == "__main__":
    main()
