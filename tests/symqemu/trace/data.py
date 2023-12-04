import dataclasses
import enum
import functools
import itertools
import json
import math
import pathlib
import pickle

import cattrs

import util


class SymbolKind(enum.Enum):
    BOOL = 0
    CONSTANT = 1
    READ = 2
    CONCAT = 3
    EXTRACT = 4
    ZEXT = 5
    SEXT = 6
    ADD = 7
    SUB = 8
    MUL = 9
    UDIV = 10
    SDIV = 11
    UREM = 12
    SREM = 13
    NEG = 14
    NOT = 15
    AND = 16
    OR = 17
    XOR = 18
    SHL = 19
    LSHR = 20
    ASHR = 21
    EQUAL = 22
    DISTINCT = 23
    ULT = 24
    ULE = 25
    UGT = 26
    UGE = 27
    SLT = 28
    SLE = 29
    SGT = 30
    SGE = 31
    LOR = 32
    LAND = 33
    LNOT = 34
    ITE = 35
    ROL = 36
    ROR = 37
    INVALID = 38


@dataclasses.dataclass
class Operation:
    kind: SymbolKind
    properties: dict


@dataclasses.dataclass
class RawSymbol:
    operation: Operation
    size_bits: int
    input_byte_dependency: list[int]
    args: list[str]


@dataclasses.dataclass
class RawTraceStep:
    pc: int
    memory_to_symbol_mapping: dict[str, str]


@dataclasses.dataclass
class RawPathConstraint:
    symbol: str
    after_step: int
    new_input_value: list[int] | None


@dataclasses.dataclass
class RawTraceData:
    trace: list[RawTraceStep]
    symbols: dict[str, RawSymbol]
    path_constraints: list[RawPathConstraint]


@dataclasses.dataclass
class Symbol:
    operation: Operation
    size_bits: int
    input_byte_dependency: list[int]
    args: list['Symbol']


@dataclasses.dataclass
class TraceStep:
    pc: int
    memory_to_symbol_mapping: dict[str, Symbol]


@dataclasses.dataclass
class PathConstraint:
    symbol: Symbol
    after_step: TraceStep
    new_input_value: bytes | None


@dataclasses.dataclass
class MemoryArea:
    address: int
    name: str


@dataclasses.dataclass
class TraceData:
    trace: list[TraceStep]
    symbols: dict[str, Symbol]
    path_constraints: list[PathConstraint]
    debug_text: str
    memory_areas: list[MemoryArea]


MEMORY_AREA_MAX_DISTANCE = 0x100000
BACKEND_TRACE_FILE = pathlib.Path('/tmp/backend_trace.json')
SYMQEMU_TRACE_ADDRESSES_FILE = pathlib.Path('/tmp/symqemu_addresses.json')


def convert_operation(raw_operation: Operation, size_bits: int) -> Operation:
    operation = Operation(
        kind=SymbolKind(raw_operation.kind),
        properties=raw_operation.properties
    )

    if 'value' in operation.properties:
        operation.properties['value'] = int(operation.properties['value']).to_bytes(math.ceil(size_bits / 8), 'little')

    return operation


def convert_symbols(raw_symbols: dict[str, RawSymbol]) -> dict[str, Symbol]:
    symbols = {}

    def recursively_create_symbol(symbol_id: str):
        if symbol_id in symbols:
            return symbols[symbol_id]

        raw_symbol = raw_symbols[symbol_id]
        args = [recursively_create_symbol(arg) for arg in raw_symbol.args]

        symbol = Symbol(
            operation=convert_operation(raw_symbol.operation, raw_symbol.size_bits),
            args=args,
            input_byte_dependency=raw_symbol.input_byte_dependency,
            size_bits=raw_symbol.size_bits
        )
        symbols[symbol_id] = symbol
        return symbol

    for symbol_id in raw_symbols:
        recursively_create_symbol(symbol_id)

    return symbols


