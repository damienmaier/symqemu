import pathlib
import subprocess

SYMQEMU_RUN_STDOUT_STDERR = pathlib.Path('/tmp/symqemu_stdout_stderr')
SYMQEMU_EXECUTABLE = pathlib.Path(__file__).parent.parent.parent / "build" / "x86_64-linux-user" / "qemu-x86_64"
BINARIES_DIR = pathlib.Path(__file__).parent / "binaries"


def run_symqemu_on_test_binary(
        binary_name: str,
        qemu_executable: pathlib.Path = SYMQEMU_EXECUTABLE,
        additional_args: str = None,
        generated_test_cases_output_dir: pathlib.Path = None
) -> None:
    if generated_test_cases_output_dir is None:
        generated_test_cases_output_dir = pathlib.Path('/tmp/symqemu_output')
        generated_test_cases_output_dir.mkdir(exist_ok=True)

    if additional_args is None:
        additional_args = ''

    binary_dir = BINARIES_DIR / binary_name

    with open(binary_dir / 'args', 'r') as f:
        binary_args = f.read().strip().split(' ')

    def replace_placeholder_with_input(arg: str):
        return str(binary_dir / 'input') if arg == '@@' else arg

    binary_args = *map(replace_placeholder_with_input, binary_args),

    command = str(qemu_executable), *additional_args.split(), str(binary_dir / 'binary'), *binary_args

    environment_variables = {
        'SYMCC_OUTPUT_DIR': str(generated_test_cases_output_dir),
        'SYMCC_INPUT_FILE': str(binary_dir / 'input')
    }

    print(f'about to run command: {" ".join(command)}')
    print(f'with environment variables: {environment_variables}')

    with open(SYMQEMU_RUN_STDOUT_STDERR, 'w') as f:
        subprocess.run(
            command,
            env=environment_variables,
            stdout=f,
            stderr=subprocess.STDOUT,
        )
