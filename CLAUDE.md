# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 仓库性质

这不是一个可构建的应用，而是 **Agent Skill + 云端运维脚本 + 视频/LLM 工作流包** 的集合：本地 Mac 上的 Agent 通过 `google-colab-cli`（`~/.local/bin/colab`）/ `colab-mcp` / `colabllm` 遥控 Google Colab GPU（主力 G4 96GB Blackwell，10.05 CCU/h）和 Google Drive 云盘。

- 没有 build / lint / test 体系，也没有 `pyproject.toml` / `requirements.txt`。改完脚本的最低验证是 `python3 -m py_compile <file>` 或 `bash -n <file>.sh`；真正的验证要上云跑，**会花 CCU，先问用户**。`./scripts/deepseek_g4/fast_start_g4.sh status` 只读查询 CCU 余额，不开机，可以拿来冒烟测试本地 colab-cli 环境。
- 文档、注释、commit message 以中文为主，commit 用 conventional 前缀（`feat(deepseek-g4): …`、`docs(ep3): …`）。
- `.gitignore` 的口径：输入素材（`sample_inputs/`、BGM `tracks/`、剧集 `refs/`/`cover/`、付费 API 产出的 `work/*.json` 和 `suno_v*.mp3`）要提交；可以重新渲染的（`outputs/`、`clips/`、`final/`、`preview/`、`work/` 下的中间媒体）不提交。
- 路径不要写死 home 目录：本地工具用 `Path.home()` / `$HOME`，仓库内文件用 `Path(__file__).resolve()` 推算。可选的外部目录用环境变量，参考 `run_cloud_tts_remote.py` 的 `TTS_TAKES_DIR` / `TTS_ARTIFACT_DIR`。

## 两份 Skill 定义（容易改错）

- 根目录 `SKILL.md` 是**权威版本**（含 §6 colabllm 协同、`ista-coder-iq2xxs` 方案）。
- `skills/colab-ultra-workstation/` 是给外部安装用的标准 Skill 目录镜像（`SKILL.md` + `scripts/` + `references/` + `templates/`），内容是根目录的完整拷贝。**只改根目录，改完再同步到镜像**，不要直接改镜像：
  ```bash
  R=/Volumes/WorkData/Workspace/projects/colab-ultra-workstation; M=$R/skills/colab-ultra-workstation
  cp $R/SKILL.md $M/; for d in scripts references templates; do rsync -a --exclude __pycache__ --exclude .DS_Store $R/$d/ $M/$d/; done
  for d in scripts references templates; do diff -rq -x __pycache__ -x .DS_Store $R/$d $M/$d; done   # 无输出 = 已同步
  ```
- `SKILL.md` 用 progressive disclosure：主文件只放选卡矩阵和 SOP，领域细节放在 `references/*.md`，按任务需要再读（DeepSeek → `deepseek_v41_748b_g4_guide.md`；MiniMax-H3 → 先读 `minimax_h3_zero_waste_sop.md` 里的铁律 A~G）。

## 防烧钱硬规则（所有云端操作）

1. **计费包裹**：开 GPU 前先跑 `python3 scripts/colab_meter.py start -s <session> -g <G4|L4|T4|A100|H100>`，结束后跑 `python3 scripts/colab_meter.py stop -s <session>`（只释放这个会话；`--all` 会强杀全部会话；还有 `report` 子命令）。释放之后按 `SKILL.md` §4 的格式输出「算力释放与计费核验报告」。`colabllm <service> up/down` 也要用同名会话套上 meter。
2. **下载走 CPU**：从 HuggingFace 拉大模型、整理云盘一律用 `colab new -s <s>`（CPU，0 CCU/h），不要在 G4/H100 上首次下载。
3. **不在 FUSE 路径上 mmap 大模型**：`/content/drive` 随机读只有约 25 MB/s，还有 112 GiB 缓存墙。权重要通过 Drive v3 API 并发拉取或 HF CDN 落到本地 NVMe `/content/fast_*`（见 `scripts/launch_g4_comfyui_fast.py`、`scripts/deepseek_g4/step3_*.py`）。
4. **长任务脱机**：超过 15 秒的远程任务用 `nohup … > /tmp/x.log 2>&1 &` 后台跑，本地用 `perl -e 'alarm N; exec @ARGV' colab exec …` 带超时轮询，防止 WebSocket 断开后卡死。
5. **销毁实例前**先用 Drive API 确认产物在云端 `size > 0`。
6. 本地能做的（提示词、配置、首帧素材、口型对齐、字幕、合成）都在本地做完，再开 GPU。

