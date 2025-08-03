from channels.generic.websocket import AsyncJsonWebsocketConsumer

class LogConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.group_name = f"logs_{self.task_id}"
        # 加入日志房间
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # 离开日志房间
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def log_message(self, event):
        # 收到日志行推送
        await self.send_json({'message': event['message']})

    async def log_complete(self, event):
        # 日志完成事件
        await self.send_json({'complete': event['timestamp']})