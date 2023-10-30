import pathlib
import subprocess

SYMQEMU_EXECUTABLE = pathlib.Path(__file__).parent.parent.parent / "x86_64-linux-user" / "symqemu-x86_64"
BINARIES_DIR = pathlib.Path(__file__).parent / "binaries"


def run_symqemu_on_test_binary(binary_name: str, output_dir: pathlib.Path) -> None:
    binary_dir = BINARIES_DIR / binary_name

    subprocess.run(
        [
            str(SYMQEMU_EXECUTABLE),
            str(binary_dir / 'binary'),
            str(binary_dir / 'input')
        ],
        env={
            'SYMCC_OUTPUT_DIR': str(output_dir),
            'SYMCC_INPUT_FILE': str(binary_dir / 'input')
        }
    )

