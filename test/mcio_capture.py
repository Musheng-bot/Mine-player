"""抓取 MCio 画面并保存为 PNG —— 用来证明 Python 侧确实收到了游戏画面。

用法：
    conda activate mcio
    cd D:\\codes\\Mine-player
    python mcio_capture.py                 # 原地抓 5 张
    python mcio_capture.py --walk 40       # 每抓一张前先前进 40 步
    python mcio_capture.py --count 8 --interval 30

会输出 shot_000.png, shot_001.png ...，并打印每张的位置与数值统计。
"""

from __future__ import annotations

import argparse
import time

import numpy as np

import mcio_ctrl as mcio
from mcio_ctrl.envs import mcio_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="抓 MCio 画面存成 PNG")
    p.add_argument("--count", type=int, default=5, help="抓几张")
    p.add_argument("--interval", type=int, default=20, help="两张之间空转多少步")
    p.add_argument("--walk", type=int, default=0, help="每张前先按 W 前进多少步（0 = 不走）")
    p.add_argument("--width", type=int, default=854)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--prefix", default="shot", help="文件名前缀")
    return p.parse_args()


def main() -> None:
    from PIL import Image

    args = parse_args()
    opts = mcio.types.RunOptions.for_connect(width=args.width, height=args.height)
    env = mcio_env.MCioEnv(opts)
    keys = list(env.action_space.spaces.keys())

    def action(w: int = 0) -> dict:
        a = {k: np.int64(0) for k in keys}
        a["cursor_delta"] = np.array((0, 0), dtype=np.int32)
        if w:
            a["W"] = np.int64(1)
        return a

    print("连接中……")
    obs, _ = env.reset()
    print(f"已连接。画面 {obs['frame'].shape} {obs['frame'].dtype}")

    # 死亡就推进重生
    for _ in range(100):
        if float(obs["pos"][1]) > 0:
            break
        obs, _r, term, _t, _i = env.step(action())

    for i in range(args.count):
        if args.walk and i > 0:
            print(f"  前进 {args.walk} 步……")
            for _ in range(args.walk):
                obs, _r, term, _t, _i = env.step(action(w=1))
                if term:
                    for _ in range(100):
                        obs, _r, term, _t, _i = env.step(action())
                        if not term:
                            break

        obs, _r, term, _t, _i = env.step(action())
        frame = obs["frame"]
        pos = obs["pos"]

        name = f"{args.prefix}_{i:03d}.png"
        Image.fromarray(frame).save(name)

        print(
            f"  [{i + 1}/{args.count}] {name}  "
            f"shape={frame.shape} dtype={frame.dtype} "
            f"min={frame.min()} max={frame.max()} mean={frame.mean():.1f}  "
            f"位置=({pos[0]:7.2f},{pos[1]:6.2f},{pos[2]:7.2f})  "
            f"yaw={float(obs['yaw'][0]):7.1f} pitch={float(obs['pitch'][0]):6.1f}"
        )

        for _ in range(args.interval):
            obs, _r, term, _t, _i = env.step(action())
            if term:
                break

    env.close()
    print(f"\n完成，共 {args.count} 张。")


if __name__ == "__main__":
    main()
