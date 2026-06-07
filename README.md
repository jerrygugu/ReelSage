# ReelSage v2.0 — 商业级本地实时视频理解 + 云授权管理

> **版权所有 © 2026 Kimi (GitHub: jerrygugu)。保留所有权利。**
> 本仓库分发 **ReelSage.exe**（可执行程序 + 运行库 + 安装脚本）；核心源码
> （授权校验 / 一机一码等）已编译进 exe，**不随仓库提供**。
> 本软件为**专有软件**，禁止逆向、破解、再分发与未授权商用，详见 [LICENSE](./LICENSE)（EULA）。
>
> 本地 VLM 实时视频理解工具，需联网授权使用。
>
> 💬 **使用 / 授权码 / 商业合作 / 技术支持 QQ 群：318982155**

---

## 快速开始（三步，下载后即可用）

> 环境要求：**Windows 10/11 + NVIDIA GPU + 必须安装 Python 3.11.x**
> （`ReelSage.exe` 用 Python 3.11 编译，依赖环境必须同为 3.11，否则模型加载失败）
> 8B 模型约需 16GB 显存，显存不足请在界面里选 4B。

```bat
:: 0) 下载本仓库（Code → Download ZIP 解压，或 git clone）

:: 1) 复制配置模板
copy config_local.example.json config_local.json

:: 2) 安装运行环境（自动建 .venv + 装 CUDA12.4 版 PyTorch 及依赖；要求 Python 3.11）
安装依赖.bat

:: 3) 下载模型（交互菜单：选 8B 或 4B；RAG 可选，可跳过）
download_models.bat
```

完成后 **直接双击 `ReelSage.exe` 启动**（无需任何脚本、无黑窗）。

| 文件 / 脚本 | 作用 |
|---|---|
| **`ReelSage.exe`** | 主程序（核心逻辑已编译加固，双击即用） |
| `安装依赖.bat` | 创建 `.venv`，安装 Python 3.11 的 CUDA 12.4 版 PyTorch + 依赖 |
| `download_models.bat` | 从 hf-mirror 镜像下载 Qwen3-VL（4B/8B）/ BGE-M3 / Chinese-CLIP，断点续传 |
| `config_local.example.json` | 配置模板，复制为 `config_local.json` 使用 |

> - `.venv`、`models/` 体积巨大，**不在仓库内**，由上面脚本本地生成/下载。
> - 本软件需**联网授权**：首次使用需用授权码/账号登录（联系 QQ 群 318982155）。
> - 源码（含一机一码 / 授权逻辑）已编译进 `ReelSage.exe`，仓库内不含 `.py` 源码。

---

## 全景架构

```
┌────────────────────────────────────────────────────────────┐
│            客户端 (Windows EXE，可混淆打包)                 │
│  ────────────────────────────────────────────────────────  │
│   UI (Tkinter, 暗/亮主题, 分镜墙, 角色面板, 事件/对白)      │
│        │                                                    │
│        ▼                                                    │
│   Analyzer  ──┬── ShotDetector ──── VisualMemory             │
│               ├── CharacterRegistry                         │
│               ├── Summarizer (shot→scene→act→final)         │
│               ├── Quality + Retry                           │
│               └── MetricsHub                                │
│        │                                                    │
│        ▼                                                    │
│   VLM Engine (Qwen3-VL 4B/8B, 本地 GPU)                     │
│                                                             │
│   Licensing (Fernet 加密本地凭据 + 心跳 + 设备指纹)         │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / 一机一码
                               ▼
┌────────────────────────────────────────────────────────────┐
│            云授权服务端 (FastAPI + SQLAlchemy)              │
│  ────────────────────────────────────────────────────────  │
│   /api/v1/activate · /heartbeat · /deactivate (客户端)      │
│   /api/v1/admin/login · customers · licenses · devices ·   │
│   audit · stats (管理后台 API)                              │
│  ────────────────────────────────────────────────────────  │
│   Web 控制台 (静态 SPA, 暗/亮主题, 全部 CRUD)               │
│   bcrypt + JWT + 审计日志                                   │
└────────────────────────────────────────────────────────────┘
```

