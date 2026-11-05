import struct

with open("users.tbl", "rb") as f:
    while row := f.read(16):
        id_, age, name = struct.unpack("<ii8s", row)
        print(id_, age, name.rstrip(b"\x00").decode())