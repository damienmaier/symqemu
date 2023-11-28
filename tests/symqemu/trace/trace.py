import pathlib

import data



new = data.build_data(
    binary_name='printf',
    qemu_executable=pathlib.Path('/home/ubuntu/symqemu-new-version/build/x86_64-linux-user/qemu-x86_64'),
    additional_args='-cpu qemu64 -d op'
)

with open(pathlib.Path(__file__).parent.parent / 'new' / 'stdout_stderr', 'w') as file:
    for step in new.trace:
        print(hex(step.pc), file=file)