---

## 客户端能力（cinescribe/）

| 维度 | 实现 |
|---|---|
| 视频源 | OpenCV 直接打开本地视频，按时间戳同步抽帧 |
| 推理 | 本地 Qwen3-VL 4B / 8B，bfloat16 + device_map=auto |
| 实时性 | 解码 / 推理 / UI 三线程解耦，UI 永不卡 |
| 智能采样 | 黑屏跳过 / 场景切换 / 字幕差异 / 文本去重 / 自适应采样 |
| **分镜检测** | 在线 multi-strategy（直方图 + 边缘 + 自适应阈值），每镜头自动选关键帧 |
| **视觉记忆 + 角色** | 文本聚类的角色登记表 + 历史镜头摘要，shot-aware prompt |
| **分层总结** | shot → scene → act → final，结构化事件 / 对白抽取 |
| **质量校验** | VLM 空 / 拒答 / 乱码 / 重复自动重试，全链路指标采集 |
| **三种产物分别导出** | 实时记录 / 分镜 / 总结 任意组合；MD / TXT / JSON / HTML / 关键帧拼图 |
| **主题** | 白天 / 黑夜热切换 |
| **模型下载** | UI 内一键下载 Qwen3-VL（hf-mirror / ModelScope / 官方）|
| **断点续跑** | 启动自动检测 + 询问 |
| **授权** | 一机一码激活 / 心跳 / 离线宽限期 / 服务端实时吊销 |

启动：
```bash
# 安装依赖
pip install -r requirements_local.txt

# 启动
python ReelSage.py
# 或
启动_ReelSage.bat
```

首次启动会要求输入授权码（管理员在控制台「授权」里签发）。

---

## 云授权后端（server/）

完整 FastAPI 应用 + Vanilla JS 控制台，**零构建依赖**，单机即可部署。

启动：
```bash
cd server
启动_服务端.bat
# 或：pip install -r requirements.txt && uvicorn app.main:app --port 8000
```

访问：
- 控制台： http://127.0.0.1:8000/
- OpenAPI： http://127.0.0.1:8000/docs
- 默认账号： **admin / admin**（首次登录请立即改密码）

完整文档： [server/README.md](server/README.md)

---

## 工业级加固打包（二进制不可反编译）

双击 `打包客户端.bat` 选择模式：

| 模式 | 工具 | 产物 | 安全等级 |
|---|---|---|---|
| **Nuitka 二进制**（推荐） | Nuitka + C 编译器 | `dist_nuitka/ReelSage.exe` 单文件 | ★★★★★ 核心代码翻译为 C → 原生机器码，无 `.pyc`，反编译需逆向工程 |
| PyArmor 混淆（快速） | PyArmor + PyInstaller | `dist/ReelSage/` | ★★★ 字节码加密 |

命令行：
```bash
python build_exe.py --mode=nuitka     # 推荐，10–30 分钟
python build_exe.py --mode=pyarmor    # 兜底，1–3 分钟
python build_exe.py --clean           # 清理
```

> **首次使用 Nuitka** 需要本机有 C 编译器（Windows: VS Build Tools / MSYS2 GCC）。
> Nuitka 会在首次运行时自动下载 MingW64，按提示输入 Yes 即可。

---

## 目录结构