## 架构：本地遥控器 + 云端执行器

`workflows/NN_<场景>/` 下每个场景都是独立包，参数互不影响，结构相同：

- `*_remote.py`（本地运行）：通过 `~/.local/share/uv/tools/google-colab-cli/bin/python` 重新执行自己（`os.execv`），以便 `import colab_cli`；然后按 OAuth 检查 → `colab_meter start` → `colab new --gpu G4` → `colab dfs mount` → 把脚本和素材分块 base64 传到云端 `/tmp/` → `colab exec -f` nohup 拉起 → 轮询 → 拉回 MP4 → `colab_meter stop` 的顺序执行。
- `run_*.py`（云端运行）：把 ComfyUI API 格式的 workflow JSON（`workflow_*.json`）加载进来，按 `*_config.json` 动态改写节点（扫描 `LoadImage`/`LoadAudio`、换角色图/声纹/台词/风格），提交给 `127.0.0.1:8188`。分段信息（节点 ID 区间）硬编码在 `get_default_seg_meta()` 一类函数里，**改 workflow JSON 的节点编号时要一起改这里**。
- 分段生成会把每段约 5MB 的 `AV_LATENT` 存到 Drive，所以 `--only-seg N` / `--start-seg` / `--end-seg` 可以单独重修某一段，不必全量重跑。
- 云端固定路径：`/content/drive/MyDrive/AI_Workstation/ComfyUI`（Drive 上的持久副本）、`/content/ComfyUI`（本地运行副本）。脚本会自动补建 `My Drive → MyDrive` 软链接。
- `workflows/05_ancient_rap_battle/` 不一样：以本地流水线为主（`scripts/` 下 analyze_song → kie_suno → make_clips → h3_colab_runner → align_and_lipsync → assemble → package），按剧集目录 `episodes/<name>/` 组织，云端只负责 H3 出片。完整 SOP 和本地 venv（`/tmp/lipsync_venv`）用法见它的 `README.md`。

## DeepSeek-V4.1 748B on G4（`scripts/deepseek_g4/`）

四步流水线：`step1_cpu_download_to_drive.py`（CPU 免费落盘）→ `step2_g4_build_engines.sh`（首次编译 sm_120a 引擎并打包）→ `step3_g4_hybrid_stage_and_benchmark.py`（并发拉取 + 显存/内存三级锁定 + OpenAI 兼容网关，支持 `--auth-caddy`、`--tunnel`）→ `run_pelican_benchmark.py`。

```bash
./scripts/deepseek_g4/fast_start_g4.sh {start|switch|status|stop} [--variant ista-coder-iq2xxs|unsloth-ud-iq2xxs|abiray-gsq-iq2xxs] [--quality-mode exact|turbo] [--auth-caddy] [--tunnel quick|named]
```

变体怎么选、Engram 置零引起的拼写缺陷，见 `references/deepseek_v41_748b_g4_guide.md`。注意：`fast_start_g4.sh` 的 start/switch 只**打印**云端要执行的 step3 命令，并不自己执行。

## 本机环境前提

`colab`（google-colab-cli，用 `uv tool install --with socksio` 安装）、`colab-dfs-ext`（零浏览器挂载 Drive，`COLAB_DFS_DEFAULT=1`）、`colabllm`；本地代理是 `127.0.0.1:7890`，OAuth 时要设 `no_proxy="localhost,127.0.0.1"`。Drive 授权报 `403 ACCESS_TOKEN_SCOPE_INSUFFICIENT`，通常是授权页里 Drive 复选框没勾，重签方法见 `SKILL.md` §3。
