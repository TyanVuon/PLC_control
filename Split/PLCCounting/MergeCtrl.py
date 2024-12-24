import os
import time
import serial
import cv2
from tqdm import tqdm

print("Script started.")  # Debugging statement

# =========================
# SerialController Class
# =========================

class SerialController:
    def __init__(self, port_name='/dev/ttyUSB0', baudrate=9600, parity=serial.PARITY_ODD,
                 stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1,
                 rtscts=False, xonxoff=False):
        print("Initializing SerialController...")  # Debugging statement
        self.serial_port = self._initialize_serial(
            port_name, baudrate, parity, stopbits, bytesize, timeout, rtscts, xonxoff
        )
        if self.serial_port is None:
            raise Exception("Failed to establish serial connection.")
        #print("SerialController initialized successfully.")  # Debugging statement

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
                    print(f"Serial port {port_name} successfully opened.")
                    return ser
            except Exception as e:
                print(f"[ERROR] SerialController Attempt {attempt + 1}: {e}")
                time.sleep(1)
        print("[ERROR] SerialController failed to initialize after multiple attempts.")
        return None

    def write_data(self, data):
        try:
            self.serial_port.write(data.to_bytes(2, byteorder='little'))
            print(f"[DEBUG] Sent data: {data}")  # Debugging statement
        except Exception as e:
            print(f"[ERROR] Failed to send data: {e}")

    def read_data(self):
        """Read and parse incoming 16-bit words, using the first word as the command."""
        try:
            # Read data until the termination sequence '\r\n' and strip the last two bytes
            raw_data = self.serial_port.read_until(b'\r\n')[:-2]

            if raw_data:
                # Display the raw byte stream for debugging
                #print(f'[DEBUG] Raw byte stream: {raw_data.hex(" ")}')

                # Handle bc02 ENDING 
                if len(raw_data) == 2:
                    command = int.from_bytes(raw_data, byteorder='little')
                    print(f"[INFO] Finish received from PLC: {command}")
                    return command, None, None 

                # Ensure the length of the data is valid (multiple of 2 bytes for 16-bit words)
                if len(raw_data) % 2 != 0 or len(raw_data) < 6:
                    print("[ERROR] Incomplete 16-bit data received. Discarding data.")
                    return None, None, None

                # Split the raw data into 16-bit chunks
                words = [int.from_bytes(raw_data[i:i+2], byteorder='little') for i in range(0, len(raw_data), 2)]

                # Desired format
                command = words[0]  # Command
                layer = words[1]  # Layer
                sections = words[2]  # Sections

                print(f"[INFO] Merged Decimal: {command:04d}{layer:02d}{sections:02d}")

                return words[0], words[1], words[2]
            else:
                #print("[DEBUG] No data received.")
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
    def __init__(self, device_path='/dev/video0'):
        print("Initializing CameraController...")  # Debugging statement
        self.device_index = device_path
        self.camera = cv2.VideoCapture(self.device_index)
        if not self.camera.isOpened():
            raise Exception(f"Camera at index {device_path} could not be opened.")
        print("Camera initialized.")
        self.flush_camera_buffer(num_frames=15)
        self.configure_camera()
        #print("CameraController initialized successfully.")  # Debugging statement

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
            ret, frame = self.camera.read()
            if not ret:
                print("[DEBUG] Failed to flush a frame from camera buffer.")

    def capture_image(self, save_path):
        """Captures an image and saves it to the specified path."""
        ret, frame = self.camera.read()
        if ret:
            cv2.imwrite(save_path, frame)
            #print(f"[INFO] Captured image saved to: {save_path}")
            return True
        print("[ERROR] Failed to capture image.")
        return False

    def release(self):
        """Releases the camera resource."""
        self.camera.release()
        print("Camera resource released.")

# =========================
# CommandHandler Class
# =========================

