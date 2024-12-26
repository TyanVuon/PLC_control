PLC file: Inspection.gx3
data:dec19 14:32
revised:dec24 13:00
revised:dec25 12:00

Activate Virtual Environment ctrl: 
~/repository/Ctrl-dev/ source ctrl/bin/activate

Run container:
~/repository/Ctrl-dev/ sudo docker run -it ctrl_image /bin/bash

Virtual PLC Setup (To be used with comMergeCtrl.py for non PLC testing)
1.Create COM1 <-> COM2 pair using HHD Virtual Serial Port Tools
2.Adjust Camera/Serial address from UBUNTU to Windows
3.Make Serial_Controller.py listening to COM2 
