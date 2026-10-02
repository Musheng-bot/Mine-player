"""MCio 行走 demo：一直前进，卡住就跳。

行为：
    - 持续按住 W 前进
    - 窗口内水平位移过小视为卡住 → 按 SPACE 尝试跳过障碍
    - 连续卡住多次 → 额外左右转视角，避免一直顶着同一面墙
    - 死亡 → 自动重开一局，继续走
    - 掉线 → 干净退出（不空转）

用法：
    conda activate mcio
    cd D:\\codes\\Mine-player
    python mcio_walk.py

前提：游戏已在 SYNC 模式启动并进入世界。
"""

from __future__ import annotations

import argparse
import time
from collections import deque

import numpy as np

import mcio_ctrl as mcio
from mcio_ctrl.envs import mcio_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MCio 行走 demo：一直前进，卡住就跳")
    p.add_argument("--width", type=int, default=854)
    p.add_argument("--height", type=int, default=480)

    p.add_argument("--window", type=int, default=20, help="判定移动的窗口步数（每步 1 tick）")
    p.add_argument("--min-move", type=float, default=0.25, help="窗口内水平位移小于此值视为卡住（格）")
    p.add_argument("--jump-hold", type=int, default=4, help="跳跃按住几个 tick")
    p.add_argument("--turn-after", type=int, default=25, help="连续卡住多少次后转向")
    p.add_argument("--turn-delta", type=float, default=45.0, help="转向的鼠标像素位移")

    p.add_argument(
        "--rate",
        type=float,
        default=0.0,
        help="限速：每秒最多走多少步（0 = 不限，全速）。"
        "真实 Minecraft 是 20；限速会拉长总时长，但保留干净的一步一 tick 语义。",
    )
    p.add_argument("--max-steps", type=int, default=0, help="最多走几步（0 = 一直走）")
    p.add_argument("--log-every", type=int, default=20, help="每多少步打印一次状态")
    p.add_argument("--save-frame-every", type=int, default=0, help="每多少步存一张截图（0 = 不存）")
    return p.parse_args()


def make_action(space_keys, **overrides) -> dict:
    """构造一个动作：先全部置 0，再覆盖指定键。"""
    action = {k: np.int64(0) for k in space_keys}
    action["cursor_delta"] = np.array((0, 0), dtype=np.int32)
    action.update(overrides)
    return action


