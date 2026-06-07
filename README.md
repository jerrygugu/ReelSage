# ReelSage v2.0 — 本地实时视频理解工具

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.11-green.svg)

**🎬 基于 Qwen3-VL 的本地视频理解工具 | 智能分镜 | 场景总结**

</div>

---

> **版权所有 © 2026 Kimi (GitHub: jerrygugu)。保留所有权利。**
> 
> 本软件为**专有软件**，禁止逆向、破解、再分发与未授权商用，详见 [LICENSE](./LICENSE)。
>
> 💬 **技术支持 QQ 群：318982155 

---

## 快速开始（三步）

> **环境要求**：
> - Windows 10/11
> - NVIDIA GPU（推荐 16GB+ 显存用于 8B 模型，8GB+ 可用 4B 模型）
> - **必须安装 Python 3.11.x**（ReelSage.exe 依赖 Python 3.11 环境）

```bat
:: 1) 下载本仓库
::    点击 Code → Download ZIP 解压，或使用 git clone

:: 2) 复制配置模板
copy config_local.example.json config_local.json

:: 3) 安装运行环境（自动创建虚拟环境并安装依赖）
安装依赖.bat

:: 4) 下载模型（可选择 4B 或 8B 规格）
download_models.bat
```

**完成后直接双击 `ReelSage.exe` 启动！**

---

## 主要文件说明

| 文件 | 作用 |
|---|---|
| **ReelSage.exe** | 主程序，双击启动 |
| `安装依赖.bat` | 自动安装 Python 依赖和 PyTorch（CUDA 12.4） |
| `download_models.bat` | 下载 Qwen3-VL 模型（支持断点续传） |
| `config_local.example.json` | 配置模板文件 |

> **注意**：模型文件（`models/`）和虚拟环境（`.venv/`）体积较大，不包含在仓库中，需通过脚本下载生成。

---

## 核心功能

| 功能 | 说明 |
|---|---|
| **视频分析** | 本地视频文件解析，实时抽帧分析 |
| **AI 推理** | 使用 Qwen3-VL（4B/8B）进行视觉理解 |
| **智能分镜** | 自动检测场景切换，生成分镜记录 |
| **角色识别** | 视觉记忆 + 角色登记表 |
| **场景总结** | 分层总结：镜头 → 场景 → 幕 → 全片 |
| **多格式导出** | 支持 Markdown、TXT、JSON、HTML 及关键帧拼图 |
| **主题切换** | 亮色/暗色主题实时切换 |
| **断点续跑** | 分析中断后可继续处理 |

---

## 使用方式

### 启动程序

```bat
# 方式 1：直接双击
ReelSage.exe

# 方式 2：命令行（如需调试）
python ReelSage.py
```

### 基本操作流程

1. **选择视频**：点击「打开视频」按钮
2. **配置参数**：
   - 选择模型规格（4B/8B）
   - 调整采样间隔
   - 设置输出格式
3. **开始分析**：点击「开始分析」
4. **查看结果**：
   - 实时查看分镜墙
   - 导出分析报告
   - 保存关键帧

---

## 模型下载

ReelSage 使用以下 AI 模型：

- **Qwen3-VL (4B/8B)**：视觉语言模型，用于理解视频内容
- **BGE-M3**：文本向量模型
- **Chinese-CLIP**：视觉向量模型

运行 `download_models.bat` 会弹出交互式菜单：
1. 选择模型规格（4B 或 8B）
2. 选择下载源（hf-mirror 镜像 / ModelScope / 官方）
3. 自动下载并配置

下载完成后会自动更新 `config_local.json`，无需手动配置。

---

## 多帧打包技术

ReelSage v2.0 支持**多帧联合推理**，提升长视频时序理解能力：

- 单帧模式：每次只分析一张图片
- 多帧模式：将同一镜头内的多个时间点帧合并推理，AI 能看到动作连贯性

配置文件 `config_local.json`：

```jsonc
"多帧打包": {
    "启用": true,
    "每次推理帧数": 0,  // 0 表示根据显存自动调整
    "镜头内偏移秒": [-0.6, -0.3, 0.0, 0.3]
}
```

**自动适配规则**：

| 显存大小 | 推理帧数 | 推荐模型 |
|---|---|---|
| 24 GB+ | 4 帧 | 8B |
| 16-23 GB | 2 帧 | 8B |
| 12-15 GB | 2 帧 | 4B |
| 8-11 GB | 1 帧 | 4B |
| < 8 GB | 1 帧 | 4B (CPU) |

---

## 目录结构

```
ReelSage/
├─ ReelSage.exe              # 主程序
├─ config_local.json         # 配置文件（需复制模板生成）
├─ requirements_local.txt    # Python 依赖列表
├─ 安装依赖.bat               # 环境安装脚本
├─ download_models.bat       # 模型下载脚本
│
├─ .venv/                    # Python 虚拟环境（脚本自动创建）
├─ models/                   # AI 模型文件（脚本自动下载）
│  ├─ Qwen/                  # Qwen3-VL 模型
│  ├─ embedding/             # BGE-M3 文本向量
│  └─ vision/                # Chinese-CLIP 视觉向量
│
├─ output/                   # 分析结果输出目录
│  ├─ 实时记录/
│  ├─ 分镜/
│  └─ 总结/
│
└─ logs/                     # 运行日志
```

---

## 常见问题

### 1. 提示找不到 Python 3.11？

确保已安装 Python 3.11.x：
- 官方下载：https://www.python.org/downloads/
- 安装时勾选 "Add Python to PATH"

### 2. CUDA 相关错误？

确保已安装 NVIDIA 显卡驱动：
- 下载地址：https://www.nvidia.com/Download/index.aspx
- 推荐驱动版本：545.xx 或更新

### 3. 显存不足怎么办？

在界面中选择 **4B 模型**，或调整配置：
```jsonc
"多帧打包": {
    "启用": false,  // 关闭多帧打包节省显存
    "每次推理帧数": 1
}
```

### 4. 模型下载慢？

使用国内镜像源：
- hf-mirror：国内速度快（推荐）
- ModelScope：阿里云托管

### 5. 如何断点续跑？

重新打开同一视频，程序会自动检测到之前的进度并询问是否继续。

---

## 技术支持

- **QQ 群**：318982155（使用交流、问题反馈）

---

## 开源许可

本软件为**专有软件**，版权归作者所有。

- ✅ 允许：个人学习和非商业使用
- ❌ 禁止：逆向工程、破解、再分发、未授权商业使用

详见 [LICENSE](./LICENSE) 文件。

---

## 版本信息

- **当前版本**：v2.0.0
- **发布日期**：2026 年
- **版权所有**：© Kimi (jerrygugu)

---

**感谢使用 ReelSage！** 🎬
