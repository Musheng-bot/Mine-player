# Mine-player

用 Python 控制本机 Minecraft 里的玩家：拿到**真实的第一人称画面**，发送**键鼠级动作**。

技术路线是**客户端 Mod**（[MCio](https://modrinth.com/mod/mcio)）：

```
Minecraft 客户端 + MCio(Fabric Mod)
        ↕  ZeroMQ（消息通信）
Python (mcio_ctrl)
```

也就是「装一个模组进自己的客户端，靠消息收发」——**不需要编译任何 C++**，
不需要 MSVC / CMake / Gradle，不需要服务端。

## 环境

```powershell
conda env create -f environment.yml
conda activate mcio
```

环境已定格到精确版本（见 `environment.yml`），核心是：

| 包 | 版本 | 说明 |
|---|---|---|
| `mcio-ctrl` | 1.5.2 | Python 控制层 + Gymnasium 环境 |
| `cbor2` | **5.9.0** | ⚠️ **必须 5.x**，见下面「已知坑」 |
| `pyzmq` | 27.2.0 | 与 mod 通信 |
| `gymnasium` | 1.3.0 | 环境接口 |

## 客户端配置（PCL2）

| 项 | 值 |
|---|---|
| 游戏版本 | **1.21.3**（MCio 只支持这个版本） |
| Fabric Loader | **0.19.5** |
| mods | `mcio-1.6.1+1.21.3.jar`、`fabric-api-0.114.1+1.21.3.jar` |
| **JVM 参数** | `-DMCIO_MODE=sync` 或 `-DMCIO_MODE=async` |

### 参数必须放在「JVM 参数」栏

`-DMCIO_MODE` 是 **Java 系统属性**，只有在 **JVM 参数**栏（主类之前）才生效。
放进「游戏参数」栏会被忽略，日志里出现：

```
Completely ignored arguments: [-DMCIO_MODE=sync]
```

**验证**：日志里应该是 `MCIO_MODE=SYNC` 或 `MCIO_MODE=ASYNC`，不是别的。

## 两种模式

| | **SYNC** | **ASYNC** |
|---|---|---|
| 游戏是否等 Agent | 等（暂停） | **不等**，按 20 TPS 自己跑 |
| 速度 | 全速（实测 **~700 TPS**） | 真实 20 TPS |
| 观测 | 一步一帧，严格对应 | 异步推送，慢则丢帧（只留最新） |
| 你能否一起玩 | 不能（游戏冻着） | ✅ 可以（配 `-DMCIO_OPEN_TO_LAN=true`） |
| 适合 | RL 训练 | 看效果 / 交互 / 演示 |

**两边必须一致**，否则 `reset()` 会卡死：

| 游戏 | Python | 结果 |
|---|---|---|
| SYNC | SYNC | ✅ |
| ASYNC | ASYNC | ✅ |
| SYNC | ASYNC | ❌ 卡住 |
| ASYNC | SYNC | ❌ 卡住 |

### ⚠️ `for_connect()` 会把模式写死成 SYNC

```python
# mcio_ctrl/types.py:398
def for_connect(...):
    return cls(width=..., height=..., mcio_mode=MCioMode.SYNC)   # 固定 SYNC
```

要用 ASYNC 必须**自己构造 `RunOptions`**：

```python
from mcio_ctrl import types
opts = types.RunOptions(width=854, height=480, mcio_mode=types.MCioMode.ASYNC)
```

### 窗口「没有响应」是正常的

SYNC 模式下游戏暂停等 Agent，Windows 会判定它无响应并提示关闭。
**点「等待」，不要关。**

## 运行

```powershell
conda activate mcio
cd D:\codes\Mine-player

# 观测：开一个实时窗口显示画面 + 打印状态
python mcio_observe.py --mode async

# 主程序：一直前进，卡住就跳
python mcio_walk.py --rate 20        # 20 = 原版节奏；0 = 全速
```

## 观测与动作

```python
import mcio_ctrl as mcio
from mcio_ctrl import types
from mcio_ctrl.envs import mcio_env
import numpy as np

opts = types.RunOptions(width=854, height=480, mcio_mode=types.MCioMode.ASYNC)
env = mcio_env.MCioEnv(opts, render_mode="human")   # "human" 开观测窗口
obs, info = env.reset()

# ---- 观测 ----
obs["frame"]     # (480, 854, 3) uint8 —— 第一人称画面，方向正确，无需翻转
obs["pos"]       # (3,) float32       世界坐标
obs["yaw"]       # (1,) float32
obs["pitch"]     # (1,) float32
env.health       # float              ← 血量在这里！
info             # {}                 ← 永远是空字典

# ---- 动作（离散 0/1 + 鼠标像素位移）----
env.step({
    "W": np.int64(1),                                   # 前进
    "SPACE": np.int64(1),                               # 跳跃
    "LEFT_BUTTON": np.int64(1),                         # 攻击
    "cursor_delta": np.array((60, 0), dtype=np.int32),  # 转视角
})

env.render()     # 把最新帧画到窗口（render_mode="human" 时）
env.close()      # 断开，游戏继续运行
```

**动作键全集**：`W A S D SPACE Q E F LEFT_SHIFT LEFT_CONTROL 1..9
LEFT_BUTTON RIGHT_BUTTON MIDDLE_BUTTON cursor_delta`

**血量在 `env.health`，不在 `info` 里** —— `MCioEnv._get_info()` 返回 `{}`，
而 `base_env.py:171` 把 `packet.health` 存到了 `self.health`。

## 已知坑

### 1. cbor2 6.x 会让所有观测包解码失败 ⚠️

**症状**：

```
CBOR load error: CBORDecodeError: error decoding map
AttributeError: 'bool' object has no attribute 'pop'
Invalid ObservationPacket
```

**原因**：cbor2 6.x 改了 `object_hook` 的调用约定（5.x 传 `(decoder, map)`，
6.x 只传一个已解码的值），而 `mcio_ctrl/cbor.py:47` 假设收到 dict：

```python
mcio_type = obj_dict.pop(MCIO_PROTOCOL_TYPE, None)   # obj_dict 其实是 bool
```

**`mcio_ctrl` 的依赖里只写 `cbor2` 没有上限**，所以 `pip install mcio_ctrl`
会自动装到 6.x 然后坏掉。

**修复**：`pip install "cbor2<6"`（5.9.0 实测可用）

### 2. SYNC 模式下必须先发动作才有观测

MCio 不主动推送观测——它等你发动作，处理 1 tick 后再返回。
所以写裸 socket 客户端时，**光收不发会一直等不到数据**。

### 3. 死亡后必须先 reset 再 step

```python
# base_env.py:253
assert not self.terminated, "Must call reset() after termination"
```

而且重生是靠**动作驱动**的（`_reset_terminated_hack` 连发最多 100 个空动作）。
建议在游戏里开一次：

```
/gamerule doImmediateRespawn true
```

### 4. 端口

| 用途 | 默认 |
|---|---|
| 动作 | **4001** |
| 观测 | **8001** |

## 目录结构

```
mcio_observe.py      观测：实时窗口 + 状态打印
mcio_walk.py         主程序：一直前进，卡住就跳
environment.yml      环境定格
test/
  mcio_connect.py    连接测试：取一帧存图 + 测四类动作
  mcio_capture.py    抓图：连续抓多张存 PNG
  mcio_keepalive.py  空转：只推进世界，把死亡/卡住的状态推过去
  mcio_diag.py       底层诊断：发动作并抓原始观测包（排查连接/解码问题）
```

`test/` 里的脚本会**在运行目录**留下 PNG/bin 产物（已 gitignore）。

## 性能参考

| 指标 | 实测 |
|---|---|
| SYNC 全速 | ~700 步/秒（约 35 倍于原版 20 TPS） |
| ASYNC | 20 TPS（真实时间） |
| 画面 | 854x480 RGB，约 1.2 MB/帧 |

## 相关链接

- [MCio mod](https://modrinth.com/mod/mcio) · [mcio_ctrl](https://pypi.org/project/mcio-ctrl/) ·
  [文档 Wiki](https://github.com/twoturtles/mcio_ctrl/wiki)
- [VPT / STEVE-1 示例](https://github.com/jxiong21029/mcio-vpt-example)
