import asyncio
import json
import cv2
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole
from av import VideoFrame

# ---- Custom Video Track (OpenCV webcam) ----
class CameraVideoTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)  # 0 = default camera
        if not self.cap.isOpened():
            raise RuntimeError("Could not open webcam")

    async def recv(self):
        print("Capturing frame from webcam")
        pts, time_base = await self.next_timestamp()

        ret, frame = self.cap.read()
        if not ret:
            raise Exception("Camera capture failed")

        # Convert frame to av.VideoFrame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

# ---- WebRTC setup ----
async def run():
    pc = RTCPeerConnection()
    pc.addTrack(CameraVideoTrack())

    async with websockets.connect("ws://localhost:8080") as ws:
        # Handle messages from signaling server
        async def signaling():
            async for message in ws:
                data = json.loads(message)
            if data["type"] == "answer":
                answer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                await pc.setRemoteDescription(answer)
            elif data["type"] == "candidate":
                candidate = data["candidate"]
                ice_candidate = RTCIceCandidate(
                    sdpMid=candidate.get("sdpMid"),
                    sdpMLineIndex=candidate.get("sdpMLineIndex"),
                    candidate=candidate.get("candidate")
                )
                await pc.addIceCandidate(ice_candidate)

        # When ICE candidates are gathered, send them
        @pc.on("icecandidate")
        async def on_icecandidate(event):
            if event.candidate:
                await ws.send(json.dumps({
                    "type": "candidate",
                    "candidate": event.candidate.to_dict()
                }))

        # Create offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await ws.send(json.dumps({
            "type": pc.localDescription.type,
            "sdp": pc.localDescription.sdp
        }))

        await signaling()  # loop until closed

if __name__ == "__main__":
    asyncio.run(run())
