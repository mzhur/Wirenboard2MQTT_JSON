import asyncio
class WB_MAP6S():
    def __init__(self, loop, client, address) -> None:
        self.loop = loop
        self.client = client
        self.address = address
        if self.loop.is_running():
            asyncio.create_task(self.sync())
        else:
            self.loop.run_until_complete(self.sync())
    async def chanel_update(self, chanel):
        pass