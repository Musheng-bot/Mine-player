# MCio 控制器 API

MCio 把 Minecraft 封装成两个标准的 **Gymnasium 环境**，用于收发画面与键鼠动作。

- Mod：https://modrinth.com/mod/mcio
- 控制库：`mcio_ctrl`（[PyPI](https://pypi.org/project/mcio-ctrl/)）
- 官方 Wiki：https://github.com/twoturtles/mcio_ctrl/wiki

## 1. 安装

```powershell
conda env create -f environment.yml
conda activate mcio
```

## 2. 启动与关闭

### 2.1 完整生命周期

```python
import numpy as np
from mcio_ctrl import types
from mcio_ctrl.envs import mcio_env

# ── 1. 配置 ──────────────────────────────────────────────
opts = types.RunOptions(
    width=854,               # 画面宽（默认 640）
    height=480,              # 画面高（默认 360）
    mcio_mode=types.MCioMode.ASYNC,   # SYNC | ASYNC
)

# ── 2. 构造环境（此时还不连接）──────────────────────────
env = mcio_env.MCioEnv(opts)          # render_mode="human" 可加观测窗口

# ── 3. 连接（这一步真正建立连接并拿第一帧）──────────────
obs, info = env.reset()

# ── 4. 主循环 ────────────────────────────────────────────
for _ in range(1000):
    action = env.get_noop_action()    # 空动作，或自己构造
    obs, reward, terminated, truncated, info = env.step(action)

    if terminated or truncated:
        obs, info = env.reset()       # 必须 reset 才能继续 step

# ── 5. 关闭（断开连接；游戏本身不受影响）────────────────
env.close()
```

`close()` 可重复调用，也可以直接用 `with`：

```python
with mcio_env.MCioEnv(opts) as env:
    obs, info = env.reset()
    ...
# 退出 with 自动 close
```

### 2.2 两种连接方式

| 方式 | 行为 | 用法 |
|---|---|---|
| **连接已运行的实例** | 不启动游戏，只连上去 | 不给 `instance_name`（默认） |
| **启动并连接** | 由 `mcio_ctrl` 拉起游戏 | 给 `instance_name` + `world_name` |

手动启动客户端时，游戏自己开着，控制端只连接：

```python
opts = types.RunOptions(width=854, height=480, mcio_mode=types.MCioMode.ASYNC)
env = mcio_env.MCioEnv(opts)
obs, info = env.reset()      # 连接到已在运行的游戏
```

**注意**：`types.RunOptions.for_connect()` 这个便捷方法会把模式固定成 SYNC：

```python
# mcio_ctrl/types.py
@classmethod
def for_connect(cls, width=..., height=...):
    return cls(width=width, height=height, mcio_mode=MCioMode.SYNC)
```

要用 ASYNC 就自己构造 `RunOptions`（如上）。模式解析顺序是：
显式参数 → 环境变量 `MCIO_MODE` → 默认值 `ASYNC`。

### 2.3 SYNC vs ASYNC

| | SYNC | ASYNC |
|---|---|---|
| 游戏是否等 Agent | **等**（暂停） | 不等，按 20 TPS 跑 |
| 速度 | 全速，只受硬件限制 | 真实 20 TPS |
| 观测对齐 | 一步一帧，严格对应 | 异步推送，慢则丢帧（只留最新） |
| 人类可否同玩 | 否 | 是（配 `MCIO_OPEN_TO_LAN=true`） |
| 适合 | RL 训练 | 交互 / 演示 |

Java 侧模式在启动器的 **JVM 参数**栏设置（不是「游戏参数」栏）：

```
-DMCIO_MODE=sync
```

**两边必须一致**，否则 `reset()` 会一直卡住。

SYNC 模式下游戏窗口会显示「未响应」——这是设计行为，点「等待」，不要关。

## 3. 两个环境

两者都是 `gymnasium.Env` 的子类，共享基类 `MCioBaseEnv`。

| | `MCioEnv` | `MinerlEnv` |
|---|---|---|
| 导入 | `from mcio_ctrl.envs import mcio_env` | `from mcio_ctrl.envs import minerl_env` |
| 类名 | `mcio_env.MCioEnv` | `minerl_env.MinerlEnv` |
| 观测 | 画面 **+ 位置/视角** | **只有画面** |
| 动作 | 键鼠级（鼠标像素位移） | MineRL 1.0 抽象动作（视角角度） |
| 用途 | 贴近真人操作、模仿学习 | 直接跑 MineRL 生态的现成 Agent |

### 3.1 `MCioEnv`

**观测空间**

| 字段 | 形状 / 类型 | 说明 |
|---|---|---|
| `frame` | `Box(0, 255, (480, 854, 3), uint8)` | 第一人称画面 |
| `pos` | `Box(-inf, inf, (3,), float32)` | 世界坐标 x, y, z |
| `yaw` | `Box(-180.0, 180.0, (1,), float32)` | 水平朝向 |
| `pitch` | `Box(-90.0, 90.0, (1,), float32)` | 俯仰 |

画面尺寸由 `RunOptions(width=, height=)` 决定，上表是 854x480 时的形状。

**动作空间**（23 个键）

| 类别 | 键 | 取值 |
|---|---|---|
| 移动 | `W` `A` `S` `D` | `Discrete(2)` |
| 跳跃 | `SPACE` | `Discrete(2)` |
| 交互 | `E`（使用/开背包） `Q`（丢弃） `F`（交换主副手） | `Discrete(2)` |
| 修饰 | `LEFT_SHIFT`（潜行） `LEFT_CONTROL`（疾跑） | `Discrete(2)` |
| 快捷栏 | `1` … `9` | `Discrete(2)` |
| 鼠标键 | `LEFT_BUTTON` `RIGHT_BUTTON` `MIDDLE_BUTTON` | `Discrete(2)` |
| 视角 | `cursor_delta` | `Box(-1200, 1200, (2,), int32)` |

`cursor_delta` 是**鼠标像素位移**，不是绝对位置——相对当前光标移动 `(dx, dy)`。

#### 关于 `Discrete(2)` 的三个细节

**① 取值就是 `{0, 1}`，dtype 是 `int64`。**

```python
NO_PRESS = np.int64(0)    # 松开
PRESS    = np.int64(1)    # 按下
```

实现里用 `bool(action_val)` 判断（`env_util.py:90`），所以传 `True`/`False` 也能用。
但建议统一用 `np.int64(0/1)`。

**② 不传的键 = 不管它，维持上一次状态。**

`process_action()` 遍历的是 **`action` 字典里实际存在的键**。所以：

| 做法 | 效果 |
|---|---|
| 传 `W=np.int64(1)` | 按下 W |
| 传 `W=np.int64(0)` | 松开 W |
| **不传 `W`** | **不动它** —— 沿用上一帧状态 |

这意味着只传 `{"W": 1}` 会漏掉松开逻辑：上一轮按下的 `SPACE` 不会被松开，会一直按着。
所以用 `get_noop_action()` 打底再改：

```python
action = env.get_noop_action()   # 23 个键显式置 0
action["W"] = np.int64(1)        # 只改要按的
```

**③ 只有状态变化才发送事件。**

`update()` 会和上一帧做差集（`env_util.py:56-68`），只发新增的按下和松开：

```python
new_presses  = pressed - self.pressed_set
new_releases = self.pressed_set & released
```

所以连续多步传 `W=1` 只会发一次 PRESS 事件，之后 Minecraft 保持按住。这是省带宽的优化，
对写代码没有影响——照常每步传完整动作字典即可。

`env.get_noop_action()` 返回一个全 0 的动作字典：

```python
action = env.get_noop_action()
action["W"] = np.int64(1)                                  # 前进
action["cursor_delta"] = np.array((60, 0), dtype=np.int32)  # 右转
```

### 3.2 `MinerlEnv`

**观测空间**：`pov` — `Box(0, 255, (480, 854, 3), uint8)`

**动作空间**（24 个键，MineRL 1.0 命名）

| 类别 | 键 |
|---|---|
| 移动 | `forward` `back` `left` `right` |
| 移动修饰 | `jump` `sneak` `sprint` |
| 交互 | `attack` `use` `drop` `pickItem` `swapHands` `inventory` |
| 快捷栏 | `hotbar.1` … `hotbar.9` |
| 视角 | `camera` — `Box(-180.0, 180.0, (2,), float32)` |
| 其他 | `ESC` |

和 `MCioEnv` 的区别：视角用**角度**而不是像素，观测没有位置信息。

## 4. 通用 API（基类 `MCioBaseEnv`）

### `reset(seed=None, *, options=None) -> (obs, info)`

建立连接并返回第一帧。**会先 `close()` 掉之前的连接**，所以可反复调用。

`options` 是 `ResetOptions`（dict），目前只支持一个键：

```python
obs, info = env.reset(options={
    "commands": [
        "time set day",
        "weather clear",
        "gamemode creative",
        "tp @p 0 100 0",
        "give @p diamond_sword",
    ]
})
```

命令**不要带开头的 `/`**。

不同命令生效耗时不同（`time set` 可能要 ~20 tick），发完命令建议
`env.skip_steps(20)` 确保生效。

### `step(action, *, options=None) -> (obs, reward, terminated, truncated, info)`

| 返回 | 类型 | 说明 |
|---|---|---|
| `obs` | dict | 观测 |
| `reward` | `int` | **恒为 0**，见「能力边界」 |
| `terminated` | `bool` | **血量归零时为 True**（即死亡） |
| `truncated` | `bool` | **恒为 False** |
| `info` | `dict` | **恒为空 `{}`** |

`options` 同 `reset`，可在 step 中下发命令。

**`terminated` 之后必须先 `reset()` 再 `step()`**，否则抛断言错误：

```
AssertionError: Must call reset() after termination
```

### `skip_steps(n_steps) -> (obs, reward, terminated, truncated, info)`

连续发 n 个空动作并返回最后一帧。用于等命令生效，或做 frame skip。

```python
env.skip_steps(4)      # 跳过 4 tick
```

### `render() -> NDArray | None`

- `render_mode="human"`：把最新帧画到 GLFW 窗口，返回 `None`
- `render_mode="rgb_array"`：返回最新帧 `NDArray`
- `render_mode=None`（默认）：什么都不做

### `close()`

断开 socket 连接。**不关闭游戏**。可重复调用。

## 5. 观测包里的更多数据

`MCioEnv` 只暴露 4 个观测字段，但原始 `ObservationPacket` 有 20 个：

```
version  sequence  mode  last_action_sequence  frame_sequence
frame  frame_width  frame_height  frame_type
cursor_mode  cursor_pos
health  player_pos  player_pitch  player_yaw
inventory_main  inventory_armor  inventory_offhand
options
```

**血量通过 `env.health` 取**（`info` 是空的）：

```python
obs, info = env.reset()
print(env.health)      # 20.0
```

基类里把它存成了属性：

```python
self.health = packet.health
if self.health == 0.0:
    self.terminated = True
```

要拿背包、护甲、光标位置等，继承 `MCioBaseEnv` 自己扩展观测空间：

```python
from mcio_ctrl.envs.base_env import MCioBaseEnv

class MyEnv(MCioBaseEnv):
    def _packet_to_observation(self, packet):
        return {
            "frame": self.last_frame,
            "health": packet.health,
            "inventory": packet.inventory_main,
            "cursor_pos": packet.cursor_pos,
        }
    def _action_to_packet(self, action, commands=None):
        ...
```

## 6. 控制样例

### 6.1 最小可用：走 20 步

```python
import numpy as np
from mcio_ctrl import types
from mcio_ctrl.envs import mcio_env

opts = types.RunOptions(width=854, height=480, mcio_mode=types.MCioMode.ASYNC)

with mcio_env.MCioEnv(opts, render_mode="human") as env:
    obs, info = env.reset()
    print(f"起始位置 {obs['pos']}")

    for i in range(20):
        action = env.get_noop_action()
        action["W"] = np.int64(1)                  # 一直前进
        obs, reward, terminated, truncated, info = env.step(action)
        env.render()
        print(f"  步 {i}: pos={np.round(obs['pos'], 2)} health={env.health}")

        if terminated:
            obs, info = env.reset()                # 死亡必须 reset
```

### 6.2 完整控制样例：前进 + 卡住就跳 + 转向

```python
"""一直前进，卡住就跳，连续卡住就转向。"""
import argparse
import time
from collections import deque

import numpy as np
from mcio_ctrl import types
from mcio_ctrl.envs import mcio_env


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["sync", "async"], default="async")
    p.add_argument("--rate", type=float, default=20.0, help="每秒几步，0=全速")
    p.add_argument("--window", type=int, default=20, help="判定移动的窗口步数")
    p.add_argument("--min-move", type=float, default=0.25, help="窗口位移低于此值算卡住")
    p.add_argument("--turn-after", type=int, default=5, help="连续卡住多少次后转向")
    args = p.parse_args()

    mode = types.MCioMode.SYNC if args.mode == "sync" else types.MCioMode.ASYNC
    opts = types.RunOptions(width=854, height=480, mcio_mode=mode)

    with mcio_env.MCioEnv(opts, render_mode="human") as env:
        obs, info = env.reset()

        recent = deque(maxlen=args.window)
        x0, z0 = float(obs["pos"][0]), float(obs["pos"][2])
        recent.append((x0, z0))

        stuck = 0
        jump_left = 0
        step = 0
        next_t = 0.0

        while True:
            # ---- 限速 ----
            if args.rate > 0:
                now = time.monotonic()
                if now < next_t:
                    time.sleep(next_t - now)
                next_t = time.monotonic() + 1.0 / args.rate

            x, z = float(obs["pos"][0]), float(obs["pos"][2])
            recent.append((x, z))

            # ---- 卡住检测 ----
            if len(recent) >= args.window:
                dx = recent[-1][0] - recent[0][0]
                dz = recent[-1][1] - recent[0][1]
                if (dx * dx + dz * dz) ** 0.5 < args.min_move:
                    stuck += 1
                    jump_left = 4                 # 跳 4 tick
                else:
                    stuck = 0

            # ---- 组动作 ----
            action = env.get_noop_action()
            action["W"] = np.int64(1)             # 始终前进
            if jump_left > 0:
                action["SPACE"] = np.int64(1)
                jump_left -= 1
            if stuck >= args.turn_after:          # 卡太久，转向绕路
                action["cursor_delta"] = np.array((90, 0), dtype=np.int32)
                stuck = 0

            obs, reward, terminated, truncated, info = env.step(action)
            env.render()
            step += 1

            if step % 20 == 0:
                print(f"  步 {step:5d} pos={np.round(obs['pos'], 2)} "
                      f"health={env.health} 卡住={stuck}")

            if terminated:                        # 死亡 → 重开
                print(f"  步 {step}: 死亡，重开")
                obs, info = env.reset()
                x0, z0 = float(obs["pos"][0]), float(obs["pos"][2])
                recent.clear()
                recent.append((x0, z0))
                stuck = 0


if __name__ == "__main__":
    main()
```

### 6.3 下发命令做任务初始化

```python
obs, info = env.reset(options={
    "commands": ["time set day", "weather clear", "tp @p 0 100 0"]
})
env.skip_steps(20)          # 等命令生效
```

### 6.4 接入 Stable-Baselines3

```python
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from mcio_ctrl import types
from mcio_ctrl.envs import minerl_env

opts = types.RunOptions(width=64, height=64, mcio_mode=types.MCioMode.SYNC)
env = Monitor(minerl_env.MinerlEnv(opts))

model = PPO("CnnPolicy", env, n_steps=256, verbose=1)
model.learn(total_timesteps=100_000)
```

`pov` 是标准 `uint8` 图像，`CnnPolicy` 可直接用。**但 `reward` 恒为 0，
必须先自己定义奖励**（见下一节）。

## 7. 能力边界

### 能做到

- **真实第一人称 RGB 画面**，`uint8`，尺寸可配
- **键鼠级动作**：所有常见按键 + 鼠标三个键 + 鼠标像素位移
- **状态观测**：世界坐标、朝向
- **下发任意 Minecraft 命令**（teleport / time / weather / give / gamemode …）
- **SYNC 全速**：官方称 tick timer 被禁用，速度只受硬件限制
- **人机同玩**（ASYNC + `MCIO_OPEN_TO_LAN=true`）
- **无头模式**（`hide_window=True`）
- **兼容 MineRL 1.0 动作/观测空间**，可跑 MineRL 生态的现成 Agent
- **兼容性能 mod**（如 Sodium 提速）
- **支持资源包 / 着色器**，可做域随机化

### 需要自己补

| 限制 | 说明 |
|---|---|
| **`reward` 恒为 0** | `_process_step()` 直接 `return 0, self.terminated, False`。任何训练都必须自己定义奖励 |
| **`info` 恒为空** | `_get_info()` 返回 `{}` |
| **`truncated` 恒为 False** | 没有内置时间限制，要自己限步 |
| **观测字段少** | `MCioEnv` 只有 4 个；血量在 `env.health`；背包/护甲等在原始包里但不暴露 |
| **没有方块 / 实体信息** | 纯像素 + 坐标。做导航、避障需自己从画面推断，或用命令查询 |
| **只能控制单个玩家** | 一个环境对应一个 bot |
| **只支持 MC 1.21.3** | mod 版本锁在这个游戏版本 |
| **仅 Java 版** | 基岩版不行 |
| **需要 Fabric** | 不兼容 Forge / NeoForge |

### 扩展方式

| 想做 | 怎么做 |
|---|---|
| 自定义奖励 | 覆写 `_process_step()` |
| 更多观测字段 | 覆写 `_packet_to_observation()`，从 `ObservationPacket` 取 |
| 自定义动作空间 | 覆写 `_action_to_packet()`，把离散动作映射到多个键 |
| frame skip | 用 `skip_steps(n)` |
| 多环境并行 | 多个 `MCioEnv` 实例 + 不同端口（`MCIO_ACTION_PORT` / `MCIO_OBSERVATION_PORT`） |

## 8. 配置项速查

通过 `RunOptions(...)` 传参，或设环境变量给 Java 侧。

| 参数 | 环境变量 | 默认 | 说明 |
|---|---|---|---|
| `mcio_mode` | `MCIO_MODE` | `ASYNC` | `OFF` / `SYNC` / `ASYNC` |
| `width` / `height` | — | 640 / 360 | 画面尺寸 |
| `action_port` | `MCIO_ACTION_PORT` | **4001** | 动作端口 |
| `observation_port` | `MCIO_OBSERVATION_PORT` | **8001** | 观测端口 |
| `hide_window` | `MCIO_HIDE_WINDOW` | `false` | 隐藏游戏窗口（无头） |
| `open_to_lan` | `MCIO_OPEN_TO_LAN` | `false` | 开局域网供人加入 |
| `open_to_lan_port` | `MCIO_OPEN_TO_LAN_PORT` | 12001 | LAN 端口 |
| `open_to_lan_mode` | `MCIO_OPEN_TO_LAN_MODE` | `SPECTATOR` | LAN 里的游戏模式 |
| `instance_name` | — | `None` | 给了就由库启动游戏 |
| `world_name` | — | `None` | 配合 `instance_name` |
| `mc_username` | — | — | 机器人显示名 |
| `java_path` | — | — | 指定 java 可执行文件 |
| — | `MCIO_UNLIMITED_FPS` | SYNC 下 true | 解除帧率限制 |
| — | `MCIO_PRELOAD_CHUNKS` | `true` | 预载区块（仅 SYNC） |
| — | `MCIO_SKIN` | 15 | 皮肤选择 |
| — | `MCIO_STATS_RESET` | `true` | 连接时重置统计 |

完整列表见 `mcio_ctrl` Wiki 的 MCioConfig 页。

## 9. 故障排查

| 症状 | 原因 |
|---|---|
| `reset()` 一直卡住 | 游戏侧和控制端模式不一致 |
| `CBORDecodeError: error decoding map` | `cbor2` 装成了 6.x，需 `pip install "cbor2<6"` |
| `AssertionError: Must call reset() after termination` | 死亡后没 `reset()` |
| `info` 里拿不到血量 | 血量在 `env.health`，`info` 恒为空 |
| 游戏显示「未响应」 | SYNC 模式正常现象，点「等待」 |
| 死亡后卡在死亡界面 | 缺 `doImmediateRespawn`，执行 `/gamerule doImmediateRespawn true` |
