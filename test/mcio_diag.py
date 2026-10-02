"""诊断 MCio 观测包：发一个动作触发，再抓原始 CBOR 响应。

SYNC 模式下 MCio 不会主动发观测，必须先发动作。

用法：游戏进入世界后运行
    conda activate mcio
    cd D:\\codes\\Mine-player
    python mcio_diag.py
"""

from __future__ import annotations

import pprint
import time

import zmq

from mcio_ctrl import cbor as mcio_cbor
from mcio_ctrl import network, types


def main() -> None:
    print(f"MCIO_PROTOCOL_VERSION = {network.MCIO_PROTOCOL_VERSION}")
    print(f"动作端口 {types.DEFAULT_ACTION_PORT} / 观测端口 {types.DEFAULT_OBSERVATION_PORT}\n")

    ctx = zmq.Context()

    # 动作：PUSH（我们 -> 游戏）
    action_sock = ctx.socket(zmq.PUSH)
    action_sock.connect(f"tcp://{types.DEFAULT_HOST}:{types.DEFAULT_ACTION_PORT}")

    # 观测：PULL（游戏 -> 我们）
    obs_sock = ctx.socket(zmq.PULL)
    obs_sock.connect(f"tcp://{types.DEFAULT_HOST}:{types.DEFAULT_OBSERVATION_PORT}")

    print("已连接两个 socket，等待握手 2 秒……")
    time.sleep(2.0)

    def send_action(seq: int) -> None:
        pkt = network.ActionPacket(version=network.MCIO_PROTOCOL_VERSION, sequence=seq)
        raw = mcio_cbor.encode(pkt)
        action_sock.send(raw)
        print(f"  -> 已发送动作 seq={seq}（{len(raw)} 字节）")

    print("\n发送第一个动作触发观测……")
    t0 = time.time()
    send_action(1)

    if not obs_sock.poll(15000, zmq.POLLIN):
        print("  15 秒内没收到观测包")
        print("  可能：游戏没在世界里 / 不是 SYNC 模式 / 窗口被关了")
        action_sock.close()
        obs_sock.close()
        ctx.term()
        return

    print(f"  收到！延迟 {time.time() - t0:.2f}s\n")

    for i in range(3):
        if i > 0:
            if not obs_sock.poll(10000, zmq.POLLIN):
                print(f"  第 {i + 1} 个包超时")
                break
        pbytes = obs_sock.recv()

        print(f"===== 包 {i + 1} =====")
        print(f"  原始长度      : {len(pbytes)} 字节")
        print(f"  期望帧大小    : 480*854*3 = {480 * 854 * 3} 字节")
        print(f"  恰好等于帧大小: {len(pbytes) == 480 * 854 * 3}")
        print(f"  头部 180 字节 : {pbytes[:180]!r}")

        # 1) 原生 cbor2 解码，看真实类型
        try:
            obj = mcio_cbor.cbor2.loads(pbytes)
            print(f"  原生 cbor2 类型: {type(obj).__name__}")
            if isinstance(obj, dict):
                print(f"  字典键 ({len(obj)} 个): {list(obj.keys())}")
            else:
                r = pprint.pformat(obj)
                print(f"  repr 前 400    : {r[:400]}")
        except Exception as exc:
            print(f"  原生 cbor2 失败: {type(exc).__name__}: {exc}")

        # 2) mcio_ctrl 自己的解码器
        try:
            obj2 = mcio_cbor.decode(pbytes)
            print(f"  mcio decode 类型: {type(obj2).__name__}")
        except Exception as exc:
            print(f"  mcio decode 失败: {type(exc).__name__}: {exc}")

        # 3) 走正规解包路径看它报什么
        try:
            pkt = network.ObservationPacket.unpack(pbytes)
            if pkt is None:
                print("  ObservationPacket.unpack 返回 None（内部已记日志）")
            else:
                print(f"  ObservationPacket OK: mode={pkt.mode} "
                      f"{pkt.frame_height}x{pkt.frame_width} "
                      f"frame={len(pkt.frame)} 字节 health={pkt.health}")
        except Exception as exc:
            print(f"  unpack 抛异常   : {type(exc).__name__}: {exc}")

        with open(f"mcio_pkt_{i + 1}.bin", "wb") as f:
            f.write(pbytes)
        print(f"  已保存 mcio_pkt_{i + 1}.bin\n")

        send_action(i + 2)

    action_sock.close()
    obs_sock.close()
    ctx.term()


if __name__ == "__main__":
    main()