```
F:\ReelSage\
├─ ReelSage.py                # 客户端入口
├─ config_local.json          # 客户端配置
├─ requirements_local.txt     # 客户端依赖
├─ build_exe.py               # 混淆 + 打包脚本
├─ 打包客户端.bat
├─ 启动_ReelSage.bat
│
├─ cinescribe/                # 客户端核心包
│  ├─ analyzer.py             # 分析主流程
│  ├─ shots.py                # 分镜检测
│  ├─ memory.py               # 视觉记忆 + 角色登记
│  ├─ summarizer.py           # 分层总结
│  ├─ exporter.py             # 多格式导出
│  ├─ intelligence.py         # 智能采样 + checkpoint
│  ├─ quality.py              # VLM 输出校验
│  ├─ metrics.py              # 性能指标
│  ├─ vlm_engine.py           # Qwen3-VL 推理引擎
│  ├─ video_source.py         # OpenCV 视频源
│  ├─ model_downloader.py     # 模型下载（hf-mirror/ModelScope）
│  ├─ branding.py             # logo / 版权
│  ├─ theme.py                # 主题（暗/亮）
│  ├─ licensing.py            # 一机一码 / 心跳
│  ├─ ui_app.py               # 主 UI
│  ├─ ui_activation.py        # 激活对话框
│  ├─ ui_downloader.py        # 模型下载 UI
│  └─ ...
│
└─ server/                    # 云授权后端
   ├─ requirements.txt
   ├─ run.py
   ├─ 启动_服务端.bat
   ├─ README.md
   ├─ app/
   │  ├─ main.py              # FastAPI 入口
   │  ├─ config.py            # 配置 (环境变量驱动)
   │  ├─ database.py          # SQLAlchemy 引擎
   │  ├─ models.py            # ORM (Customer/License/Device/...)
   │  ├─ schemas.py           # Pydantic 模型
   │  ├─ security.py          # bcrypt + JWT + 授权码生成
   │  ├─ deps.py              # 依赖注入
   │  └─ api/
   │     ├─ client_api.py     # 客户端 API
   │     └─ admin_api.py      # 管理后台 API
   └─ static/                 # 控制台 SPA
      ├─ index.html
      ├─ css/style.css
      └─ js/app.js
```

---

## 模型下载（仅 VLM）

菜单「模型 → 模型下载中心」用于下载 **Qwen3-VL / Qwen2.5-VL** 等视觉语言模型。

**文本向量（BGE-M3）与视觉向量（Chinese-CLIP）已随项目内置**在 `models/embedding/`、`models/vision/`，无需在下载中心单独下载；路径见 `config_local.json` → `向量检索`。

1. 打开「模型下载中心」
2. 选择 VLM 规格与镜像源 → 下载
3. 完成后自动写回 `config_local.json` → 立即可用

---

## 多帧打包（长视频时序理解的关键）

旧架构每次只送 1 张图给 VLM，长视频里"动作连贯性"很差。ReelSage v2 改成：

> 同一镜头内**当前帧 + 最近 N-1 张缩略图**一次推理 → VLM 看到时序

`config_local.json`：

```jsonc
"多帧打包": {
    "启用": true,
    "每次推理帧数": 0,          // 0 = 按显存自适应
    "镜头内偏移秒": [-0.6, -0.3, 0.0, 0.3]
}
```

自适应规则：

| 显存 | 帧数/次 | VLM | 辅助模型 |
|---|---|---|---|
| 24 GB+ | 4 帧 | 8B | 全开 |
| 16-23 GB | 2 帧 | 8B | 全开 |
| 12-15 GB | 2 帧 | 4B | 全开 |
| 8-11 GB | 1 帧 | 4B | 关闭 |
| < 8 GB | 1 帧 | 4B/CPU | 关闭 |

---

## 部署最佳实践

1. **服务端**：放公网，Nginx/Caddy 反代 8000 + HTTPS（强烈建议）。
2. **客户端**：把 `config_local.json` 的 `授权 → 服务端地址` 改成你的公网地址，再用 `打包客户端.bat` 出 EXE。
3. **生成授权码**：控制台 → 客户 → 新建；授权 → 签发 → 把生成的授权码（形如 `A3K9-FQ2X-7TPM-WD8H-J5RN`）发给客户。
4. **回收/吊销**：控制台 → 设备 → 吊销，**最长 5 分钟**（一次心跳）后客户端失效。

