import json
import struct

with open("users.tbl", "wb") as f:
    f.write(struct.pack("<ii8s", 1, 30, b"bob"))
    f.write(struct.pack("<ii8s", 2, 25, b"alice"))
    f.write(struct.pack("<ii8s", 3, 41, b"joni"))

catalog = {
    "tables": {
        "users": {
            "file": "users.tbl",
            "columns": [
                {"name": "id", "type": "int", "size": 4},
                {"name": "age", "type": "int", "size": 4},
                {"name": "name", "type": "char", "size": 8},
            ],
        }
    }
}

with open("catalog.json", "w") as f:
    json.dump(catalog, f, indent=4)
