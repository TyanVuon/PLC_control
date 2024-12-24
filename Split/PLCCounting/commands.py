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


        # Overall progress bar
        self.total_images = sum(self.layers)
        self.total_bar = tqdm(total=self.total_images, desc="Total Progress", unit="image", position=0, leave=True)

        self.current_iai_index = None  # Keeps track of the current layer index received from PLC

    def handle_ready(self):
        """Send READY signal and initialize folder structure."""
        #print("[INFO] Sending READY signal (300) to PLC.")
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
        """Handle image capture dynamically for the specified layer and section count."""
        layer_folder = self.layer_folders[layer]  
        image_path = os.path.join(layer_folder, f"image_{self.image_count}.jpg")


        #comment out for testing
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
                self.layer_bar.close()
                self.serial.write_data(500)  # DONE signal for completed layer
            else:
                self.serial.write_data(500)  # DONE signal for normal capture completion
        else:
            self.serial.write_data(600)  # Treat as a failed capture
 
    def process_incoming_command(self, command, layer, sections):
        """Process incoming commands and dynamically adjust layer progress."""
        
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


                #UNCOMMENT after testing
                self.camera.flush_camera_buffer(num_frames=5)  # Ensure the camera is ready for the new layer


                # Ensure folder for the new layer exists
                while len(self.layer_folders) < layer:
                    layer_folder = os.path.join(self.output_dir, f"Layer_{len(self.layer_folders) + 1}")
                    os.makedirs(layer_folder, exist_ok=True)
                    self.layer_folders.append(layer_folder)

                # Initialize new progress bar for the new layer with static denominator
                total_sections_for_layer = self.layers[layer] 
                self.layer_bar = tqdm(
                    total=total_sections_for_layer,  # Use fixed total from `self.layers`
                    desc=f"Layer {layer} Progress",
                    unit="image", position=1, leave=True
                )

            # Pass the command to handle_capture
            self.handle_capture(layer, sections)
        else:
            print(f"[WARNING] Unknown command received: {command}")
