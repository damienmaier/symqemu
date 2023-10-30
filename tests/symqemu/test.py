import filecmp
import pathlib
import shutil
import subprocess
import unittest
import util


class SymQemuTests(unittest.TestCase):
    SYMQEMU_OUTPUT_DIR = pathlib.Path(__file__).parent / "symqemu_output"

    def setUp(self):
        self.SYMQEMU_OUTPUT_DIR.mkdir()

    def tearDown(self):
        shutil.rmtree(self.SYMQEMU_OUTPUT_DIR)

    def test_simple(self):

        util.run_symqemu_on_test_binary(binary_name='simple', output_dir=self.SYMQEMU_OUTPUT_DIR)

        expected_vs_actual_output_comparison = filecmp.dircmp(self.SYMQEMU_OUTPUT_DIR, util.BINARIES_DIR / 'simple' / 'expected_outputs')
        self.assertEqual(expected_vs_actual_output_comparison.diff_files, [])
        self.assertEqual(expected_vs_actual_output_comparison.left_only, [])
        self.assertEqual(expected_vs_actual_output_comparison.right_only, [])
        self.assertEqual(expected_vs_actual_output_comparison.funny_files, [])
