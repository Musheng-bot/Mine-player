"""最小 Agent：连接 MCio，什么都不做，只把世界推进下去。

用途：
    - 游戏卡在死亡界面 / 重生流程走不完时，用这个把状态推过去
    - 排查"到底连不连得上"，不掺杂任何行为逻辑

它会：
    1. 连接
    2. 如果玩家是死的，反复 reset 直到活着（MCio 靠动作驱动重生）
    3. 持续发送无操作动作，让世界保持运行
    4. Ctrl+C 停止

用法：
    conda activate mcio
    cd D:\\codes\\Mine-player
    python mcio_keepalive.py
"""

from __future__ import annotations

import argparse
import time

import numpy as np

import mcio_ctrl as mcio
from mcio_ctrl.envs import mcio_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="空转 Agent：只把世界推进，不做任何操作")
    p.add_argument("--rate", type=float, default=20.0, help="每秒几步（默认 20 = 原版节奏）")
    p.add_argument("--log-every", type=int, default=60, help="每多少步打印一次")
    p.add_argument("--max-steps", type=int, default=0, help="最多几步（0 = 不限）")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    opts = mcio.types.RunOptions.for_connect()
    env = mcio_env.MCioEnv(opts)
    keys = list(env.action_space.spaces.keys())

    noop = {k: np.int64(0) for k in keys}
    noop["cursor_delta"] = np.array((0, 0), dtype=np.int32)

    print("连接中……")
    try:
        obs, info = env.reset()
    except Exception as exc:
        print(f"连接失败：{type(exc).__name__}: {exc}")
        env.close()
        return

    def health() -> float:
        # 血量是 env 的属性；MCioEnv 的 info 是空字典
        return float(getattr(env, "health", 0.0))

    # 死亡时靠连续动作把重生流程推完
    tries = 0
    while health() <= 0 and tries < 10:
        tries += 1
        print(f"  玩家已死亡，推进重生流程（第 {tries} 次）……")
        for _ in range(100):
            obs, _r, term, _t, info = env.step(noop)
            if not term and env.health > 0:
                break

    print(f"已连接。位置 {np.round(obs['pos'], 2)}  生命 {env.health}")
    print(f"空转中（每秒约 {args.rate:.0f} 步），Ctrl+C 停止……")

    step = 0
    started = time.monotonic()
    next_t = started
    try:
        while True:
            if args.rate > 0:
                now = time.monotonic()
                if now < next_t:
                    time.sleep(next_t - now)
                next_t = time.monotonic() + 1.0 / args.rate

            obs, _r, terminated, truncated, info = env.step(noop)
            step += 1

            if terminated:
                print(f"  步 {step}: 玩家死亡，推进重生……")
                for _ in range(100):
                    obs, _r, terminated, _t, info = env.step(noop)
                    if not terminated:
                        break

            if step % args.log_every == 0:
                p = obs["pos"]
                print(
                    f"  步 {step:6d} | 位置 ({p[0]:8.2f},{p[1]:7.2f},{p[2]:8.2f}) | "
                    f"生命 {env.health:4.1f} | {step / max(time.monotonic() - started, 1e-6):5.1f} 步/秒"
                )

            if args.max_steps and step >= args.max_steps:
                break

    except KeyboardInterrupt:
        print("\n收到 Ctrl+C。")
    except Exception as exc:
        print(f"\n中断：{type(exc).__name__}: {exc}")
    finally:
        env.close()
        print(f"已断开。共 {step} 步，用时 {time.monotonic() - started:.1f} 秒")


if __name__ == "__main__":
    main()
