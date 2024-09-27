import time
import websockets
from requests import Session
import os
import dotenv
import json
import asyncio

dotenv.load_dotenv()

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

API_BASE = "https://openapi.vito.ai"

class RTZRClient:
    def __init__(self):
        self._sess = Session()
        self._token = None
        self.websocket = None
        self.queue = asyncio.Queue()

    @property
    def token(self):
        if self._token is None or self._token["expire_at"] < time.time():
            resp = self._sess.post(
                API_BASE + "/v1/authenticate",
                data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
            )
            resp.raise_for_status()
            self._token = resp.json()
        return self._token["access_token"]

    async def start(self, config=None):
        if self.websocket is not None:
            raise ValueError("Already connected")
        if config is None:
            config = dict(
                sample_rate="16000",
                encoding="LINEAR16",
                use_itn="true",
                use_disfluency_filter="false",
                use_profanity_filter="false",
            )

        STREAMING_ENDPOINT = "wss://{}/v1/transcribe:streaming?{}".format(
            API_BASE.split("://")[1], "&".join(map("=".join, config.items()))
        )
        conn_kwargs = dict(extra_headers={"Authorization": "bearer " + self.token})

        self.websocket = await websockets.connect(STREAMING_ENDPOINT, **conn_kwargs)
        
        # Start the transcriber coroutine
        asyncio.create_task(self.transcriber())
    
    async def stream(self, data):
        await self.websocket.send(data)

    async def stop(self):
        await self.websocket.send("EOS")
        await self.websocket.close()
        self.websocket = None

    async def transcriber(self):
        try:
            async for msg in self.websocket:
                msg = json.loads(msg)
                if msg["final"]:
                    await self.queue.put(msg["alternatives"][0]["text"])
                    print("User: " + msg["alternatives"][0]["text"])
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")

    async def get_transcription(self):
        return await self.queue.get()