def raw_memory_address_to_named_location(raw_memory_address: int, memory_areas: list[MemoryArea]) -> str:
    def distance(memory_area: MemoryArea) -> int:
        return raw_memory_address - memory_area.address

    def is_candidate(memory_area: MemoryArea) -> bool:
        return \
            abs(distance(memory_area)) < MEMORY_AREA_MAX_DISTANCE \
                if memory_area.name == 'stack' \
                else 0 <= distance(memory_area) < MEMORY_AREA_MAX_DISTANCE

    def absolute_distance(memory_area: MemoryArea) -> int:
        return abs(distance(memory_area))

    closest_memory_area = min(filter(is_candidate, memory_areas), key=absolute_distance)

    return f'{closest_memory_area.name}+{hex(distance(closest_memory_area))}'


def convert_trace_step(raw_trace_step: RawTraceStep, symbols: dict[str, Symbol],
                       memory_areas: list[MemoryArea]) -> TraceStep:
    def convert_mapping(mapping: dict[str, str]) -> dict[str, Symbol]:
        def convert_mapping_element(raw_address: str, symbol_id: str) -> tuple[str, Symbol]:
            return raw_memory_address_to_named_location(int(raw_address), memory_areas), symbols[symbol_id]

        return dict(itertools.starmap(convert_mapping_element, mapping.items()))

    return TraceStep(
        pc=raw_trace_step.pc,
        memory_to_symbol_mapping=convert_mapping(raw_trace_step.memory_to_symbol_mapping)
    )


def convert_path_constraint(raw_path_constraint: RawPathConstraint, symbols: dict[str, Symbol],
                            trace_steps: list[TraceStep]) -> PathConstraint:
    return PathConstraint(
        symbol=symbols[raw_path_constraint.symbol],
        after_step=trace_steps[raw_path_constraint.after_step],
        new_input_value=bytes(
            raw_path_constraint.new_input_value) if raw_path_constraint.new_input_value is not None else None
    )


def build_data(
        binary_name: str,
        qemu_executable: pathlib.Path,
        pickle_destination_file: pathlib.Path,
        additional_qemu_args: str = ''
) -> TraceData:
    # Make sure that we will get an error if the files are not created
    BACKEND_TRACE_FILE.unlink(missing_ok=True)
    SYMQEMU_TRACE_ADDRESSES_FILE.unlink(missing_ok=True)
    util.SYMQEMU_RUN_STDOUT_STDERR.unlink(missing_ok=True)

    util.run_symqemu_on_test_binary(
        binary_name=binary_name,
        qemu_executable=qemu_executable,
        additional_args=additional_qemu_args
    )

    with open(BACKEND_TRACE_FILE) as file:
        raw_trace_data = cattrs.Converter(forbid_extra_keys=True).structure(json.load(file), RawTraceData)

    with open(SYMQEMU_TRACE_ADDRESSES_FILE) as file:
        def convert_to_memory_area(raw_memory_area: dict[str, str]) -> MemoryArea:
            return cattrs.Converter(forbid_extra_keys=True).structure(raw_memory_area, MemoryArea)

        memory_areas = list(map(convert_to_memory_area, json.load(file)))

    symbols = convert_symbols(raw_trace_data.symbols)
    trace_steps = list(
        map(functools.partial(convert_trace_step, symbols=symbols, memory_areas=memory_areas), raw_trace_data.trace))
    path_constraints = list(map(functools.partial(convert_path_constraint, symbols=symbols, trace_steps=trace_steps),
                                raw_trace_data.path_constraints))

    trace_data = TraceData(
        trace=trace_steps,
        symbols=symbols,
        path_constraints=path_constraints,
        debug_text=util.SYMQEMU_RUN_STDOUT_STDERR.read_text(),
        memory_areas=memory_areas
    )

    with open(pickle_destination_file, 'wb') as file:
        pickle.dump(trace_data, file)
