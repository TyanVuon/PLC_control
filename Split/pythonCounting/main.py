from serial_controller import SerialController
from camera_controller import CameraController
from commands import CommandHandler


def main():
    serial_comm = SerialController(port_name='/dev/ttyUSB0')
    camera = CameraController()
    handler = CommandHandler(serial_comm, camera)

    print("Ready to accept commands. Type 'ready' or 'exit'.")

    try:
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
    except KeyboardInterrupt:
        print("\n[INFO] Program interrupted.")
    finally:
        serial_comm.close()
        camera.release()


if __name__ == "__main__":
    main()
