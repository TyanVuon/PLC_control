from tqdm import tqdm
import os
import time

class CommandHandler:
    def __init__(self, serial_controller, camera_controller):
        self.serial = serial_controller
        self.camera = camera_controller
        self.image_count = 1
        self.current_section_count = 0
        self.current_layer_index = 0
        self.output_dir = None
        self.layer_folders = []
        self.layers = [1, 8, 12, 18, 24, 30, 36, 40, 45, 60, 60]  # Example total sections per layer

        # Progress bars
        self.total_images = sum(self.layers)  # Total number of images to be captured
        self.total_bar = tqdm(total=self.total_images, desc="Total Progress", unit="image", position=0, leave=True)
        


    def handle_ready(self):
        """Send READY signal and initialize folder structure."""
        #print("[INFO] Sending READY signal (300) to PLC.")
        self.serial.write_data(300)
        self.initialize_folders()
        

        # Initialize the first layer progress bar
        self.layer_bar = tqdm(total=self.layers[self.current_layer_index], 
                              desc=f"Layer {self.current_layer_index + 1} Progress", 
                              unit="image", position=1, leave=True)

    def initialize_folders(self):
        """Create directory structure for the session."""
        self.output_dir = self._create_batch_directory()
        self._create_layer_folders()

    def _create_batch_directory(self):
        base_path = os.getcwd()
        batch_number = 1
        while os.path.exists(os.path.join(base_path, f"Batch_{batch_number}")):
            batch_number += 1
        dir_name = f"Batch_{batch_number}"
        os.makedirs(dir_name, exist_ok=True)
        return dir_name

    def _create_layer_folders(self):
        for i in range(1, len(self.layers) + 1):
            layer_folder = os.path.join(self.output_dir, f"Layer_{i}")
            os.makedirs(layer_folder, exist_ok=True)
            self.layer_folders.append(layer_folder)


    def handle_capture(self, layer, sections):
        """Handle image capture for the specified layer and section count."""
        # Synchronize to the incoming layer if needed
        if layer != self.current_layer_index:
            print(f"[INFO] Syncing to Layer {layer + 1} from Layer {self.current_layer_index + 1}")
            self.current_layer_index = layer
            self.current_section_count = 0

            # Close previous progress bar if it exists
            if hasattr(self, 'layer_bar') and self.layer_bar:
                self.layer_bar.close()

            # Initialize progress bar for the new layer
            self.layer_bar = tqdm(
                total=self.layers[self.current_layer_index],
                desc=f"Layer {self.current_layer_index + 1} Progress",
                unit="image", position=1, leave=True
            )

            # If this is the first image of the new layer, add stabilization step
        if self.current_section_count == 0:
            # Wait for mechanical and exposure stability
            time.sleep(0.1)  # Adjust the delay as needed
            self.camera.flush_camera_buffer(num_frames=2)  # Flush a few frames to ensure freshness


        layer_folder = self.layer_folders[layer]
        image_path = os.path.join(layer_folder, f"image_{self.image_count}.jpg")

        time.sleep(0.1)
        self.camera.flush_camera_buffer(num_frames=3)

        if self.camera.capture_image(image_path):
            # Confirm the image is saved
            for _ in range(10):
                if os.path.exists(image_path):
                    break
                time.sleep(0.1)
            else:
                print("[ERROR] Image not saved to disk. Skipping DONE signal.")
                return  # Do not send the 500 signal

            self.image_count += 1
            self.current_section_count += 1

            # Update bars
            self.layer_bar.update(1)
            self.total_bar.update(1)

            # Check if the current section is complete
            if self.current_section_count >= sections:
                # Layer is complete, but do NOT increment layer index here
                tqdm.write(f"[INFO] Layer {self.current_layer_index + 1} complete.")
                self.layer_bar.close()
                # Do not increment self.current_layer_index here.
                # Just send DONE signal.
                self.serial.write_data(500)
            else:
                # Normal capture completion for each image
                self.serial.write_data(500)
        else:
            self.serial.write_data(600)  # Optional: send ERROR signal


    def process_incoming_command(self, command, layer, sections):
        """Process incoming commands from the PLC."""
        if command == 400:
            self.handle_capture(layer, sections)
        else:
            print(f"[WARNING] Unknown command received: {command}")
