"""DocToWeKnora plugin entry point."""

from __future__ import annotations

from langbot_plugin.api.definition.plugin import BasePlugin


class DocToWeKnoraPlugin(BasePlugin):
    """文件消息入库 WeKnora"""

    async def initialize(self) -> None:
        # 不在共享运行时里做全局临时文件清理，避免误删其他插件/工作区的文件。
        pass

    async def terminate(self) -> None:
        pass
