import argparse
import json
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).parent.parent))

import util

BACKEND_TRACE_FILE = pathlib.Path('/tmp/backend_trace.json')
SYMQEMU_TRACE_ADDRESSES_FILE = pathlib.Path('/tmp/symqemu_addresses.json')
MAX_DISTANCE = 0x10000


def build_trace(binary_name: str, qemu_path: pathlib.Path, output_file_path: pathlib.Path):
    # Make sure that we will get an error if symqemu does not create the trace files
    BACKEND_TRACE_FILE.unlink(missing_ok=True)
    SYMQEMU_TRACE_ADDRESSES_FILE.unlink(missing_ok=True)

    util.run_symqemu_on_test_binary(binary_name=binary_name, qemu_executable=qemu_path, additional_args='-cpu qemu64')

    with open(BACKEND_TRACE_FILE) as file:
        backend_trace = json.load(file)

    with open(SYMQEMU_TRACE_ADDRESSES_FILE) as file:
        symqemu_addresses = json.load(file)

    with open(output_file_path, 'w') as output_file:
        for entry in backend_trace:
            print(f'pc : {hex(entry["pc"])}', file=output_file)
            for address in entry['symbolicAddresses']:

                def distance(area) -> int:
                    return address - area['address']

                def absolute_distance(area) -> int:
                    return abs(distance(area))

                def is_close(area) -> bool:
                    return 0 >= distance(area) >= -MAX_DISTANCE \
                        if area['name'] == 'stack' \
                        else 0 <= distance(area) <= MAX_DISTANCE

                close_areas = list(filter(is_close, symqemu_addresses))
                if close_areas:
                    closest_area = min(close_areas, key=absolute_distance)
                    address_to_print = f'{closest_area["name"]}+{hex(distance(closest_area))}'
                else:
                    address_to_print = hex(address)

                print(f'    {address_to_print}', file=output_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build a trace of an execution of symqemu')
    parser.add_argument('binary', type=str, help='The name of the test binary to run symqemu on')
    parser.add_argument('qemu', type=str, help='Path to qemu executable')
    parser.add_argument('output', type=pathlib.Path, help='Path to output trace file')
    args = parser.parse_args()

    build_trace(binary_name=args.binary, qemu_path=pathlib.Path(args.qemu), output_file_path=pathlib.Path(args.output))