### 生产部署安全清单（必读）

| 项 | 处理方式 |
|---|---|
| **服务端密钥** | 设置环境变量 `REELSAGE_SECRET_KEY=<64 位随机字符串>`；不设也会自动落盘到 `server/.secret_key`（chmod 600），但仍推荐放 Vault / docker secret |
| **初始管理员密码** | 首次启动会在控制台打印一次随机强密码（不写日志）。立即记录并登录后强制改密 |
| **错误详情泄露** | `REELSAGE_EXPOSE_ERROR_DETAIL=false`（默认）。调试时才设 true |
| **限流参数** | `REELSAGE_RATE_LIMIT_LOGIN=10/minute`、`REELSAGE_RATE_LIMIT_ACTIVATE=20/minute`（可调） |
| **管理后台 IP 白名单** | `REELSAGE_ADMIN_IP_WHITELIST=["1.2.3.4","5.6.7.0/24"]`（强烈推荐） |
| **CORS** | `REELSAGE_CORS_ORIGINS=[]`（默认空，仅同源；如前后端分离才填白名单） |
| **构建签名密钥** | 打包机器设置 `REELSAGE_BUILD_SECRET=<32 位以上随机字符串>`；服务端同名变量。两边一致才能识别正版 |
| **心跳间隔** | 客户端 `config_local.json → 授权 → 心跳间隔秒`：默认 60 秒（吊销最快 1 分钟生效）。要求秒级吊销可调到 15-30 秒（流量增加） |
| **HTTPS** | 服务端反代必须 HTTPS；客户端在 `config_local.json` 的 `服务端地址` 用 `https://` |

### 设备指纹兼容性

- Windows 11 24H2 / Server 2025 默认已卸载 `wmic`，本项目自动改为：
  1. SMBIOS 固件表（`GetSystemFirmwareTable('RSMB')`，ctypes 直读）
  2. PowerShell `Get-CimInstance`
  3. wmic（仅在老系统上兜底）
- Linux 用 `/sys/class/dmi/`；macOS 用 `system_profiler` / `sysctl`。

---

## 套餐价格

| 套餐 | 时长 | 价格 | 说明 |
|---|---|---|---|
| 免费试用 | 7 天 | ¥0 | 完整功能体验，到期自动关闭 |
| 月卡 | 30 天 | **¥29** | 一机绑定 · 联系客服开通 |
| **年卡（推荐）** | 365 天 | **¥59** | 含云端升级权益 |
| **永久 VIP** | 终身 | **¥99** | 终身使用 · 终身免费大版本升级 |

> **功能咨询 / 授权开通 / 续费升级 / 技术支持**：客服 QQ **1513712845**
> 服务端「授权」页面提供「试用 / 月卡 / 年卡 / 永久 VIP」一键预设按钮。

---

## 在线升级（云端发版 → 客户端自动覆盖）

1. 管理员在控制台「版本发布」页 → 新建版本
   - 填版本号、下载直链、SHA256 校验值（强烈建议）
   - 勾选「force_update」即可强制所有旧客户端升级
2. 客户端启动后 1.5 秒静默检测；用户也可在「关于我们」页手动点「立即检测更新」
3. 弹窗 → 下载 → SHA256 校验 → `update.bat` 接管 → 覆盖 → 重启

强制更新模式：弹窗只有「立即更新」和「退出程序」两个选项，无法跳过。

---

## 中文安装包

```bash
打包安装包.bat
```
（需预装 Inno Setup 6+；产物在 `installer/output/ReelSage_Setup_2.0.0.exe`）

特性：
- 简体中文向导
- 桌面快捷方式 / 开始菜单 / 卸载入口
- EULA 许可协议（中文）
- 卸载时自动清理 `__pycache__` 和 `logs`

---

## 版本

- 客户端：**v2.0.0**
- 服务端：**v2.0.0**
- 版权：**© Kimi · All Rights Reserved**
- 客服 QQ：**1513712845**
