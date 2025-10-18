import asyncio
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
import fractions
from datetime import datetime
import depthai as dai

class CustomVideoStreamTrack(VideoStreamTrack):
    def __init__(self, camera_id):
        super().__init__()
        # self.cap = cv2.VideoCapture(camera_id)
        self.frame_count = 0

        self.pipeline = dai.Pipeline()
        self.cam = self.pipeline.create(dai.node.Camera).build()
        self.videoQueue = self.cam.requestOutput((1280,720)).createOutputQueue(maxSize=1, blocking=False)
        self.pipeline.start()

    async def recv(self):
        if self.pipeline.isRunning():
            self.frame_count += 1
            print(f"Sending frame {self.frame_count}")
            # ret, frame = self.cap.read()
            videoIn = self.videoQueue.get()
            # assert isinstance(videoIn, dai.ImgFrame)
            print("Got frame from camera")
            if not videoIn:
                print("Frame not available")
                return None
            frame = videoIn.getCvFrame()
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = self.frame_count
            video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = self.frame_count
            video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base
            return video_frame

async def setup_webrtc_and_run(ip_address, port, camera_id):
    signaling = TcpSocketSignaling(ip_address, port)
    pc = RTCPeerConnection()
    video_sender = CustomVideoStreamTrack(camera_id)
    pc.addTrack(video_sender)

    try:
        await signaling.connect()

        @pc.on("datachannel")
        def on_datachannel(channel):
            print(f"Data channel established: {channel.label}")

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state is {pc.connectionState}")
            if pc.connectionState == "connected":
                print("WebRTC connection established successfully")

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await signaling.send(pc.localDescription)

        while True:
            obj = await signaling.receive()
            if isinstance(obj, RTCSessionDescription):
                await pc.setRemoteDescription(obj)
                print("Remote description set")
            elif obj is None:
                print("Signaling ended")
                break
        print("Closing connection")
    finally:
        await pc.close()

async def main():
    ip_address = "localhost" # Ip Address of Remote Server/Machine
    port = 9999
    camera_id = 0  # Change this to the appropriate camera ID
    await setup_webrtc_and_run(ip_address, port, camera_id)

if __name__ == "__main__":
    asyncio.run(main())