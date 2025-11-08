import pathlib

from qibolab import ConfigKinds
from qibolab._core.pulses import Pulse, Readout, Drag, Acquisition, Rectangular
from qibolab._core.components.configs import IqConfig, DcConfig
from qibolab._core.parameters import Parameters, Settings, NativeGates
from qibolab._core.native import SingleQubitNatives, Native
from qibolab._core.instruments.keysight.components import QcsAcquisitionConfig

ConfigKinds.extend([QcsAcquisitionConfig])
ROOT = pathlib.Path(__file__).parent

readout_frequency_maps = {
    0: 4.955e9,
    1: 5.087e9,
    4: 5.2627e9,
    5: 5.392e9,
    6: 5.515e9,
    16: 5.7135e9,
    11: 5.8355e9,

    2: 4.943e9,
    3: 5.079e9,
    8: 5.252e9,
    9: 5.377e9,
    10: 5.498e9,
    19: 5.721e9,
    15: 5.835e9,

    7: 4.989e9,
    12: 5.165e9,
    13: 5.322e9,
    17: 5.519e9,
    14: 5.665e9,
    18: 5.9e9
}


config = {}
natives = {}
for qubit_id in range(20):
    config[f"{qubit_id}/drive"] = IqConfig(frequency=int(4.35e9))
    config[f"{qubit_id}/probe"] = IqConfig(frequency=int(readout_frequency_maps[qubit_id]))
    config[f"{qubit_id}/acquisition"] = QcsAcquisitionConfig(delay=0, smearing=0)
    config[f"{qubit_id}/flux"] = DcConfig(offset=0)
    natives[qubit_id] = SingleQubitNatives(
        RX=Native([
            (f"{qubit_id}/drive", Pulse(duration=50, amplitude=0.2, envelope=Drag(rel_sigma=2, beta=0)))
        ]),
        MZ=Native([
            (f"{qubit_id}/acquisition", Readout(
                acquisition=Acquisition(duration=2000),
                probe=Pulse(duration=2000, amplitude=0.1, envelope=Rectangular())))
        ])
    )

params = Parameters(
    settings=Settings(relaxation_time=50000),
    configs=config,
    native_gates=NativeGates(single_qubit=natives)
)

(ROOT / "parameters.json").write_text(params.model_dump_json(indent=4))

