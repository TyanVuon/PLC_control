import serial
import struct
import time

# Open the serial port for sending data (use the appropriate Linux device file)
ser = serial.Serial('/dev/pts/5', baudrate=9600, parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)

# Define the layers and sections
layers = [1, 8, 12, 18, 24, 30, 36, 40, 45, 60, 60]  # Sections per layer

def format_and_send(command, layer_count, section_count):
    """Format and send the data via serial port."""
    try:
        # Convert integers to 16-bit Little Endian bytes
        command_bytes = struct.pack('<H', command)          # e.g., 400 -> 90 01
        layer_bytes = struct.pack('<H', layer_count)        # Layer count
        section_bytes = struct.pack('<H', section_count)    # Section count

        # Merge the bytes and append \r\n
        full_data = command_bytes + layer_bytes + section_bytes + b'\r\n'

        # Send the data
        ser.write(full_data)
        print(f"Sent: CMD={command}, LAY={layer_count}, SEC={section_count} -> Bytes: {full_data.hex()}")
    except Exception as e:
        print(f"[ERROR] Failed to send data: {e}")

def automate_sending(command, layers):
    """Automate sending data for the defined layers and sections."""
    for layer_index, total_sections in enumerate(layers, start=1):  # Layer index starts at 1
        for section_count in range(1, total_sections + 1):          # Section count starts at 1
            format_and_send(command, layer_index, section_count)    # Correct order: Layer first, Section second
            time.sleep(1)  # Add a 1-second delay between sends

        print(f"[INFO] Completed Layer {layer_index} with {total_sections} sections.\n")

    # Dynamically calculate final layer and section
    final_command = 700
    final_layer = len(layers)  # The last layer index
    final_section = layers[-1]  # The last section count in the final layer
    format_and_send(final_command, final_layer, final_section)
    print(f"[INFO] Final command sent: CMD=700, LAY={final_layer}, SEC={final_section}.")


try:
    print("Starting automated VirtualPLC...")
    command = 400  # Fixed command value
    automate_sending(command, layers)

except KeyboardInterrupt:
    print("\n[INFO] Stopped by user.")
finally:
    ser.close()
    print("Serial port closed.")