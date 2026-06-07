"""
ReelSage 本地模型一键下载（完全独立版，只用 Python 标准库）。

特点：
- **零第三方依赖**：只用 urllib / json / os，即使 .venv 不完整也能跑
- 默认走 hf-mirror.com 国内镜像，断点续传 + 原子写入 + 404 自动跳过
- 自动创建所有目标文件夹，位置与 config_local.json 完全一致

下载目标：
    Qwen3-VL 4B  ->  ./qwen3-vl-4b                          （VLM，必需，二选一）
    Qwen3-VL 8B  ->  ./qwen3-vl-8b                          （VLM，必需，二选一）
    BGE-M3       ->  ./models/embedding/bge-m3              （可选，文本 RAG）
    Chinese-CLIP ->  ./models/vision/chinese-clip-vit-base  （可选，视觉 RAG）

用法：
    python download_models.py           # 交互菜单
    python download_models.py 8b        # 直接下 8B
    python download_models.py 4b
    python download_models.py rag       # 两个 RAG 模型
    python download_models.py all       # 8B + 两个 RAG
镜像切换：设环境变量 REELSAGE_MIRROR = hf-mirror | huggingface
"""

from __future__ import annotations

import http.client
import json
import os
import socket
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# 强制 UTF-8 控制台输出，避免 Windows GBK 控制台打印中文/进度条时崩溃
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# ----------------------- 配置 -----------------------

_MIRROR_BASE = {
    "hf-mirror": "https://hf-mirror.com",
    "huggingface": "https://huggingface.co",
}
MIRROR = os.environ.get("REELSAGE_MIRROR", "hf-mirror")
BASE = _MIRROR_BASE.get(MIRROR, _MIRROR_BASE["hf-mirror"])

UA = {"User-Agent": "ReelSage/3.0 (+model-downloader)"}

# 模型 -> (HF 仓库, 目标目录)
VLM_MODELS = {
    "4b": ("Qwen/Qwen3-VL-4B-Instruct", "./qwen3-vl-4b"),
    "8b": ("Qwen/Qwen3-VL-8B-Instruct", "./qwen3-vl-8b"),
}
BGE_REPO = "BAAI/bge-m3"
BGE_DIR = "./models/embedding/bge-m3"

# Chinese-CLIP：从 Hugging Face 下载官方仓库（OFA-Sys）
CNCLIP_REPO = "OFA-Sys/chinese-clip-vit-base-patch16"
CNCLIP_DIR = "./models/vision/chinese-clip-vit-base"

ALL_DIRS = [
    "./qwen3-vl-4b",
    "./qwen3-vl-8b",
    "./models",
    "./models/embedding",
    "./models/embedding/bge-m3",
    "./models/vision",
    "./models/vision/chinese-clip-vit-base",
]


# ----------------------- 工具 -----------------------

