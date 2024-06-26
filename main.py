import json
import itertools
import os
from enum import Enum
from typing import List
from metrics import base
from keyboard import *
from metric import *

class KeymeowEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Pos):
            return {"row": o.row, "col": o.col, "layer": o.layer}
        if isinstance(o, Finger):
            return o.name
        if isinstance(o, KeyCoord):
            return {"pos": o.pos, "x": o.x, "y": o.y, "finger": o.finger.name}
        if isinstance(o, Keyboard):
            return {"name": o.name, "keys": {"map": o.keymap}, "combos": o.combos}
        if isinstance(o, Nstroke):
            return o.nstroke
        if isinstance(o, NstrokeType):
            return o.name[0]
        if isinstance(o, NgramType):
            return o.name.capitalize()
        if isinstance(o, NstrokeData):
            return [o.nstroke, o.amounts]
        if isinstance(o, Metric):
            return {"name": o.name, "short": o.short, "ngram_type": o.ngram_type}
        if isinstance(o, MetricAmount):
            return [o.metric, o.amount]
        if isinstance(o, MetricData):
            return {"metrics": o.metrics, "strokes": o.strokes, "keyboard": o.keyboard}
        if isinstance(o, Combo):
            return {"coords": o.coords}
        print(o)
        return super().default(o)

def encode_metricdata(o):
    if isinstance(o, Pos):
        return {"row": o.row, "col": o.col, "layer": o.layer}
    if isinstance(o, Finger):
        return o.name
    if isinstance(o, KeyCoord):
        return {"pos": o.pos, "x": o.x, "y": o.y, "finger": o.finger.name}
    if isinstance(o, Keyboard):
        return {"name": o.name, "keys": {"map": o.keymap}, "combos": o.combos}
    if isinstance(o, Nstroke):
        return o.nstroke
    if isinstance(o, NstrokeType):
        return o.name[0]
    if isinstance(o, NgramType):
        return o.name.capitalize()
    if isinstance(o, NstrokeData):
        return [o.nstroke, o.amounts]
    if isinstance(o, Metric):
        return {"name": o.name, "short": o.short, "ngram_type": o.ngram_type}
    if isinstance(o, MetricAmount):
        return [o.metric, o.amount]
    if isinstance(o, MetricData):
        return {"metrics": o.metrics, "strokes": o.strokes, "keyboard": o.keyboard}
    if isinstance(o, Combo):
        return {"coords": o.coords}
    print(o)
    return super().default(o)
    
NstrokeType = Enum("NstrokeType", ["MONOSTROKE", "BISTROKE", "TRISTROKE"])

class Nstroke:
    def __init__(self, kind: NstrokeType, nstroke: List[int]):
        self.kind = kind
        self.nstroke = nstroke

class MetricAmount:
    def __init__(self, metric: int, amount: float):
        self.metric = metric
        self.amount = amount

class NstrokeData:
    def __init__(self, nstroke: Nstroke, amounts: List[MetricAmount]):
        self.nstroke = nstroke
        self.amounts = amounts

def has_combo(keys):
    return True in [isinstance(key, Combo) for key in keys]

class MetricData:
    def __init__(self, metrics: List[Metric], kb: Keyboard):
        self.metrics = metrics
        self.strokes = []
        self.nstrokes_measured = 0
        self.nstrokes_matched = 0
        self.keyboard = kb

        bimetrics = [(idx, m) for (idx, m) in enumerate(metrics) if m.ngram_type in [NgramType.BIGRAM, NgramType.SKIPGRAM]]
        trimetrics = [(idx, m) for (idx, m) in enumerate(metrics) if m.ngram_type == NgramType.TRIGRAM]

        for size in [2, 3]:
            for nstroke in itertools.product(enumerate(list(kb.compound_nstrokes())), repeat=size):
                kind = NstrokeType.TRISTROKE if size == 3 else NstrokeType.BISTROKE
                ns = [pair[0] for pair in nstroke] # real nstroke being the indexes of keys
                keys = [pair[1] for pair in nstroke] # key data for metrics
                data = NstrokeData(Nstroke(kind, ns), [])
                for idx, m in bimetrics if size == 2 else trimetrics:
                    self.nstrokes_measured += 1
                    a = keys[0]
                    b = keys[1]
                    is_static_val = isinstance(m.value, int)
                    matches = False
                    value = 0
                    if size == 2:
                        if m.splittable and has_combo(keys):
                            split = split_strokes(a, b)
                            for (x, y) in split:
                                if m.predicate(x, y):
                                    matches = True
                                    value += m.value(x, y) if not is_static_val else m.value
                        else:
                            matches = m.predicate(a, b)
                            value = m.value(a, b) if not is_static_val else 0
                    else:
                        if not m.splittable:
                            c = keys[2]
                            matches = m.predicate(a, b, c)
                            value = m.value(a, b, c) if not is_static_val else 0
                        else:
                            print("Warning: tristroke metrics cannot be automatically split")
                    if not matches:
                        continue
                    self.nstrokes_matched += 1
                    if not value:
                        if not is_static_val:
                            continue
                        value = m.value
                    data.amounts.append(MetricAmount(idx, value))
                if data.amounts:
                    self.strokes.append(data)

def check_keyboard(kb: Keyboard):
    for (finger, keys) in enumerate(kb.keymap):
        for key in keys:
            if finger != key.finger.value:
                print(f"WARNING: keyboard {kb.name} has key with finger {key.finger} in {Finger(finger)} list")

    for combo in kb.combos:
        for ckey in combo.coords:
            contained = any(map(lambda p: p.row == ckey.pos.row and p.col == ckey.pos.col, [k.pos for keys in kb.keymap for k in keys]))
            if not contained:
                print(f"WARNING: keyboard {kb.name} has combo involving nonexistent key ({ckey.pos.col}, {ckey.pos.row})")
                
            

from keyboard_metrics import KEYBOARDS
import time
import msgpack

total_evaluated = 0
total_matched = 0
start = time.time()

for (k, _) in KEYBOARDS:
    check_keyboard(k)
for (k, m) in KEYBOARDS:
    print(f"Exporting {k.name} ({len(list(k.compound_nstrokes()))} keys)...", end="", flush=True)
    data = MetricData(m, k)
    total_evaluated += data.nstrokes_measured
    total_matched += data.nstrokes_matched
    packed = msgpack.packb(data, default=encode_metricdata)
    f = open(os.path.join("./export/", k.name + ".metrics"), "wb")
    f.write(packed)
    f.close()
    print(f" done ({round(100 * data.nstrokes_matched / data.nstrokes_measured)}%)")

elapsed = time.time() - start
print(f"Evaluated {total_evaluated} nstrokes in {elapsed:.2f} seconds ({round(total_evaluated/elapsed)} per second)")
print(f"{round(100 * total_matched / total_evaluated)}% of nstrokes matched a metric")

#generate_metrics(ansi, base.METRIC_LIST)