def main() -> None:
    args = parse_args()

    opts = mcio.types.RunOptions.for_connect(width=args.width, height=args.height)
    env = mcio_env.MCioEnv(opts)
    keys = list(env.action_space.spaces.keys())

    obs = None
    x0 = z0 = 0.0
    step = 0
    deaths = 0
    started = time.time()

    print("正在连接 Minecraft（游戏会在 SYNC 模式下暂停等你，这是正常的）……")
    try:
        obs, _info = env.reset()
    except Exception as exc:
        print(f"\n连接失败：{type(exc).__name__}: {exc}")
        print()
        print("常见原因：")
        print("  1. 游戏没运行，或还没进入世界（MCio 只接管游戏内的控制）")
        print("  2. 不是 SYNC 模式（PCL2 的 JVM 参数里要有 -DMCIO_MODE=sync）")
        print("  3. cbor2 装成了 6.x（需 pip install \"cbor2<6\"）")
        env.close()
        return

    print(f"已连接。画面 {obs['frame'].shape}，起始位置 {np.round(obs['pos'], 2)}")
    if args.rate > 0:
        print(f"已限速：每秒最多 {args.rate:.1f} 步（原版 Minecraft 是 20）")
    else:
        print("全速运行（SYNC 模式不等待 tick 计时器）")

    recent: deque[tuple[float, float]] = deque(maxlen=args.window)
    x0, z0 = float(obs["pos"][0]), float(obs["pos"][2])
    recent.append((x0, z0))

    stuck_count = 0
    jump_left = 0
    next_step_time = time.monotonic()

    print("开始前进（Ctrl+C 停止）……")

    try:
        while True:
            # ---- 限速 ----
            if args.rate > 0:
                now = time.monotonic()
                if now < next_step_time:
                    time.sleep(next_step_time - now)
                next_step_time = time.monotonic() + 1.0 / args.rate

            pos = obs["pos"]
            x, z = float(pos[0]), float(pos[2])
            recent.append((x, z))

            if len(recent) >= 2:
                dx = recent[-1][0] - recent[0][0]
                dz = recent[-1][1] - recent[0][1]
                moved = (dx * dx + dz * dz) ** 0.5
            else:
                moved = float("inf")

            if len(recent) >= args.window:
                if moved < args.min_move:
                    stuck_count += 1
                    jump_left = args.jump_hold
                else:
                    stuck_count = 0

            action = make_action(keys, W=np.int64(1))
            if jump_left > 0:
                action["SPACE"] = np.int64(1)
                jump_left -= 1
            if stuck_count >= args.turn_after:
                action["cursor_delta"] = np.array((args.turn_delta, 0), dtype=np.int32)
                stuck_count = 0

            obs, _reward, terminated, truncated, _info = env.step(action)
            step += 1

            if step % args.log_every == 0:
                p = obs["pos"]
                sps = step / max(time.monotonic() - started, 1e-6)
                # 注意：血量不在 info 里（MCioEnv 的 _get_info 返回空字典），
                # 它是 env 的属性，由 base_env 每步从观测包更新。
                print(
                    f"  步 {step:6d} | 位置 ({p[0]:8.2f},{p[1]:7.2f},{p[2]:8.2f}) | "
                    f"位移 {((p[0]-x0)**2 + (p[2]-z0)**2) ** 0.5:7.2f} 格 | "
                    f"窗口 {moved:5.2f} | 卡住 {stuck_count:2d} | "
                    f"生命 {env.health:4.1f} | {sps:6.1f} 步/秒"
                )

            if args.save_frame_every and step % args.save_frame_every == 0:
                try:
                    from PIL import Image

                    name = f"walk_{step:06d}.png"
                    Image.fromarray(obs["frame"]).save(name)
                    print(f"          已存 {name}")
                except ImportError:
                    pass

            # ---- 死亡：自动重开 ----
            if terminated:
                deaths += 1
                print(f"\n  [死亡 #{deaths}] 第 {step} 步，位置 {np.round(obs['pos'], 1)}。自动重开……")
                try:
                    obs, _info = env.reset()
                except Exception as exc:
                    print(f"  重开失败（可能已掉线）：{type(exc).__name__}: {exc}")
                    break
                x0, z0 = float(obs["pos"][0]), float(obs["pos"][2])
                recent.clear()
                recent.append((x0, z0))
                stuck_count = 0
                jump_left = 0
                print(f"  已重生，新起点 {np.round(obs['pos'], 2)}\n")
                continue

            if truncated:
                print(f"  第 {step} 步被截断，重开……")
                obs, _info = env.reset()
                x0, z0 = float(obs["pos"][0]), float(obs["pos"][2])
                recent.clear()
                recent.append((x0, z0))
                continue

            if args.max_steps and step >= args.max_steps:
                print(f"\n达到 --max-steps={args.max_steps}，停止。")
                break

    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，停止。")
    except Exception as exc:
        print(f"\n运行中断：{type(exc).__name__}: {exc}")
        print("（如果游戏被关闭或死亡后未恢复，会走到这里）")

    finally:
        try:
            env.step(make_action(keys))
        except Exception:
            pass
        env.close()

    p = obs["pos"] if obs is not None else None
    elapsed = time.monotonic() - started
    if p is not None:
        total = ((p[0] - x0) ** 2 + (p[2] - z0) ** 2) ** 0.5
        print(
            f"\n结束：{step} 步，本局从 ({x0:.1f},{z0:.1f}) 到 ({p[0]:.1f},{p[2]:.1f})，"
            f"水平位移 {total:.2f} 格"
        )
    print(f"用时 {elapsed:.1f} 秒，平均 {step / max(elapsed, 1e-6):.1f} 步/秒，死亡 {deaths} 次")


if __name__ == "__main__":
    main()
