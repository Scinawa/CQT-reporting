import json
import pathlib

fd = pathlib.Path(__file__).parent / "calibration.json"

with open(fd) as r:
    raw = json.load(r)

for qb in range(4, 20):
    raw["single_qubits"][str(qb)] = raw["single_qubits"]["3"]

fd.write_text(json.dumps(raw, indent=4))
