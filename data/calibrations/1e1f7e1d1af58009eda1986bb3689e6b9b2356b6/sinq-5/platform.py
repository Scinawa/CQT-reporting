import pathlib

from qibolab.platform import Platform
from qibolab.channels import Channel, ChannelMap
from qibolab.instruments.icarusqfpga import *
from qibolab.serialize import (
    load_instrument_settings,
    load_qubits,
    load_runcard,
    load_settings,
)

FOLDER = pathlib.Path(__file__).parent

# XY port to DAC channel mapping
cmap_xyline = {
    # RFSoC DAC channel mapping
        "x1": 3,
        "x2": 13,
        "x3": 8,
        "x4": 5,
        "x5": 0,
}

# Qubit mapping to readout port, XY port
cmap_qubits = {
    0: ["r1", "x1"],
    1: ["r1", "x2"],
    2: ["r1", "x3"],
    3: ["r1", "x4"],
    4: ["r1", "x5"],
}
# RO port to DAC, ADC channel pair mapping
cmap_roline = {"r1": (6, 6)}

NAME = "sinq-5"
ADDRESS = "192.168.0.131"

def create():
    controller = RFSOC_RO("board1", ADDRESS,
                           delay_samples_offset_dac=0,
                           delay_samples_offset_adc=11)

    channels: Dict[str, Channel] = {}

    # XY channel mapping
    for input_port, dac_channel in cmap_xyline.items():
        port = controller.ports(input_port)
        port.dac = dac_channel

        channels[input_port] = Channel(
            name=input_port,
            port=port
        )

    # RO channel mapping
    for input_port, (dac_channel, adc_channel) in cmap_roline.items():
        port = controller.ports(input_port)
        port.dac = dac_channel
        port.adc = adc_channel
        channels[input_port] = Channel(
            name=input_port,
            port=port
        )
    cmap = ChannelMap(channels)
    
    instruments = {controller.name: controller}

    runcard = load_runcard(FOLDER)
    qubits, couplers, pairs = load_qubits(runcard)
    settings = load_settings(runcard)
    instruments = load_instrument_settings(runcard, instruments)

    # Map qubit to its channels
    for qid, q in qubits.items():
        readout_port, xy_port = cmap_qubits[qid]
        q.drive = cmap[xy_port]
        q.readout = cmap[readout_port]

    return Platform(
        NAME,
        qubits,
        pairs,
        instruments,
        settings,
        resonator_type="2D",
        couplers=couplers,
    )
