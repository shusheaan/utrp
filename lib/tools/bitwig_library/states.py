"""CLAP preset envelopes and sfizz LV2 → VST3 state conversion.

Formats: bitwig/dawproject; sfztools/sfizz-ui SfizzVstState.cpp;
steinbergmedia/vst3_base fstreamer.cpp. sfizz schema version 5.
"""
from __future__ import annotations

import math
import struct

from source import Sound

SFIZZ_ID = 'E8FAB71815ED46E38B5983101E12993F'


def clap_preset(plugin_id: str, state: bytes) -> bytes:
    encoded = plugin_id.encode('utf-8')
    if not encoded or not state:
        raise ValueError('Empty CLAP plugin ID or state')
    return b'clap' + struct.pack('>I', len(encoded)) + encoded + state


def string8(value: str) -> bytes:
    encoded = value.encode('utf-8') + b'\0'
    return struct.pack('<i', len(encoded)) + encoded


def sfizz_component(sound: Sound) -> bytes:
    if sound.sfz is None or sound.scala is None:
        raise ValueError('Missing sfizz sample/tuning path')
    params = dict(sound.parameters)
    expected = {'volume', 'num_voices', 'oversampling', 'preload_size', 'scala_root_key',
                'tuning_frequency', 'stretched_tuning', 'sample_quality', 'oscillator_quality',
                'freewheeling_sample_quality', 'freewheeling_oscillator_quality',
                'sustain_cancels_release'}
    if set(params) != expected:
        raise ValueError(f'Unexpected sfizz parameters: {set(params) ^ expected}')
    oversampling = params['oversampling']
    if oversampling < 1 or math.log2(oversampling) % 1:
        raise ValueError('sfizz oversampling must be a power of two')
    data = struct.pack('<Q', 5) + string8(str(sound.sfz))
    data += struct.pack('<fiii', params['volume'], int(params['num_voices']),
                        int(math.log2(oversampling)), int(params['preload_size']))
    data += string8(str(sound.scala))
    data += struct.pack('<iffiiiihiI', int(params['scala_root_key']), params['tuning_frequency'],
                        params['stretched_tuning'], int(params['sample_quality']),
                        int(params['oscillator_quality']), int(params['freewheeling_sample_quality']),
                        int(params['freewheeling_oscillator_quality']),
                        int(params['sustain_cancels_release']), -1, len(sound.controllers))
    for cc, value in sound.controllers:
        if not 0 <= cc <= 65535 or not 0 <= value <= 1:
            raise ValueError('Invalid sfizz controller')
        data += struct.pack('<Hf', cc, value)
    return data


def vst3_preset(plugin_id: str, component: bytes) -> bytes:
    if len(plugin_id) != 32:
        raise ValueError('VST3 class ID must contain 32 hex characters')
    bytes.fromhex(plugin_id)
    header_size = 48
    header = b'VST3' + struct.pack('<i', 1) + plugin_id.encode('ascii')
    header += struct.pack('<q', header_size + len(component))
    listing = b'List' + struct.pack('<i', 1) + b'Comp'
    listing += struct.pack('<qq', header_size, len(component))
    return header + component + listing
