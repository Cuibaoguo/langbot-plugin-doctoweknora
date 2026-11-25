"""DocToWeKnora plugin entry point."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from langbot_plugin.api.definition.plugin import BasePlugin

logger = logging.getLogger(__name__)

_SWEEP_INTERVAL = 3600        # 每小时扫一次
_MAX_AGE_SECONDS = 3600       # 超过 1 小时的临时文件删掉
_SWEEP_DIRS = ("/tmp", "/app/data/temp", "/app/temp")
_TMP_PATTERNS = ("lark_file_", "file_", "upload_", "tmp_")


class DocToWeKnoraPlugin(BasePlugin):
    """文件消息入库 WeKnora"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sweeper_task = None

    async def initialize(self) -> None:
        if self._sweeper_task is None or self._sweeper_task.done():
            self._sweeper_task = asyncio.create_task(self._sweep_loop())
            logger.info("[DocToWeKnora] 临时文件清理任务已启动")

    async def terminate(self) -> None:
        t = self._sweeper_task
        if t and not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._sweeper_task = None

    async def _sweep_loop(self) -> None:
        while True:
            try:
                self._sweep_once()
            except Exception as e:
                logger.warning(f"[DocToWeKnora] 清理异常：{e}")
            await asyncio.sleep(_SWEEP_INTERVAL)

    @staticmethod
    def _sweep_once() -> None:
        now = time.time()
        removed = 0
        for d in _SWEEP_DIRS:
            try:
                names = os.listdir(d)
            except OSError:
                continue
            for n in names:
                if not any(n.startswith(pat) for pat in _TMP_PATTERNS):
                    continue
                p = os.path.join(d, n)
                try:
                    if now - os.path.getmtime(p) > _MAX_AGE_SECONDS:
                        os.remove(p)
                        removed += 1
                except OSError:
                    pass
        if removed:
            logger.info(f"[DocToWeKnora] 清理过期临时文件 {removed} 个")
