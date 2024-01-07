import os
import asyncio
from typing import Any
import websockets
import json
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
from aiortc.contrib.media import MediaRelay, MediaPlayer, MediaStreamTrack

options = {"framerate": "24", "video_size": "320x240"}
webcam = MediaPlayer("/dev/video0", format="v4l2", options=options)
video_track: MediaStreamTrack

pc: RTCPeerConnection
websocket_url = os.getenv('WEBSOCKET_URL')

if not websocket_url:
    raise Exception('Forgot to initialize websocket url')

class WebSocket:
    def __init__(self):
        pass

    async def connect(self, uri):
        self.channels = {}
        self.uri = uri
        self.ws = await websockets.connect(self.uri)

    async def listen_for_msgs(self):
        while True:
            res = json.loads(await self.ws.recv())
            await self.propagate(res['channel'], res['data'])

    async def send_pings(self):
        while True:
            if self.ws.open:
                await self.emit('clientsOnline')
            await asyncio.sleep(20)

    async def emit(self, channel: str, data: Any = ''):
        await self.ws.send(json.dumps({ 'channel': channel, 'data': data }))

    def register(self, channel, callback):
        self.channels[channel] = callback

    async def propagate(self, channel, data):
        callback = self.channels.get(channel)
        if not callback: return
        await callback(data)

async def add_video_track(pc):
    global video_track
    relay = MediaRelay()
    video_track = relay.subscribe(webcam.video)
    pc.addTrack(video_track)

async def main():
    global pc
    ws = WebSocket()
    await ws.connect(websocket_url)

    async def connect_handler(data):
        print('connected')

    async def send_offer(data):
        offer = await pc.createOffer()
        print('sending offer')
        await pc.setLocalDescription(offer)
        await ws.emit(
            "offer",
            {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
            },
        )

    async def set_answer(answer):
        print('answer')
        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
        )

    async def msg_handler(data):
        print('Msg:', data)

    async def disconnect_handler(data):
        print('received disconnect request')
        await pc.close()

    ws.register('connected', connect_handler)
    ws.register('begin', send_offer)
    ws.register('answer', set_answer)
    ws.register('msg', msg_handler)
    ws.register('disconnect', disconnect_handler)

    init = asyncio.create_task(initialize_connection(ws))
    send_pings = asyncio.create_task(ws.send_pings())
    listen_for_msgs = asyncio.create_task(ws.listen_for_msgs())
    await asyncio.gather(init, send_pings, listen_for_msgs)

async def initialize_connection(ws: WebSocket):
    global pc
    print('creating new rtc connection')
    iceServers = [RTCIceServer(urls="stun:stun.l.google.com:19302")]
    pc = RTCPeerConnection(RTCConfiguration(iceServers))

    @pc.on("iceconnectionstatechange")
    async def on_ice_candidate():
        global video_track
        print(pc.iceConnectionState)
        if (pc.iceConnectionState not in ['disconnected', 'closed', 'failed']):
            return
        await pc.close()
        video_track.stop()
        await initialize_connection(ws)

    # add reconnect code
    await add_video_track(pc)
    await ws.emit('clientsOnline')
    await ws.emit('match', { 'type': 'drone', 'id': 'droneId' })

asyncio.run(main())
