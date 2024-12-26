import os
import time
import serial
import cv2
from tqdm import tqdm


# =========================
# SerialController Class
# =========================

class SerialController:
    def __init__(self, port_name='/dev/ttyUSB0', baudrate=9600, parity=serial.PARITY_ODD,
                 stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1,
                 rtscts=False, xonxoff=False):
        # print("Initializing SerialController...")  # Debugging statement
        self.serial_port = self._initialize_serial(
            port_name, baudrate, parity, stopbits, bytesize, timeout, rtscts, xonxoff
        )
        if self.serial_port is None:
            raise Exception("Failed to establish serial connection.")

    def _initialize_serial(self, port_name, baudrate, parity, stopbits, bytesize, timeout, rtscts, xonxoff, retries=3):
        for attempt in range(retries):
            try:
                ser = serial.Serial(
                    port=port_name, baudrate=baudrate, parity=parity,
                    stopbits=stopbits, bytesize=bytesize, timeout=timeout,
                    rtscts=rtscts, xonxoff=xonxoff
                )
                if ser.is_open:
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()
                    ser.dtr = False
                    time.sleep(0.1)
                    ser.dtr = True
                    # print(f"Serial port {port_name} successfully opened.")
                    return ser
            except Exception as e:
                print(f"[ERROR] SerialController Attempt {attempt + 1}: {e}")
                time.sleep(1)
        print("[ERROR] SerialController failed to initialize after multiple attempts.")
        return None

    def write_data(self, data):
        try:
            self.serial_port.write(data.to_bytes(2, byteorder='little'))  # Send data
            self.serial_port.flush()  # Ensure the data is actually transmitted
        except Exception as e:
            raise Exception(f"[ERROR] Failed to send data to PLC: {e}")

    def read_data(self):
        try:
            raw_data = self.serial_port.read_until(b'\r\n')[:-2]
            if raw_data:
                words = [int.from_bytes(raw_data[i:i + 2], byteorder='little') for i in range(0, len(raw_data), 2)]
                return words[0], words[1], words[2]
            else:
                return None, None, None
        except Exception as e:
            print(f"[ERROR] Failed to read data: {e}")
            return None, None, None

    def close(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            print("Serial port closed.")


# =========================
# CameraController Class
# =========================

class CameraController:
    #def __init__(self, device_path='/dev/video0'): for UBUNTU
    def __init__(self, device_path=0):
        # print("Initializing CameraController...")
        self.device_index = device_path
        self.camera = cv2.VideoCapture(self.device_index)
        if not self.camera.isOpened():
            raise Exception(f"Camera at index {device_path} could not be opened.")
        # print("Camera initialized.")
        self.configure_camera()
        self.flush_camera_buffer(num_frames=15)

    def configure_camera(self):
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 2048)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 2048)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        # print("Camera configured.")

    def flush_camera_buffer(self, num_frames=15):
        """Flush the camera buffer to clear stale frames."""
        # print(f"[INFO] Flushing camera buffer with {num_frames} frames.")
        for _ in range(num_frames):
            ret, frame = self.camera.read()
            if not ret:
                print("[DEBUG] Failed to flush a frame from the camera buffer.")

    def capture_image(self, save_path):
        ret, frame = self.camera.read()
        if ret:
            cv2.imwrite(save_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            return True
        print("[ERROR] Failed to capture image.")
        return False

    def release(self):
        self.camera.release()
        print("Camera resource released.")


# =========================
# CommandHandler Class
# =========================

class CommandHandler:
    def __init__(self, serial_controller, camera_controller, product_id=None, username=None):
        self.serial = serial_controller
        self.camera = camera_controller
        self.image_count = 1
        self.current_layer = None  # Track layer changes

        # Allow parameter-based or manual input
        self.product_id = product_id if product_id else input("Enter Product ID (12 characters): ").strip()
        self.username = username if username else input("Enter Username: ").strip()

        # Ensure both product_id and username are valid
        if not self.product_id or not self.username:
            raise ValueError("Both Product ID and Username must be provided.")

        # Set the output directory after initializing product_id and username
        self.output_dir = os.path.join(os.getcwd(), f"{self.product_id}_{self.username}")
        self.initialize_output_directory()

    def initialize_output_directory(self):
        """Create the output directory."""
        if not self.output_dir:
            raise ValueError("Output directory is not set.")
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[INFO] Output directory created: {self.output_dir}")

    def handle_ready(self):
        """Send READY signal (300) to PLC and initialize the output directory."""
        if not self.serial.serial_port or not self.serial.serial_port.is_open:
            raise Exception("[ERROR] Serial port is not open. Cannot send READY signal.")

        self.serial.write_data(300)  # Send 300 to PLC
        time.sleep(0.1)
        self.camera.flush_camera_buffer(num_frames=8)

        # Initialize progress bars
        self.total_images = 334  # Adjust based on total images to capture
        self.total_bar = tqdm(total=self.total_images, desc="Total Progress", unit="image", position=0, leave=True)

    def handle_capture(self, layer, section):
        """Capture and save an image with a specific naming format."""
        # Detect new layer transition
        if layer != self.current_layer:
            self.camera.flush_camera_buffer(num_frames=7)  # Clear stale frames at layer start
            self.current_layer = layer  # Update current layer

        file_name = f"{self.product_id}-layer{layer + 1:02d}-section{section:02d}.png"
        save_path = os.path.join(self.output_dir, file_name)

        self.camera.flush_camera_buffer(num_frames=3)

        if self.camera.capture_image(save_path):
            self.serial.write_data(500)  # DONE signal for normal capture completion
            self.total_bar.update(1)  # Update progress bar
        else:
            self.serial.write_data(600)  # Treat as a failed capture

    def process_incoming_command(self, command, layer, section):
        """Process incoming commands and capture images based on them."""
        if command == 700:  # Exit command
            print("[INFO] Exit command received. Terminating program.")
            self.serial.write_data(700)
            self.camera.release()
            self.serial.close()
            exit(0)
        elif command == 400:  # Capture command
            self.handle_capture(layer, section)
        else:
            print(f"[WARNING] Unknown command received: {command}")


# =========================
# Main Function
# =========================

def main():
    serial_comm = None
    camera = None
    handler = None
    try:

        #serial_comm = SerialController(port_name='/dev/ttyUSB0') for UBUNTU
        serial_comm = SerialController(port_name='COM2')
        camera = CameraController()
        handler = CommandHandler(serial_comm, camera)

        print("Type 'ready' to initialize or 'exit' to quit.")

        while True:
            user_input = input("Enter command: ").strip().lower()
            if user_input == 'ready':
                handler.handle_ready()  # Send 300 and initialize directory
                # print("[INFO] Ready signal sent and directory initialized. Waiting for PLC commands.")
                while True:
                    command, layer, section = serial_comm.read_data()
                    if command:
                        handler.process_incoming_command(command, layer, section)
            elif user_input == 'exit':
                print("[INFO] Exiting program as requested.")
                break
            else:
                print("[WARNING] Unknown command. Type 'ready' to initialize or 'exit' to quit.")

    except KeyboardInterrupt:
        print("\n Terminates halfway")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    finally:
        if serial_comm:
            serial_comm.close()
        if camera is not None:
            camera.release()
        if handler:
            if hasattr(handler, 'total_bar') and handler.total_bar:
                handler.total_bar.close()


if __name__ == "__main__":
    main()