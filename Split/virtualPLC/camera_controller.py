import time
"this file is dummy cam simulating opening of capturing"


class CameraController:
    def __init__(self, device_path=0):
        print("Camera initialized (Dummy Mode).")
        self.device_index = device_path
        self.dummy_mode = True  # Always in Dummy Mode
        self.frame_count = 0
        print(f"Camera initialized (Dummy Mode).")



    def warm_up(self):
        print("Warming up camera (Dummy Mode)...")
        time.sleep(1)

    def configure_camera(self):
        print("Configuring camera (Dummy Mode)...")

    def flush_camera_buffer(self, num_frames=0):
        """Simulate flushing the camera buffer."""
        print(f"Flushing camera buffer: {num_frames} frames (Dummy Mode).")

    def capture_image(self, save_path):
        """Simulate capturing an image."""
        self.frame_count += 1
        print(f"Captured dummy image {self.frame_count} at: {save_path}")

        # Simulate a response as if the image was saved
        return True  # Always indicate success

    def release(self):
        """Simulate releasing the camera."""
        print("Camera resource released (Dummy Mode).")
