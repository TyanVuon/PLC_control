import cv2
import os
import time


class CameraController:
    def __init__(self, device_path='/dev/video0'):
        self.device_index = device_path
        self.camera = cv2.VideoCapture(self.device_index)
        if not self.camera.isOpened():
            raise Exception(f"Camera at index {device_path} could not be opened.")
        print("Camera initialized.")
        self.flush_camera_buffer(num_frames=15)
        self.configure_camera()

    def warm_up(self):
        time.sleep(1)  # Adjust the delay as needed
        self.flush_camera_buffer(num_frames=15)

    def configure_camera(self):
        """Configures the camera with necessary settings."""
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 2048)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 2048)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        print("Camera configured.")

    def flush_camera_buffer(self, num_frames=0):
        """Flush the camera buffer to clear stale frames."""
        for _ in range(num_frames):
            self.camera.read()

    def capture_image(self, save_path):
        """Captures an image and saves it to the specified path."""
        ret, frame = self.camera.read()
        if ret:
            cv2.imwrite(save_path, frame)
            #print(f"Captured image saved to: {save_path}")
            return True
        print("[ERROR] Failed to capture image.")
        return False

    def release(self):
        """Releases the camera resource."""
        self.camera.release()
        print("Camera resource released.")
