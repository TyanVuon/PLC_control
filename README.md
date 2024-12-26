```markdown
# PLC File: Inspection.gx3

### Details
- **Date:** Dec 19, 14:32  
- **Revised:**  
  - Dec 24, 13:00  
  - Dec 25, 12:00  

---

## Activate Virtual Environment (`ctrl`)
To activate the virtual environment, run the following command:

```bash
~/repository/Ctrl-dev/ source ctrl/bin/activate
```

---

## Run Docker Container
To run the container, execute:

```bash
~/repository/Ctrl-dev/ sudo docker run -it ctrl_image /bin/bash
```

---

## Virtual PLC Setup
**To be used with `comMergeCtrl.py` for non-PLC testing.**

1. **Create COM1 <-> COM2 Pair:**  
   Use HHD Virtual Serial Port Tools to create a virtual COM port pair.

2. **Adjust Camera/Serial Address:**  
   Update the addresses for **Ubuntu** to **Windows** compatibility.

3. **Set Up Serial_Controller.py:**  
   Ensure the script is listening to `COM2` for proper communication.

--- 


```