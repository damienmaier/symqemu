import pathlib

import util
import shutil

TEST_CASES_DIR = pathlib.Path('/tmp/concolic_test_cases')

if __name__ == '__main__':

    shutil.rmtree(TEST_CASES_DIR, ignore_errors=True)
    TEST_CASES_DIR.mkdir(parents=True)

    NEW_SYMQEMU = pathlib.Path('/home/ubuntu/symqemu-new-version/build/qemu-x86_64')
    OLD_SYMQEMU = pathlib.Path('/home/ubuntu/symqemu/x86_64-linux-user/symqemu-x86_64')

    util.run_symqemu(
        qemu_executable=OLD_SYMQEMU,
        qemu_additional_args= [],
        binary=pathlib.Path('/home/ubuntu/new-symqemu-demo/simple/binary'),
        binary_arguments=[],
        generated_test_cases_output_dir=TEST_CASES_DIR,
        binary_stdin=b'seaa'
    )

    for test_case in TEST_CASES_DIR.iterdir():
        print(test_case)
        print(test_case.read_bytes())
        print()
