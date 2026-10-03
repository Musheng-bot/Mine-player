# Mine-player

用代码控制本机 Minecraft 里的玩家：拿到真实的第一人称画面，发送键鼠级动作。

技术路线是客户端 Mod（[MCio](https://modrinth.com/mod/mcio)）：往自己的客户端装一个
Fabric 模组，通过 ZeroMQ 收发消息。选用 MC 版本 `1.21.3`。

```
Minecraft 客户端 + MCio mod   ←→   mcio_ctrl
```

## 环境

```powershell
conda env create -f environment.yml
conda activate mcio
```

## 客户端

| 项            | 值                                                       |
| ------------- | -------------------------------------------------------- |
| 游戏版本      | **1.21.3**                                               |
| Fabric Loader | 0.19.5                                                   |
| mods          | `mcio-1.6.1+1.21.3.jar`、`fabric-api-0.114.1+1.21.3.jar` |
| JVM 参数      | `-DMCIO_MODE=sync` 或 `-DMCIO_MODE=async`                |

## 运行

先启动游戏并进入世界，然后：

```powershell
conda activate mcio
cd <path/to/Mine-player>

python mcio_walk.py --rate 20        # 一直前进，卡住就跳
python mcio_observe.py --mode async  # 开窗口实时观察画面
```

## 文档

- [API 文档](docs/api.md) —— 启动/关闭、观测与动作、能力边界、控制样例、故障排查
- [MCio mod](https://modrinth.com/mod/mcio) · [mcio_ctrl](https://pypi.org/project/mcio-ctrl/)
- [MCio Wiki](https://github.com/twoturtles/mcio_ctrl/wiki)
