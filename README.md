# DocToWeKnora

LangBot 插件：收到文件消息后自动下载并入库到 [WeKnora](https://github.com/Tencent/WeKnora) 知识库。

## 功能

- 监听 `message.received` 事件，自动提取文件附件
- 兼容 `base64` / `bytes` / `path` / `url` 四种 `file_seg` 形态
- 通过 WeKnora OpenAPI v1 上传（`X-API-Key` 鉴权）
- 支持按机器人 UUID 自动匹配知识库，或手动指定 `knowledge_base_id`
- 处理完自动清理临时文件，另有每小时兜底清扫

## 安装

1. 下载 `pc-DocToWeKnora-x.y.z.lbpkg`
2. LangBot 插件页 → 上传插件 → 选择 lbpkg
3. 填写配置（见下）

## 与 WeKnora Agent 配合使用

本插件只负责「把文件送进 WeKnora 知识库」，不负责问答。
推荐搭配 LangBot 官方 **WeKnora Agent** 运行器一起用，形成「发文件入库 → 提问检索回答」闭环：

1. 在流水线里把 Runner 选为 `WeKnora Agent`，填好 `API Base URL`、API Key、`knowledge-base-ids`
2. 本插件作为事件监听器挂在同一条流水线上，配置同一个知识库 ID
3. 用户发文件 → 本插件入库 → 用户提问 → WeKnora Agent 检索回答

两者共用同一套 WeKnora 凭证和知识库 ID，不需要重复部署。
若只装本插件不装 WeKnora Agent，文件能入库但机器人不会自动检索回答，需自行在别处调用 WeKnora 问答。

### ⚠️ 两个插件的 URL 写法不同，别抄混

| 插件 | 配置项 | 写法 | 说明 |
|---|---|---|---|
| **本插件** DocToWeKnora | `weknora_base_url` | `http://WeKnora-app:8080` | **不带** `/api/v1`，插件内部自己拼 `/api/v1/knowledge-bases/...` |
| **WeKnora Agent** 运行器 | `API Base URL` | `http://WeKnora-app:8080/api/v1` | **带** `/api/v1`，官方运行器要求末尾含 `/api/v1` |

写错这个是「装了不工作」最常见的原因。

## 配置

| 配置项 | 必填 | 说明 |
|---|---|---|
| `weknora_base_url` | ✅ | WeKnora 服务地址，如 `http://WeKnora-app:8080` |
| `weknora_api_key` | ✅ | WeKnora API Key（后台「空间完全访问」类型） |
| `knowledge_base_id` | ❌ | 指定知识库 ID；留空则按机器人 UUID 自动匹配 |
| `allowed_ext` | ❌ | 允许的扩展名，逗号分隔；留空表示全部放行 |
| `bot_kb_map` | ❌ | 多机器人映射，一行一个 `bot_uuid=knowledge_base_id`；`knowledge_base_id` 留空时生效 |

### 多机器人场景

一个 LangBot 挂多个机器人、各自入库不同知识库时，**不要填 `knowledge_base_id`**，改用 `bot_kb_map`：
匹配规则：

1. `knowledge_base_id` 填了 → 直接用它（单机器人场景最简单）
2. 没填 → 用当前消息的 `bot_uuid` 查 `bot_kb_map`
3. 都未命中 → 插件记 warning 并跳过，不会误传

**怎么找 bot_uuid**：LangBot 机器人配置页 URL 里，形如 `/bots/<uuid>`；或数据库 `bots` 表 `uuid` 列。

### 推荐 `allowed_ext`
## 格式支持

插件本身不限制格式，实际解析能力取决于 WeKnora 后端引擎：

| 引擎 | 支持格式 |
|---|---|
| MinerU | `.pdf` `.jpg` `.jpeg` `.png` `.bmp` `.tiff` `.doc` `.docx` `.ppt` `.pptx` |
| anydoc | `.docx` `.doc` `.pptx` `.ppt` `.xlsx` `.xls` `.epub` `.docm` `.odp` `.ods` `.odt` `.pptm` `.rtf` `.xlsm` |
| 内置 | `.mhtml` `.htm` `.html` `.md` `.markdown` `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.tiff` `.webp` |
| Simple | `.csv` `.txt` `.json` `.mp3` `.wav` `.m4a` `.flac` `.ogg` |

## 环境要求

- LangBot（含 `langbot_plugin_runtime`）
- WeKnora 后端，OpenAPI v1 可用
- 插件与 WeKnora 需网络互通（同 Docker 网络即可）

## 已知限制

- 飞书单文件上传上限 10MB（平台限制，非插件限制）
- 扫描版 PDF 需 WeKnora 开启 OCR 才能检索内容
- `.mobi` 不在 WeKnora 支持列表，建议先转 PDF

## License

MIT
