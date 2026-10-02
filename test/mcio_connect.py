"""连接你自己启动的 Minecraft（已装 MCio mod），收发动作与观测。

前提：
    1. Fabric 1.21.3 客户端，mods/ 里有 MCio 和 Fabric API
    2. 启动时带了 MCio 同步模式参数（见 README）
    3. 已进入一个世界（不是主菜单）

用法：
    conda activate mcio
    python mcio_connect.py
"""

from __future__ import annotations

import numpy as np

import mcio_ctrl as mcio
from mcio_ctrl.envs import mcio_env


def main() -> None:
    # for_connect() = 只连接已在运行的实例，不启动新的
    # （它设 instance_name=None，所以不会去装/起游戏）
    opts = mcio.types.RunOptions.for_connect(width=854, height=480)

    env = mcio_env.MCioEnv(opts)
    print(f"观测空间: {env.observation_space}")
    print(f"动作空间键: {sorted(env.action_space.spaces.keys())}")

    obs, info = env.reset()
    frame = obs["frame"]
    print(f"\n第一帧: shape={frame.shape} dtype={frame.dtype} "
          f"min={frame.min()} max={frame.max()}")
    print(f"位置: {obs['pos']}  yaw={obs['yaw']}  pitch={obs['pitch']}")

    # 保存一张图，方便肉眼确认画面方向是否正确
    try:
        from PIL import Image

        Image.fromarray(frame).save("frame_check.png")
        print("已保存 frame_check.png —— 请打开确认画面是正的（天空在上）")
    except ImportError:
        print("（未装 Pillow，跳过存图）")

    # ---- 发动作 ----
    # 动作是一个 dict，键就是上面那些；cursor_delta 是鼠标相对位移（像素）
    def do(action: dict, steps: int = 1) -> dict:
        out = None
        for _ in range(steps):
            out, _reward, terminated, truncated, _info = env.step(action)
            if terminated or truncated:
                break
        return out  # type: ignore[return-value]

    noop = {k: np.int64(0) for k in env.action_space.spaces}
    noop["cursor_delta"] = np.array((0, 0), dtype=np.int32)

    def act(**overrides) -> dict:
        a = dict(noop)
        a.update(overrides)
        return a

    print("\n--- 测试：前进 10 步 ---")
    before = obs["pos"].copy()
    obs = do(act(W=np.int64(1)), 10)
    after = obs["pos"]
    print(f"位置 {np.round(before, 2)} -> {np.round(after, 2)}")

    print("--- 测试：右转视角 ---")
    obs = do(act(**{"cursor_delta": np.array((60, 0), dtype=np.int32)}), 5)
    print(f"yaw = {obs['yaw']}")

    print("--- 测试：跳跃 ---")
    obs = do(act(SPACE=np.int64(1)), 5)
    print(f"pos.y = {obs['pos'][1]:.2f}")

    print("--- 测试：攻击 ---")
    obs = do(act(**{"LEFT_BUTTON": np.int64(1)}), 3)
    print("攻击动作已发送")

    env.close()
    print("\n已断开连接（游戏仍在运行）。")


if __name__ == "__main__":
    main()