def _human(n: float) -> str:
    """字节 -> 人类可读（B/KB/MB/GB）。"""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _eta(seconds: float) -> str:
    if seconds <= 0 or seconds != seconds or seconds == float("inf"):
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _bar(frac: float, width: int = 26) -> str:
    """生成可视化进度条，如 [████████░░░░░░] 。"""
    frac = max(0.0, min(1.0, frac))
    filled = int(round(frac * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def _draw_progress(done: int, total: int, t0: float) -> None:
    elapsed = max(0.001, time.time() - t0)
    spd = done / elapsed  # bytes/s
    if total > 0:
        frac = done / total
        remain = (total - done) / spd if spd > 0 else 0
        line = (
            f"\r   {_bar(frac)} {frac * 100:5.1f}%  "
            f"{_human(done)}/{_human(total)}  "
            f"{_human(spd)}/s  ETA {_eta(remain)}   "
        )
    else:
        line = f"\r   {_human(done)}  {_human(spd)}/s   "
    sys.stdout.write(line)
    sys.stdout.flush()


def safetensors_intact(path: str) -> bool:
    """校验 .safetensors 是否完整：文件实际大小 >= 8 + 头长度 + 最大张量结束偏移。

    截断/损坏（如下载中断后被误当完整文件）会返回 False。
    """
    try:
        sz = os.path.getsize(path)
        with open(path, "rb") as fp:
            raw = fp.read(8)
            if len(raw) < 8:
                return False
            n = struct.unpack("<Q", raw)[0]
            if n <= 0 or n > 100 * 1024 * 1024:  # 头长度异常
                return False
            hdr = json.loads(fp.read(n).decode("utf-8", "replace"))
        mx = max(
            (v["data_offsets"][1] for k, v in hdr.items()
             if k != "__metadata__" and isinstance(v, dict) and "data_offsets" in v),
            default=0,
        )
        return sz >= 8 + n + mx
    except Exception:  # noqa: BLE001
        return False


def file_intact(path: str) -> bool:
    """通用完整性判断：.safetensors 用头部校验；其它文件只要求存在且非空。"""
    if not os.path.isfile(path):
        return False
    if path.lower().endswith(".safetensors"):
        return safetensors_intact(path)
    return os.path.getsize(path) > 0


def _skip(path: str) -> bool:
    name = os.path.basename(path).lower()
    if name.startswith("."):
        return True
    bad = (".gitattributes", "readme", ".md", ".gitignore", "training_args")
    return any(b in path.lower() for b in bad)


def list_repo_files(repo: str, max_tries: int = 8) -> list[str]:
    url = f"{BASE}/api/models/{repo}/tree/main?recursive=true"
    data = None
    for i in range(1, max_tries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            break
        except _RETRIABLE as exc:
            wait = min(30, 3 * i)
            print(f"    [清单获取失败] {wait}s 后重试 ({i}/{max_tries})... ({exc})")
            time.sleep(wait)
    if data is None:
        raise RuntimeError("获取文件清单多次失败，请检查网络或切换镜像。")
    files = [
        it["path"]
        for it in data
        if isinstance(it, dict) and it.get("type") == "file" and not _skip(it.get("path", ""))
    ]
    files.sort()
    return files


# 断线时被视为"可重试"的网络异常
_RETRIABLE = (
    urllib.error.URLError,
    socket.timeout,
    TimeoutError,
    ConnectionError,
    http.client.IncompleteRead,
    http.client.RemoteDisconnected,
)


def download_file(url: str, target: str) -> bool:
    """断点续传 + 原子写入 + **断线无限自动续传（直到完成）**。

    - 网络中断/超时：等待后从 .part 续传，**不放弃**，一直重连到下完
    - 404：该文件仓库里没有，跳过（返回 True）
    - 416：本地 .part 已是完整文件，直接转正
    - 退避：等待时间按 3,6,9... 递增，最长 30s
    """
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    tmp = target + ".part"
    is_st = target.lower().endswith(".safetensors")

    # 已存在且无 .part：仅当**完整性校验通过**才跳过；
    # 否则（旧版 bug 留下的截断文件）转成 .part 续传或删除重下。
    if os.path.isfile(target) and not os.path.isfile(tmp):
        if file_intact(target):
            return True
        print(f"   [损坏] {os.path.basename(target)} 校验失败，重新下载...")
        try:
            os.rename(target, tmp)  # 截断文件是有效前缀，可作续传起点
        except OSError:
            try:
                os.remove(target)
            except OSError:
                pass

    attempt = 0          # 连续失败次数（成功传输一次数据就清零）
    while True:
        resume = os.path.getsize(tmp) if os.path.isfile(tmp) else 0
        req = urllib.request.Request(url, headers=dict(UA))
        if resume > 0:
            req.add_header("Range", f"bytes={resume}-")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                # 服务器忽略 Range（返回 200 而非 206）→ 从头重写
                if resume > 0 and code == 200:
                    resume = 0
                mode = "ab" if resume > 0 else "wb"
                total = int(resp.headers.get("Content-Length", "0")) + resume
                done = resume
                t0 = time.time()
                last = 0.0
                with open(tmp, mode) as fp:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        fp.write(chunk)
                        done += len(chunk)
                        attempt = 0  # 有数据进来 -> 连接正常，重置失败计数
                        now = time.time()
                        if now - last >= 0.15:
                            _draw_progress(done, total, t0)
                            last = now
            # **关键**：服务器可能提前关闭连接（read 返回空但并未下完）。
            # 必须校验 done == total，否则会把残缺文件误当完整文件转正。
            if total > 0 and done < total:
                attempt += 1
                wait = min(30, 3 * attempt)
                print(
                    f"\n   [未下完] 连接提前关闭，已存 {_human(done)}/{_human(total)}，"
                    f"{wait}s 后续传 (第 {attempt} 次)..."
                )
                time.sleep(wait)
                continue  # 回到循环顶部，按 .part 当前大小用 Range 续传
            os.replace(tmp, target)
            sys.stdout.write("\r" + " " * 78 + "\r")
            sys.stdout.flush()
            # 内容级校验：若前缀本身损坏（罕见），删除整文件从头重下一次
            if is_st and not safetensors_intact(target):
                attempt += 1
                if attempt > 3:
                    print(f"   [校验失败] {os.path.basename(target)} 多次仍损坏，请删后重下。")
                    return False
                print(f"   [校验失败] {os.path.basename(target)} 内容损坏，从头重下...")
                try:
                    os.remove(target)
                except OSError:
                    pass
                continue
            return True
        except urllib.error.HTTPError as he:
            if he.code == 404:
                if os.path.isfile(tmp):
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
                return True  # 仓库里没有该文件，跳过
            if he.code == 416:  # Range 越界：本地已下完
                if os.path.isfile(tmp):
                    os.replace(tmp, target)
                return True
            attempt += 1
            wait = min(30, 3 * attempt)
            print(f"\n   [HTTP {he.code}] {wait}s 后重试 (第 {attempt} 次)...")
            time.sleep(wait)
        except _RETRIABLE as exc:
            attempt += 1
            got = os.path.getsize(tmp) if os.path.isfile(tmp) else 0
            wait = min(30, 3 * attempt)
            print(
                f"\n   [网络中断] 已存 {_human(got)}，{wait}s 后自动续传 "
                f"(第 {attempt} 次重连)... ({exc})"
            )
            time.sleep(wait)
        except KeyboardInterrupt:
            print("\n   [已暂停] 进度已保存到 .part，重跑脚本可继续。")
            raise
        except Exception as exc:  # noqa: BLE001
            # 未知异常也按可重试处理，保证"直到完成"
            attempt += 1
            wait = min(30, 3 * attempt)
            print(f"\n   [错误] {exc}；{wait}s 后重试 (第 {attempt} 次)...")
            time.sleep(wait)


def download_repo(repo: str, target_dir: str) -> bool:
    target_dir = os.path.abspath(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    print(f"\n>>> 下载仓库 [{repo}]  ->  {target_dir}")
    print("    正在获取文件清单...")
    try:
        files = list_repo_files(repo)
    except Exception as exc:  # noqa: BLE001
        print(f"[X] 获取文件清单失败：{exc}")
        print("    检查网络 / 镜像，或设 REELSAGE_MIRROR=huggingface 重试。")
        return False
    if not files:
        print("[X] 文件清单为空。")
        return False

    n = len(files)
    ok = True
    for i, rel in enumerate(files, 1):
        url = f"{BASE}/{repo}/resolve/main/{rel}"
        target = os.path.join(target_dir, rel.replace("/", os.sep))
        print(f"  [{i}/{n}] {rel}")
        if not download_file(url, target):
            ok = False
    # 完整性校验：config + 至少一个权重 + 所有 .safetensors 必须通过头部校验
    has_cfg = os.path.isfile(os.path.join(target_dir, "config.json"))
    weights = [f for f in os.listdir(target_dir) if f.endswith((".safetensors", ".bin"))]
    bad = [
        f for f in weights
        if f.endswith(".safetensors") and not safetensors_intact(os.path.join(target_dir, f))
    ]
    if ok and has_cfg and weights and not bad:
        print(f"[OK] {repo} 下载完成且校验通过：{target_dir}")
        return True
    if bad:
        print(f"[!] 以下分片仍不完整：{bad}")
    print(f"[!] {repo} 可能不完整（config:{has_cfg} 权重:{len(weights)} 损坏:{len(bad)}）。重跑本脚本可自动续传修复。")
    return False


def download_cnclip() -> bool:
    """下载 Chinese-CLIP 从 Hugging Face 官方仓库"""
    return download_repo(CNCLIP_REPO, CNCLIP_DIR)


def prepare_dirs() -> None:
    for d in ALL_DIRS:
        os.makedirs(os.path.abspath(d), exist_ok=True)


# ----------------------- 任务 -----------------------

def do_vlm(key: str) -> bool:
    repo, target = VLM_MODELS[key]
    return download_repo(repo, target)


def do_bge() -> bool:
    return download_repo(BGE_REPO, BGE_DIR)


def do_rag() -> bool:
    a = do_bge()
    b = download_cnclip()
    return a and b


def scan_all() -> bool:
    """扫描所有模型目录，报告每个文件的完整性。返回是否全部健康。"""
    targets = [
        ("Qwen3-VL 4B", VLM_MODELS["4b"][1]),
        ("Qwen3-VL 8B", VLM_MODELS["8b"][1]),
        ("BGE-M3 (文本RAG)", BGE_DIR),
        ("Chinese-CLIP (视觉RAG)", CNCLIP_DIR),
    ]
    all_ok = True
    print("=" * 60)
    print("  模型完整性扫描")
    print("=" * 60)
    for name, rel in targets:
        d = os.path.abspath(rel)
        print(f"\n=== {name}  ({rel}) ===")
        if not os.path.isdir(d) or not os.listdir(d):
            print("  [缺失] 目录为空或不存在")
            all_ok = False
            continue
        parts = [f for f in os.listdir(d) if f.endswith(".part")]
        if parts:
            print(f"  [未完成] 残留 .part: {parts}")
            all_ok = False
        sts = sorted(f for f in os.listdir(d) if f.endswith(".safetensors"))
        for f in sts:
            ok = safetensors_intact(os.path.join(d, f))
            if not ok:
                all_ok = False
            sz = os.path.getsize(os.path.join(d, f)) / (1024 * 1024)
            print(f"  [{'OK ' if ok else 'BAD'}] {sz:9.1f} MB  {f}")
        bins = [f for f in os.listdir(d) if f.endswith((".bin", ".pt"))]
        for f in bins:
            sz = os.path.getsize(os.path.join(d, f)) / (1024 * 1024)
            print(f"  [bin]  {sz:9.1f} MB  {f}  (无头部校验，仅看大小)")
    print("\n" + "=" * 60)
    print("  结果：全部健康 ✓" if all_ok else "  结果：发现缺失/损坏，运行 repair 修复")
    print("=" * 60)
    return all_ok


def repair_all() -> None:
    """只修复**已存在但损坏/不完整**的模型目录；空目录视为未安装，跳过（避免误下大模型）。"""
    print("仅修复已存在且损坏的模型（空目录请用对应下载选项手动安装）...\n")
    plan = [
        ("4b", VLM_MODELS["4b"]),
        ("8b", VLM_MODELS["8b"]),
    ]
    for key, (repo, rel) in plan:
        d = os.path.abspath(rel)
        if os.path.isdir(d) and os.listdir(d):
            print(f"\n>>> 检查/修复 {repo}")
            download_repo(repo, rel)
    for repo, rel in ((BGE_REPO, BGE_DIR), (CNCLIP_REPO, CNCLIP_DIR)):
        d = os.path.abspath(rel)
        if os.path.isdir(d) and os.listdir(d):
            print(f"\n>>> 检查/修复 {repo}")
            download_repo(repo, rel)


def run_choice(choice: str) -> None:
    c = choice.strip().lower()
    if c in ("1", "4b"):
        do_vlm("4b")
    elif c in ("2", "8b"):
        do_vlm("8b")
    elif c in ("3", "vlm"):
        do_vlm("4b"); do_vlm("8b")
    elif c in ("4", "bge"):
        do_bge()
    elif c in ("5", "clip"):
        download_cnclip()
    elif c in ("6", "all"):
        do_vlm("8b"); do_rag()
    elif c == "rag":
        do_rag()
    elif c in ("7", "scan"):
        scan_all()
    elif c in ("8", "repair"):
        repair_all()
    elif c in ("0", "q", "quit", "exit", ""):
        print("已退出。")
    else:
        print(f"无法识别的选项：{choice}")


def menu() -> str:
    print("=" * 60)
    print(f"  ReelSage 模型一键下载   镜像: {MIRROR} ({BASE})")
    print("-" * 60)
    print("  [1] Qwen3-VL 4B   (~8GB)   -> ./qwen3-vl-4b      VLM必需(二选一)")
    print("  [2] Qwen3-VL 8B   (~16GB)  -> ./qwen3-vl-8b      VLM必需(二选一,默认)")
    print("  [3] 4B + 8B 都下")
    print("  [4] 文本RAG  BGE-M3        -> ./models/embedding/bge-m3   (可选)")
    print("  [5] 视觉RAG  Chinese-CLIP  -> ./models/vision/...         (可选)")
    print("  [6] 8B + 两个RAG (全套)")
    print("  [7] 扫描完整性（不下载，只检查）")
    print("  [8] 修复已存在但损坏的模型（自动续传/重下）")
    print("  [0] 退出")
    print("=" * 60)
    return input("请选择 [1/2/3/4/5/6/7/8/0]: ")


def main() -> None:
    prepare_dirs()
    args = [a for a in sys.argv[1:] if a.strip()]
    if args:
        for a in args:
            run_choice(a)
    else:
        run_choice(menu())
    print("\n完成。模型位置已与 config_local.json 对齐，可直接启动 App。")


if __name__ == "__main__":
    main()
