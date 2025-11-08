import pathlib
import keysight.qcs as qcs

print(qcs.__version__)
FOLDER = pathlib.Path(__file__).parent

n_qubits = 6

qubit_readout_line_mapping = {
    #1: 1,
    #2: 1,
    3: 2,
    4: 2,
    #5: 1,
    #6: 1,
    #7: 1,
    8: 3,
    9: 2,
    #10: 2,
    #11: 2,
    #12: 1,
    13: 3,
    14: 3,
    #15: 3,
    #16: 2,
    #17: 1,
    #18: 3,
    #19: 3,
    #20: 2
}
qubit_xy_line_mapping = {
    3: (1, 15, 3),
    4: (1, 15, 4),
    8: (1, 13, 4),
    9: (1, 11, 1),
    13: (1, 8, 1),
    14: (1, 8, 2)
}

qubit_flux_mapping = {
    4: (1, 3, 2),
    8: (1, 3, 1),
    14: (1, 3, 4)
}

tc_flux_mapping = {
    "tc4-9": (1, 3, 3),
    "tc3-4": (1, 2, 3),
    "tc3-8": (1, 2, 2),
    "tc8-13": (1, 2, 1),
    "tc13-14": (1, 2, 4)
}

#qubits_avail = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 17]

xy_slot = [15, 13, 11, 8, 6]
bb_slot = [2, 3]
readout_awg_slot = 4
readout_downconverter_slot = 17
readout_digitizer_slot = 18
num_fastflux_lines = 8

xy_awgs = qcs.Channels(range(n_qubits), "xy_channels", absolute_phase=False)
digs = qcs.Channels(range(n_qubits), "readout_acquisition", absolute_phase=True)
readout_awgs = qcs.Channels(range(n_qubits), "readout_channels", absolute_phase=True)
qubit_flux_awgs = qcs.Channels(range(len(qubit_flux_mapping)), "qb_flux_channels", absolute_phase=False)
tc_flux_awgs = qcs.Channels(range(len(tc_flux_mapping)), "tc_flux_channels", absolute_phase=False)

readout_awg_address = [qcs.Address(1, readout_awg_slot, channel) for channel in qubit_readout_line_mapping.values()]
xy_awg_address = [qcs.Address(*addr) for addr in qubit_xy_line_mapping.values()]
dig_address = [qcs.Address(1, readout_digitizer_slot, channel) for channel in qubit_readout_line_mapping.values()]
dnc_address = [qcs.Address(1, readout_downconverter_slot, channel) for channel in qubit_readout_line_mapping.values()]
qubit_flux_address = [qcs.Address(*addr) for addr in qubit_flux_mapping.values()]
tc_flux_address = [qcs.Address(*addr) for addr in tc_flux_mapping.values()]

channel_mapper = qcs.ChannelMapper(ip_address="192.168.0.80")

channel_mapper.add_channel_mapping(xy_awgs, xy_awg_address, qcs.InstrumentEnum.M5300AWG)
channel_mapper.add_channel_mapping(readout_awgs, readout_awg_address, qcs.InstrumentEnum.M5300AWG)
channel_mapper.add_channel_mapping(digs, dig_address, qcs.InstrumentEnum.M5200Digitizer)
channel_mapper.add_channel_mapping(qubit_flux_awgs, qubit_flux_address, qcs.InstrumentEnum.M5301AWG)
channel_mapper.add_channel_mapping(tc_flux_awgs, tc_flux_address, qcs.InstrumentEnum.M5301AWG)

channel_mapper.add_downconverters(dig_address, dnc_address)

# order of arguments has changed
channel_mapper.set_lo_frequencies([(1, readout_awg_slot, chan) for chan in range(2, 4)]
                                  + [(1, readout_downconverter_slot, chan) for chan in range(2, 4)],
                                  4.9e9)
channel_mapper.set_lo_frequencies(xy_awg_address, 3.8e9)

# set the digitizer range
for chan in range(2, 4):
    dig_channel = channel_mapper.get_physical_channel((1, readout_digitizer_slot, chan))
    #dig_channel.settings.range.value = 0.045

""" for addr in tc_flux_mapping.values():
    bb_channel = channel_mapper.get_physical_channel(addr)
    bb_channel.settings.offset.value = 0.12
"""
qcs.save(channel_mapper, FOLDER / "chan_map.qcs")
