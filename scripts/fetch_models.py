# -*- coding: utf-8 -*-
"""下载 Kokoro 语音模型到 models/（GitHub Actions 每次运行前调用；已存在则跳过）。
模型源用 ModelScope（国内可达，海外 runner 一般也能连）：
  - kokoro-v1.0.onnx  ← OllmOne/Kokoro-82M-v1.0-ONNX
  - voices.bin        ← onnx-community/Kokoro-82M-v1.0-ONNX 的 voices/*.bin 合并而成
    （那些 .bin 是裸 float32，形状 (510,1,256)，需要自己打包成 npz）
"""
import os
import sys
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(BASE, "models")
ONNX = os.path.join(MODELS, "kokoro-v1.0.onnx")
VOICES = os.path.join(MODELS, "voices.bin")
ONNX_MIN = 300 * 1024 * 1024

ONNX_URL = "https://modelscope.cn/models/OllmOne/Kokoro-82M-v1.0-ONNX/resolve/master/kokoro-v1.0.onnx"
VOICE_BASE = "https://modelscope.cn/models/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/master/voices/"
VOICE_NAMES = ["af_heart", "af_bella", "af_nicole", "am_michael", "am_adam",
               "bm_george", "bm_fable"]


def log(msg):
    print(msg, flush=True)


def download_onnx():
    if os.path.exists(ONNX) and os.path.getsize(ONNX) > ONNX_MIN:
        log(f"  kokoro-v1.0.onnx 已存在 ({os.path.getsize(ONNX)//1048576} MB)")
        return
    os.makedirs(MODELS, exist_ok=True)
    for attempt in range(3):
        try:
            log(f"  下载 onnx (第 {attempt+1} 次)...")
            tmp = ONNX + ".part"
            urllib.request.urlretrieve(ONNX_URL, tmp)
            os.replace(tmp, ONNX)
            log(f"  完成 {os.path.getsize(ONNX)//1048576} MB")
            return
        except Exception as e:
            log(f"  失败: {type(e).__name__} {e}")
    raise RuntimeError("onnx 下载失败")


def build_voices():
    if os.path.exists(VOICES) and os.path.getsize(VOICES) > 1024 * 1024:
        log(f"  voices.bin 已存在 ({os.path.getsize(VOICES)//1024} KB)")
        return
    import io
    import numpy as np
    os.makedirs(MODELS, exist_ok=True)
    merged = {}
    for v in VOICE_NAMES:
        raw = urllib.request.urlopen(VOICE_BASE + v + ".bin", timeout=90).read()
        arr = np.frombuffer(raw, dtype=np.float32)
        if arr.size % 256:
            raise RuntimeError(f"{v}.bin 长度异常: {arr.size}")
        merged[v] = arr.reshape(510, 1, 256)
        log(f"  {v} ok")
    buf = io.BytesIO()
    np.savez(buf, **merged)
    with open(VOICES, "wb") as f:
        f.write(buf.getvalue())
    log(f"  合并完成 {os.path.getsize(VOICES)//1024} KB, {len(merged)} 个音色")


def main():
    log("[models] 检查 Kokoro 模型")
    download_onnx()
    build_voices()
    log("[models] 就绪")


if __name__ == "__main__":
    sys.exit(main())