class CommandHandler:
    def __init__(self, serial_controller, camera_controller):
        print("Initializing CommandHandler...")  # Debugging statement
        self.serial = serial_controller
        self.camera = camera_controller
        self.image_count = 1
        self.current_section_count = 0
        self.current_layer_index = 0
        self.output_dir = None
        self.layer_folders = []
        self.layers = [1, 8, 12, 18, 24, 30, 36, 40, 45, 60, 60]  # Example total sections per layer

        # Overall progress bar
        self.total_images = sum(self.layers)
        self.total_bar = tqdm(total=self.total_images, desc="Total Progress", unit="image", position=0, leave=True)

        self.current_iai_index = None  # Keeps track of the current layer index received from PLC
        #print("CommandHandler initialized successfully.")  # Debugging statement

    def handle_ready(self):
        """Send READY signal and initialize folder structure."""
        #print("[INFO] Sending READY signal (300) to PLC.")
        #print("[DEBUG] Handling 'ready' command.")  # Debugging statement
        self.serial.write_data(300)

        # Re-confirm the total images and refresh the total_bar
        self.total_images = sum(self.layers)  # Static total
        self.total_bar.n = 0  # Reset numerator to start fresh
        self.total_bar.total = self.total_images  # Ensure the denominator is correct
        self.total_bar.refresh()  # Refresh tqdm to display updates

        self.initialize_folders()

        # Initialize the first layer progress bar
        self.layer_bar = tqdm(total=self.layers[self.current_layer_index], 
                                desc=f"Layer {self.current_layer_index + 1} Progress", 
                                unit="image", position=1, leave=True)
        print(f"[DEBUG] Initialized progress bar for Layer {self.current_layer_index + 1}.")  # Debugging statement

    def initialize_folders(self):
        """Create directory structure for the session."""
        print("[DEBUG] Initializing folders.")  # Debugging statement
        self.output_dir = self._create_batch_directory()
        self._create_layer_folders()

    def _create_batch_directory(self):
        base_path = os.getcwd()
        batch_number = 1
        while os.path.exists(os.path.join(base_path, f"Batch_{batch_number}")):
            batch_number += 1
        dir_name = f"Batch_{batch_number}"
        os.makedirs(dir_name, exist_ok=True)
        #print(f"[INFO] Batch directory created: {dir_name}")  # Debugging statement
        return dir_name

    def _create_layer_folders(self):
        for i in range(1, len(self.layers) + 1):
            layer_folder = os.path.join(self.output_dir, f"Layer_{i}")
            os.makedirs(layer_folder, exist_ok=True)
            self.layer_folders.append(layer_folder)
            #print(f"[INFO] Layer folder created: {layer_folder}")  # Debugging statement

    def handle_capture(self, layer, sections):
        """Handle image capture dynamically for the specified layer and section count."""
        #print(f"[DEBUG] Handling capture for Layer {layer}, Sections {sections}.")  # Debugging statement
        try:
            layer_folder = self.layer_folders[layer]  
            image_path = os.path.join(layer_folder, f"image_{self.image_count}.jpg")
        except IndexError:
            print(f"[ERROR] Invalid layer index: {layer}. Available layers: {len(self.layer_folders)}")
            return

        # Comment out for testing
        time.sleep(0.1)  # Simulate delay for stability
        self.camera.flush_camera_buffer(num_frames=3)

        if self.camera.capture_image(image_path):
            self.image_count += 1
            self.current_section_count += 1

            # Update progress bars
            self.layer_bar.update(1)  # Update numerator for layer progress
            self.total_bar.update(1)  # Overall total progress

            # Check if the current section is complete
            if self.current_section_count >= self.layers[layer]:  # Check against fixed total
                #tqdm.write(f"[INFO] Layer {layer + 1} complete.")
                print(f"[INFO] Layer {layer + 1} complete.")  # Debugging statement
                self.layer_bar.close()
                self.serial.write_data(500)  # DONE signal for completed layer
            else:
                self.serial.write_data(500)  # DONE signal for normal capture completion
        else:
            self.serial.write_data(600)  # Treat as a failed capture

    def process_incoming_command(self, command, layer, sections):
        """Process incoming commands and dynamically adjust layer progress."""
        
        #print(f"[DEBUG] Processing incoming command: {command}, Layer: {layer}, Sections: {sections}")  # Debugging statement

        if command == 700:
            print("[INFO] Exit command received (700). Terminating program.")
            self.serial.write_data(700)  # Optional: Acknowledge exit command to PLC
            self.camera.release()  # Release camera resources
            self.serial.close()  # Close serial connection
            exit(0)  # Exit the program immediately

        if command == 400:

            # Detect layer change
            if layer != self.current_iai_index:
                if self.current_iai_index is not None:  # If not the first command
                    tqdm.write(f"[INFO] Layer {self.current_iai_index} complete.")
                    if hasattr(self, 'layer_bar') and self.layer_bar:
                        self.layer_bar.close()  # Close the old layer bar

                # Update current layer index
                self.current_iai_index = layer

                # UNCOMMENT after testing
                self.camera.flush_camera_buffer(num_frames=5)  # Ensure the camera is ready for the new layer

                # Ensure folder for the new layer exists
                while len(self.layer_folders) < layer:
                    layer_folder = os.path.join(self.output_dir, f"Layer_{len(self.layer_folders) + 1}")
                    os.makedirs(layer_folder, exist_ok=True)
                    self.layer_folders.append(layer_folder)
                    #print(f"[INFO] New layer folder created: {layer_folder}")  # Debugging statement

                # Initialize new progress bar for the new layer with static denominator
                total_sections_for_layer = self.layers[layer] 
                self.layer_bar = tqdm(
                    total=total_sections_for_layer,  # Use fixed total from `self.layers`
                    desc=f"Layer {layer} Progress",
                    unit="image", position=1, leave=True
                )
                #print(f"[DEBUG] Initialized progress bar for Layer {layer}.")  # Debugging statement

            # Pass the command to handle_capture
            self.handle_capture(layer, sections)
        else:
            print(f"[WARNING] Unknown command received: {command}")

# =========================
# Main Function
# =========================

def main():
    try:
        #print("[DEBUG] Starting main function.")  # Debugging statement
        serial_comm = SerialController(port_name='/dev/ttyUSB0')
        camera = CameraController()
        handler = CommandHandler(serial_comm, camera)

        print("Ready to accept commands. Type 'ready' or 'exit'.")

        while True:
            user_input = input("Enter command: ").strip().lower()
            if user_input == 'ready':
                #print("[INFO] Sending READY signal to PLC.")
                handler.handle_ready()  # Sends 300 to PLC
                #print("[INFO] Folders and counters initialized.")
                #print("listen")
                while True:
                    command, layer, sections = serial_comm.read_data()
                    if command:
                        handler.process_incoming_command(command, layer, sections)
            elif user_input == 'exit':
                print("Exiting...")
                break
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    finally:
        serial_comm.close()
        camera.release()

if __name__ == "__main__":
    main()
