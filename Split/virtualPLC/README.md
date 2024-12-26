```markdown

## Virtual PLC Setup
> ⚠ **Note:** Cannot be used through SSH unless HostPC has COM pair setup beforehand.

1. **Create COM1 <-> COM2 Pair**
   - Use **HHD Virtual Serial Port Tools** to create the pair.

2. **Adjust Camera/Serial Address**
   - Modify the configuration to match between Ubuntu and Windows.

3. **Make `Serial_Controller` Listen**
   - Configure it to listen to `COM2`.
```

