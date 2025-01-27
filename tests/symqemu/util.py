import pathlib
import subprocess

SYMQEMU_EXECUTABLE = pathlib.Path(__file__).parent.parent.parent / "x86_64-linux-user" / "symqemu-x86_64"
BINARIES_DIR = pathlib.Path(__file__).parent / "binaries"


def run_symqemu_on_test_binary(binary_name: str, output_dir: pathlib.Path) -> None:
    binary_dir = BINARIES_DIR / binary_name

    with open(binary_dir / 'args', 'r') as f:
        binary_args = f.read().strip().split(' ')

    def replace_placeholder_with_input(arg: str):
        return str(binary_dir / 'input') if arg == '@@' else arg

    binary_args = *map(replace_placeholder_with_input, binary_args),

    command = (
                  str(SYMQEMU_EXECUTABLE),
                  str(binary_dir / 'binary'),
              ) + binary_args

    environment_variables = {
        'SYMCC_OUTPUT_DIR': str(output_dir),
        'SYMCC_INPUT_FILE': str(binary_dir / 'input')
    }

    print(f'about to run command: {" ".join(command)}')
    print(f'with environment variables: {environment_variables}')

    subprocess.run(
        command,
        env=environment_variables
    )
