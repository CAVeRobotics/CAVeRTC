import asyncio
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceCandidate, RTCIceServer, RTCConfiguration
from websockets.asyncio.client import connect
from av import VideoFrame
import fractions
from datetime import datetime
import depthai as dai
import json

remoteDescSet = False
candidateQueue = []

ice_servers = [RTCIceServer(urls="stun:stun.l.google.com:19302")]

class CustomVideoStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.frame_count = 0
        self.pipeline = dai.Pipeline()
        self.cam = self.pipeline.create(dai.node.Camera).build()
        self.videoQueue = self.cam.requestOutput(size=(1280,720), fps=30).createOutputQueue(maxSize=1, blocking=False)
        self.pipeline.start()

    async def recv(self):
        if self.pipeline.isRunning():
            self.frame_count += 1
            # print(f"Sending frame {self.frame_count}")
            videoIn = self.videoQueue.get()
            # print("Got frame from camera")
            if not videoIn:
                print("Frame not available")
                return None
            frame = videoIn.getCvFrame()
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = self.frame_count
            video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = self.frame_count
            video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base
            return video_frame
        

async def setup_webrtc_and_run(ip_address, port):
    pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))
    video_sender = CustomVideoStreamTrack()
    pc.addTrack(video_sender)


    async with connect(f"ws://{ip_address}:{port}/") as ws:
        await ws.send(json.dumps({"type": "join", "room": "demo", "role": "sender"}))

        try:
            @pc.on("datachannel")
            def on_datachannel(channel):
                print(f"Data channel established: {channel.label}")

            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                print(f"Connection state is {pc.connectionState}")
                if pc.connectionState == "connected":
                    print("WebRTC connection established successfully")

            @pc.on("icecandidate")
            async def on_icecandidate(candidate):
                ws.send(json.dumps({"type":"candidate", "candidate":candidate, "room":"demo"}))


            async for message in ws:
                msg = json.loads(message)
                # print(msg)

                if msg["type"] == "ready" or msg["type"] == "peer-joined":
                    print("Creating offer")
                    offer = await pc.createOffer()
                    await pc.setLocalDescription(offer)
                    await ws.send(json.dumps({"type": "offer", "sdp":{"type":offer.type,"sdp":offer.sdp}, "room":"demo"}))
                elif msg["type"] == "answer":
                    print("Answering")
                    # print(msg["answer"])
                    await pc.setRemoteDescription(RTCSessionDescription(msg["answer"]["sdp"], msg["answer"]["type"]))
                    remoteDescSet = True
                    while candidateQueue:
                        await pc.addIceCandidate(RTCIceCandidate(candidateQueue.pop()))
                elif msg["type"] == "candidate":
                    if remoteDescSet:
                        RTCICComps = msg["candidate"]["candidate"].split(' ')
                        await pc.addIceCandidate(RTCIceCandidate(
                             component=int(RTCICComps[1]), 
                             foundation=RTCICComps[0][10:],
                             ip=RTCICComps[4],
                             port=int(RTCICComps[5]),
                             priority=int(RTCICComps[3]),
                             protocol=RTCICComps[2],
                             type=RTCICComps[6] + " " + RTCICComps[7],
                             sdpMid=msg["candidate"]["sdpMid"],
                             sdpMLineIndex=int(msg["candidate"]["sdpMLineIndex"])))
                    else:
                        candidateQueue.append(msg["candidate"])
                else:
                    print(f"Received unsupported type: {msg['type']}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await pc.close()



async def main():
    ip_address = "0.0.0.0" # Ip Address of Remote Server/Machine
    port = 8080
    await setup_webrtc_and_run(ip_address, port)

if __name__ == "__main__":
    asyncio.run(main())