```markdown
# Project Setup Documentation

## PLC File
- **Name:** `Inspection.gx3`
- **Data:** `Dec 19, 14:32`
- **Revised:**
  - `Dec 24, 13:00`
  - `Dec 25, 12:00`

## Activate Virtual Environment `ctrl`

```bash
source ctrl/bin/activate
```

## Run Container

```bash
sudo docker run -it ctrl_image /bin/bash
```

## Virtual PLC Setup
> ⚠ **Note:** Cannot be used through SSH unless HostPC has virtual COM pair setup beforehand. / COM does not run natively on Linux so below shows a workaround

### **1. Install `socat`**

`socat` is a versatile networking tool that can create virtual serial port pairs on your Ubuntu system. Follow these steps to install and configure `socat` for your project.

1. **Update Package Lists:**

   ```bash
   sudo apt update
   ```

2. **Install `socat`:**

   ```bash
   sudo apt install socat
   ```

### **2. Create a Pair of Virtual Serial Ports**

Using `socat`, you can create two interconnected virtual serial ports that simulate a physical serial connection between two applications.

1. **Run `socat` to Create Virtual Ports:**

   Open a terminal and execute the following command:

   ```bash
   socat -d -d PTY,raw,echo=0 PTY,raw,echo=0
   ```

   **Explanation:**
   - `-d -d`: Enables verbose logging to display the created PTY device names.
   - `PTY,raw,echo=0`: Creates a pseudo-terminal (PTY) in raw mode without echoing input back.

2. **Sample Output:**

   ```
   2024/12/27 16:56:07 socat[465512] N PTY is /dev/pts/5
   2024/12/27 16:56:07 socat[465512] N PTY is /dev/pts/24
   2024/12/27 16:56:07 socat[465512] N starting data transfer loop with FDs [5,5] and [7,7]
   ```

   - **Port 1:** `/dev/pts/5`
   - **Port 2:** `/dev/pts/24`

3. **Keep `socat` Running:**

   - **Foreground Mode:** Keep the terminal open to maintain the connection.
   - **Background Mode:** Run `socat` in the background to free up the terminal.

     ```bash
     socat -d -d PTY,raw,echo=0 PTY,raw,echo=0 &
     ```

     **Note:** The `&` at the end runs `socat` as a background process.

4. **Terminate `socat`:**

   If you need to stop `socat`, use the `kill` command with the process ID (PID) displayed in the output or by listing running `socat` processes.

   ```bash
   pkill socat
   ```

### **3. Configure Python Scripts to Use Virtual Ports**

