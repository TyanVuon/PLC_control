import serial
import time

class SerialController:
    def __init__(self, port_name='/dev/ttyUSB0', baudrate=9600, parity=serial.PARITY_ODD,
                 stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1,
                 rtscts=False, xonxoff=False):
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
                    print(f"Serial port {port_name} successfully opened.")
                    return ser
            except Exception as e:
                print(f"[ERROR] Attempt {attempt + 1}: {e}")
                time.sleep(1)
        return None

    def write_data(self, data):
        try:
            self.serial_port.write(data.to_bytes(2, byteorder='little'))
            #print(f"Sent data: {data}")
        except Exception as e:
            print(f"[ERROR] Failed to send data: {e}")

    def read_data(self):
        """Read and parse incoming 16-bit words, using the first word as the command."""
        try:
            # Read data until the termination sequence '\r\n' and strip the last two bytes
            raw_data = self.serial_port.read_until(b'\r\n')[:-2]

            if raw_data:
                # Display the raw byte stream for debugging
                print(f'[DEBUG] Raw byte stream: {raw_data.hex(" ")}')

                # Handle bc02 ENDING 
                if len(raw_data) == 2:
                    command = int.from_bytes(raw_data, byteorder='little')
                    print(f"Finish received from PLC: {command}")
                    return command, None, None 

                # Ensure the length of the data is valid (multiple of 2 bytes for 16-bit words)
                if len(raw_data) % 2 != 0 or len(raw_data) < 6:
                    print("[ERROR] Incomplete 16-bit data received. Discarding data.")
                    return None, None, None

                # Split the raw data into 16-bit chunks
                words = [int.from_bytes(raw_data[i:i+2], byteorder='little') for i in range(0, len(raw_data), 2)]


                #print desired format
                command = words[0]  # Command
                layer = words[1]  # Layer
                sections = words[2]  # Sections

                print(f"Merged Decimal: {command:04d}{layer:02d}{sections:02d}")
             

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
