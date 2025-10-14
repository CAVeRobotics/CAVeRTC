#!/usr/bin/env python3

import cv2
import depthai as dai
# import pyvirtualcam

# Create pipeline
with dai.Pipeline() as pipeline:
    # Define source and output
    cam = pipeline.create(dai.node.Camera).build()
    videoQueue = cam.requestOutput((1280,720)).createOutputQueue()

    # Connect to device and start pipeline
    pipeline.start()
    # uvc = pyvirtualcam.Camera(width=1280, height=720, fps=60)
    while pipeline.isRunning():
        videoIn = videoQueue.get()
        assert isinstance(videoIn, dai.ImgFrame)
        # uvc.send(videoIn.getCvFrame())

        cv2.imshow("video", videoIn.getCvFrame())

        if cv2.waitKey(1) == ord("q"):
            break
