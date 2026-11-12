"""Shows a camera's frames through SpinnakerCamera directly, without a gateway or a broker.

E.g.: python etc/examples/view_opencv.py 10.20.6.0
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from pris_msgs.utils.io import load

from pris_camera_gateway.camera import SpinnakerCamera
from pris_camera_gateway.conf.options_pb2 import CameraGatewayOptions


def main() -> None:
    path = Path(__file__).parents[1] / "conf" / "options.json"
    options = load(str(path), CameraGatewayOptions).camera
    options.ip = sys.argv[1] if len(sys.argv) > 1 else options.ip
    camera = SpinnakerCamera(options)
    camera.connect()
    camera.start()
    try:
        while True:
            capture = camera.grab(3000)
            if capture is None:
                continue
            array = cv2.imdecode(np.frombuffer(capture.image.data, dtype=np.uint8),
                                 cv2.IMREAD_COLOR)
            cv2.imshow("frame", array)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.disconnect()


if __name__ == "__main__":
    main()
