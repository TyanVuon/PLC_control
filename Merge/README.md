```markdown
# Project Setup Documentation

## PLC File
- **Name:** `Inspection.gx3`
- **Data:** `Dec 19, 14:32`
- **Revised:**
  - `Dec 24, 13:00`
  - `Dec 25, 12:00`

## Activate Virtual Environment `ctrl`
```~/repository/Ctrl-dev$ source ctrl/bin/activate
```

## Run Container
```bash
(ctrl) createch@aidevice:~/repository/Ctrl-dev/Split/PLCCounting$ sudo docker run -it ctrl /bin/bash
```

## Virtual PLC Setup
> ⚠ **Note:** Cannot be used through SSH unless HostPC has COM pair setup beforehand.

1. **Create COM1 <-> COM2 Pair**
   - Use **HHD Virtual Serial Port Tools** to create the pair.

2. **Adjust Camera/Serial Address**
   - Modify the configuration to match between Ubuntu and Windows.

3. **Make `Serial_Controller` Listen**
   - Configure it to listen to `COM2`.
```

