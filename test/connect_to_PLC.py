import serial
import time

def main():
    # Match the parameters to your SerialController settings
    port_name = '/dev/ttyUSB0'  # Update to the correct port if needed
    baudrate = 9600
    parity = serial.PARITY_ODD
    stopbits = serial.STOPBITS_ONE
    bytesize = serial.EIGHTBITS
    timeout = 1

    try:
        # Initialize serial connection
        ser = serial.Serial(
            port=port_name,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=timeout,
            rtscts=False,
            xonxoff=False
        )

        if ser.is_open:
            print(f"Serial port {port_name} successfully opened.")
        else:
            print(f"Failed to open serial port {port_name}.")
            return

        print("Listening for data from PLC...")
        while True:
            try:
                # Read data until termination sequence '\r\n' and strip last two bytes
                raw_data = ser.read_until(b'\r\n')[:-2]
                if raw_data:
                    # Display the raw byte stream for debugging
                    print(f'[DEBUG] Raw byte stream: {raw_data.hex(" ")}')

                    # Ensure the length of the data is valid (multiple of 2 bytes for 16-bit words)
                    if len(raw_data) % 2 == 0 and len(raw_data) >= 6:
                        # Split the raw data into 16-bit chunks
                        words = [int.from_bytes(raw_data[i:i+2], byteorder='little') for i in range(0, len(raw_data), 2)]

                        command, layer, sections = words[0], words[1], words[2]
                        print(f"Merged Decimal: {command:04d}{layer:02d}{sections:02d}")
                    else:
                        print("[ERROR] Incomplete 16-bit data received. Discarding data.")
                else:
                    print("[INFO] No data received.")
                time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n[INFO] Program interrupted by user.")
                break

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    main()
