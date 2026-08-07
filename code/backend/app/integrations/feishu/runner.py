from lark_oapi.channel import Events, FeishuChannel

from app.core.config import settings
from app.integrations.feishu.handler import FeishuSecurityHandler


def build_channel() -> FeishuChannel:
    if not settings.FEISHU_APP_ID or not settings.FEISHU_APP_SECRET:
        raise RuntimeError("缺少 FEISHU_APP_ID / FEISHU_APP_SECRET")
    channel = FeishuChannel(
        app_id=settings.FEISHU_APP_ID,
        app_secret=settings.FEISHU_APP_SECRET,
        transport="websocket",
    )
    handler = FeishuSecurityHandler(channel, settings.FEISHU_FIREWALL_TARGET_CODE)
    channel.on(Events.MESSAGE, handler.on_message)
    channel.on(Events.CARD_ACTION, handler.on_card_action)
    return channel


def main() -> None:
    build_channel().start()


if __name__ == "__main__":
    main()
