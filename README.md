# Mine-player

## 项目环境

在项目根目录安装依赖：

```bash
uv sync
```

## `mine_env` 画面传输

`mine_env` 通过 TCP 将一台机器捕获的画面发送到另一台机器。两台机器分别修改 `config/env.yaml` 中自己使用的部分：

```yaml
sender:
  host: "192.168.1.20" # receiver 所在机器的 IP
  port: 5000
  window: "Minecraft"  # 不区分大小写的窗口标题关键字
  region: null         # 或填写 "0,0,1920,1080"，与 window 二选一
  fps: 15
  quality: 80
  refresh_window: 1.0
receiver:
  host: "0.0.0.0"     # 监听本机所有 IPv4 接口
  port: 5000
  save: null           # 可填写 JPEG 保存路径
```

先在接收机器启动：

```bash
uv run mine-env-receiver
```

再在发送机器启动：

```bash
uv run mine-env-sender
```

两端端口必须一致，网络和防火墙需要允许连接。需要使用其他配置文件时，仅通过 `--config PATH` 指定。
