import pathlib
import subprocess
import symcctrace
import pickle

SYMQEMU_RUN_STDOUT_STDERR = pathlib.Path('/tmp/symqemu_stdout_stderr')
SYMQEMU_EXECUTABLE = pathlib.Path(__file__).parent.parent.parent / "build" / "x86_64-linux-user" / "qemu-x86_64"
BINARIES_DIR = pathlib.Path(__file__).parent / "binaries"


def run_symqemu(
        qemu_executable: pathlib.Path,
        qemu_additional_args: list[str],
        binary: pathlib.Path,
        binary_arguments: list[str],
        generated_test_cases_output_dir: pathlib.Path,
        symbolized_input_file: pathlib.Path = None,
        binary_stdin=None,
):
    command = str(qemu_executable), *qemu_additional_args, str(binary), *binary_arguments

    environment_variables = {'SYMCC_OUTPUT_DIR': str(generated_test_cases_output_dir)}
    if symbolized_input_file is not None:
        environment_variables['SYMCC_INPUT_FILE'] = str(symbolized_input_file)

    print(f'about to run command: {" ".join(command)}')
    print(f'with environment variables: {environment_variables}')

    with open(SYMQEMU_RUN_STDOUT_STDERR, 'w') as f:
        subprocess.run(
            command,
            env=environment_variables,
            stdout=f,
            stderr=subprocess.STDOUT,
            input=binary_stdin
        )



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

    def replace_placeholder_with_input(arg: str) -> str:
        return str(binary_dir / 'input') if arg == '@@' else arg

    binary_args = list(map(replace_placeholder_with_input, binary_args))

    run_symqemu(
        qemu_executable=qemu_executable,
        qemu_additional_args=additional_args.split(' '),
        binary=binary_dir / 'binary',
        binary_arguments=binary_args,
        generated_test_cases_output_dir=generated_test_cases_output_dir,
        symbolized_input_file=binary_dir / 'input',
    )


BACKEND_TRACE_FILE = pathlib.Path('/tmp/backend_trace.json')
SYMQEMU_TRACE_ADDRESSES_FILE = pathlib.Path('/tmp/symqemu_addresses.json')


def run_symqemu_and_save_trace_data(
        binary_name: str,
        qemu_executable: pathlib.Path,
        destination_directory: pathlib.Path,
        qemu_additional_args: str = '',
) -> None:
    # Make sure that we will get an error if the files are not created
    BACKEND_TRACE_FILE.unlink(missing_ok=True)
    SYMQEMU_TRACE_ADDRESSES_FILE.unlink(missing_ok=True)
    SYMQEMU_RUN_STDOUT_STDERR.unlink(missing_ok=True)

    run_symqemu_on_test_binary(
        binary_name=binary_name,
        qemu_executable=qemu_executable,
        additional_args=qemu_additional_args,

    )
    trace_data = symcctrace.parse_trace(trace_file=BACKEND_TRACE_FILE,
                                        memory_region_names_file=SYMQEMU_TRACE_ADDRESSES_FILE)

    with open(destination_directory / 'trace.pickle', 'wb') as f:
        pickle.dump(trace_data, f)

    SYMQEMU_RUN_STDOUT_STDERR.rename(destination_directory / 'stdout_stderr.txt')
