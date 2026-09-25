# Mine-player

本项目通过 CraftGround 在本机启动 Minecraft，直接获取画面和玩家状态并发送动作，不再使用屏幕截图或网络转发。

## 创建环境

```bash
conda env create -f environment.yml
conda activate mine-player
```

## 运行

```bash
python main.py
```

程序会显示 CraftGround 返回的 RGB 画面，并定期输出坐标、视角、生命值、饥饿值和背包信息。画面窗口支持以下按键：

- `W/A/S/D`：移动
- `空格`：跳跃
- `F`：攻击
- `E`：使用物品
- `I/J/K/L`：转动视角
- `Esc`：退出

只读取信息、不显示 OpenCV 窗口时运行：

```bash
python main.py --no-viewer
```

首次启动时 CraftGround 需要准备并启动 Minecraft，耗时会比之后启动更长。
