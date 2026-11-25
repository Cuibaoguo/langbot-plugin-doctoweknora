"""飞书文档消息 -> 下载 -> 入 WeKnora 知识库"""

from __future__ import annotations

import base64

import httpx

from langbot_plugin.api.definition.components.runner import Runner, RunnerContext
from langbot_plugin.api.entities.builtin.platform.events import MessageReceivedEvent
from langbot_plugin.api.entities.builtin.platform.message import File


# LangBot bot UUID -> WeKnora 知识库 ID
def _parse_bot_kb_map(raw: str) -> dict:
    """解析 bot_kb_map 配置：一行一个 bot_uuid=knowledge_base_id，# 开头为注释。"""
    m = {}
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if k and v:
            m[k] = v
    return m


class DocToWeKnoraRunner(Runner):
    """监听消息中的文件段，下载后上传到 WeKnora 知识库。"""

    async def initialize(self) -> None:
        await super().initialize()

        @self.handler(MessageReceivedEvent)
        async def on_message(ctx: RunnerContext):
            await self._handle(ctx)

    async def _handle(self, ctx: RunnerContext) -> None:
        cfg = ctx.config or {}
        event = ctx.platform_event

        # 优先取处理器配置，留空则按 bot_uuid 自动匹配
        kb_id = (cfg.get("knowledge_base_id") or "").strip()
        if not kb_id:
            bot_uuid = getattr(event, "bot_uuid", "") or ""
            mapping = _parse_bot_kb_map(cfg.get("bot_kb_map"))
            kb_id = mapping.get(bot_uuid, "")
            if kb_id:
                await ctx.log(f"按 bot_uuid={bot_uuid} 匹配 kb_id={kb_id}", "debug")
            else:
                await ctx.log(
                    f"无法确定知识库：bot_uuid={bot_uuid!r}，"
                    f"knowledge_base_id 为空且 bot_kb_map 未命中（已配 {len(mapping)} 条）",
                    "warning",
                )
                return

        allowed_ext = {
            e.strip().lower().lstrip(".")
            for e in (cfg.get("allowed_ext") or "").split(",")
            if e.strip()
        }
        reply_on_success = bool(cfg.get("reply_on_success", True))

        plugin_cfg = self.get_plugin_config() or {}
        base_url = (plugin_cfg.get("weknora_base_url") or "").rstrip("/")
        api_key = plugin_cfg.get("weknora_api_key") or ""

        if not base_url or not api_key:
            await ctx.log("插件全局配置缺 weknora_base_url / weknora_api_key，跳过", "warning")
            return
        chain = getattr(event, "message_chain", None) or []
        file_seg = next((s for s in chain if isinstance(s, File)), None)
        if file_seg is None:
            return

        name = getattr(file_seg, "name", None) or "upload.bin"
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if allowed_ext and ext not in allowed_ext:
            await ctx.log(f"暂不支持该类型：.{ext}", "warning")
            return

        await ctx.log(f"收到文件 {name}（.{ext}），开始下载", "debug")

        try:
            data = await self._download(file_seg)
        except Exception as e:
            await ctx.log(f"下载失败：{e}", "error")
            return

        await ctx.log(f"下载完成，{len(data)} 字节，开始入 WeKnora", "debug")

        try:
            doc_id = await self._upload_to_weknora(base_url, api_key, kb_id, name, data)
        except Exception as e:
            await ctx.log(f"入库失败：{e}", "error")
            return

        await ctx.log(f"入库成功：{name} -> {doc_id}", "debug")

    async def _download(self, file_seg) -> bytes:
        # 1. 优先 base64（飞书适配器常见）
        b64 = getattr(file_seg, "base64", None)
        if b64:
            if isinstance(b64, (bytes, bytearray)):
                b64 = bytes(b64).decode("ascii", "ignore")
            b64 = str(b64).strip()
            # 去掉 data URI 前缀
            if b64.startswith("data:") and "," in b64:
                b64 = b64.split(",", 1)[1]
            # 去掉空白/换行
            b64 = "".join(b64.split())
            # 补齐 padding
            pad = (-len(b64)) % 4
            if pad:
                b64 += "=" * pad
            try:
                return base64.b64decode(b64, validate=False)
            except Exception as e:
                logging.getLogger(__name__).warning(
                    f"[DocToWeKnora] base64 解码失败({e})，长度={len(b64)}，前80字符={b64[:80]!r}"
                )

        # 2. bytes 直给
        raw = getattr(file_seg, "data", None)
        if isinstance(raw, (bytes, bytearray)):
            return bytes(raw)

        # 3. 完整 URL
        url = getattr(file_seg, "url", None)
        if url and str(url).startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=120) as cli:
                r = await cli.get(url)
                r.raise_for_status()
                return r.content

        raise RuntimeError("无法下载：file_seg 无 base64 / data / url 可用")

    async def _upload_to_weknora(
        self, base_url: str, api_key: str, kb_id: str, filename: str, data: bytes
    ) -> str:
        url = f"{base_url}/api/v1/knowledge-bases/{kb_id}/knowledge/file"
        headers = {"X-API-Key": api_key}
        files = {"file": (filename, data, "application/octet-stream")}
        async with httpx.AsyncClient(timeout=300) as cli:
            r = await cli.post(url, headers=headers, files=files)
            if r.status_code >= 400:
                raise RuntimeError(
                    f"WeKnora 返回 HTTP {r.status_code}: {r.text[:500]}"
                )
            payload = r.json()
        d = payload.get("data")
        if isinstance(d, dict):
            kid = d.get("id") or d.get("knowledge_id")
            if kid:
                return str(kid)
        if isinstance(d, list) and d and isinstance(d[0], dict):
            kid = d[0].get("id") or d[0].get("knowledge_id")
            if kid:
                return str(kid)
        return str(payload.get("id") or payload.get("knowledge_id") or "unknown")
