import itertools

import symcctrace
import pathlib
import pickle
import util


def remove_additional_steps(reference_steps: list[symcctrace.data.TraceStep],
                            other_steps: list[symcctrace.data.TraceStep]) -> list[symcctrace.data.TraceStep]:
    class StepsRemovalError(Exception):
        pass

    def generator_function():
        other_steps_iterator = iter(other_steps)
        for reference_step in reference_steps:
            while True:
                try:
                    other_step = next(other_steps_iterator)
                except StopIteration:
                    raise StepsRemovalError("Reference step has no corresponding step in other steps")
                else:
                    if reference_step.pc == other_step.pc:
                        break
                    elif len(other_step.memory_to_symbol_mapping) != 0:
                        raise StepsRemovalError("Attempt to remove step that has symbolic data")

            yield other_step

    return list(generator_function())


def remove_memory_region(
        steps: list[symcctrace.data.TraceStep],
        region_name: str
) -> None:
    def is_not_region(pair: tuple[str, symcctrace.data.Symbol]) -> bool:
        location, _ = pair
        return not location.startswith(region_name)

    for step in steps:
        step.memory_to_symbol_mapping = dict(filter(is_not_region, step.memory_to_symbol_mapping.items()))


def print_steps_to_file(trace_data: symcctrace.TraceData, destination_file: pathlib.Path) -> None:
    with open(destination_file, 'w') as f:
        for step_index, step in enumerate(trace_data.trace):
            for location, symbol in step.memory_to_symbol_mapping.items():
                print(location, file=f)
            for path_constraint in filter(lambda x: x.after_step is step, trace_data.path_constraints):
                print("New path constraint with symbol", file=f)
                print(path_constraint.symbol, file=f)
                print("Taken", path_constraint.taken, file=f)
            print(f"Step index: {step_index}", file=f)
            print(f"PC: {hex(step.pc)}", file=f)
            print("----------------------------------", file=f)


def relative_address(base: str, target: str, trace_data: symcctrace.TraceData) -> int:
    base_address = next(filter(lambda x: x.name == base, trace_data.memory_areas)).address
    target_address = next(filter(lambda x: x.name == target, trace_data.memory_areas)).address
    return target_address - base_address


def missing_path_constraints(left: symcctrace.TraceData, right: symcctrace.TraceData):
    result = []

    right_path_constraints_iterator = iter(right.path_constraints)
    for left_path_constraint in left.path_constraints:

        # print(left_path_constraint.symbol)
        right_path_constraints_iterator, saved_iterator = itertools.tee(right_path_constraints_iterator)
        try:
            while left_path_constraint.symbol != next(right_path_constraints_iterator).symbol:
                pass
        except StopIteration:
            result.append(left_path_constraint)
            right_path_constraints_iterator = saved_iterator

    return result


def symbolic_trace_subset_analysis(left: list[symcctrace.data.TraceStep],
                                   right: list[symcctrace.data.TraceStep]) -> None:
    for left_step, right_step in zip(left, right):
        if left_step.pc != right_step.pc:
            print("PCs are different")
            print("Left PC", hex(left_step.pc))
            print("Right PC", hex(right_step.pc))
            print("----------------------------------")
            continue

        for location, symbol in left_step.memory_to_symbol_mapping.items():
            if location not in right_step.memory_to_symbol_mapping:
                print("PC", hex(left_step.pc))
                print("Left trace has a symbolic location that right trace does not have")
                print("Location", location)
                print("Symbol", symbol)
                print("----------------------------------")
                continue

            if right_step.memory_to_symbol_mapping[location] != symbol:
                print("PC", hex(left_step.pc))
                print("Left trace has a symbolic location that right trace has with a different symbol")
                print("Location", location)
                print("Left symbol", symbol)
                print("Right symbol", right_step.memory_to_symbol_mapping[location])
                print("----------------------------------")
                continue


def is_ancestor(symbol_a: symcctrace.data.Symbol, symbol_b: symcctrace.data.Symbol) -> bool:
    return symbol_a is symbol_b or any(is_ancestor(symbol_a, parent) for parent in symbol_b.args)


def find_problematic_instruction(
        left: list[symcctrace.data.TraceStep],
        right: list[symcctrace.data.TraceStep],
        path_constraint: symcctrace.data.PathConstraint
):
    for step_index, step_left, step_right in zip(itertools.count(), left, right):
        for location in step_left.memory_to_symbol_mapping:
            if is_ancestor(step_left.memory_to_symbol_mapping[location], path_constraint.symbol):
                if location not in step_right.memory_to_symbol_mapping or step_right.memory_to_symbol_mapping[location] != step_left.memory_to_symbol_mapping[location]:
                    print("Found problematic instruction at PC", hex(step_left.pc))
                    print("Step index", step_index)
                    return
        if step_left is path_constraint.after_step:
            print("The ptoblematic instruction is at path constraint step")
            print("Found problematic instruction at PC", hex(step_left.pc))
            print("Step index", step_index)
            return


def list_generated_test_cases(data: symcctrace.TraceData):
    for path_constraint in data.path_constraints:
        if path_constraint.new_input_value is not None:
            # print("Execution step",
            #       next(filter(lambda x: data.trace[x] is path_constraint.after_step, itertools.count())))
            # print("PC", hex(path_constraint.after_step.pc))
            print("Test case", path_constraint.new_input_value)


if __name__ == '__main__':
    old_dir = pathlib.Path(__file__).parent / 'old'
    new_dir = pathlib.Path(__file__).parent / 'new'

    # util.run_symqemu_and_save_trace_data(
    #     binary_name='printf',
    #     qemu_executable=pathlib.Path('/home/ubuntu/symqemu/x86_64-linux-user/symqemu-x86_64'),
    #     destination_directory=old_dir,
    #     qemu_additional_args='-d op -cpu qemu64'
    # )
    #
    # util.run_symqemu_and_save_trace_data(
    #     binary_name='printf',
    #     qemu_executable=pathlib.Path('/home/ubuntu/symqemu-new-version/build/qemu-x86_64'),
    #     destination_directory=new_dir,
    #     qemu_additional_args='-d op -cpu qemu64'
    # )

    util.run_symqemu_and_save_trace_data(
        binary_name='printf',
        qemu_executable=pathlib.Path('/home/ubuntu/symqemu-port/build/qemu-x86_64'),
        destination_directory=new_dir,
        qemu_additional_args='-d op -cpu qemu64'
    )

    # with open(old_dir / 'trace.pickle', 'rb') as f:
    #     old_trace_data: symcctrace.TraceData = pickle.load(f)

    with open(new_dir / 'trace.pickle', 'rb') as f:
        new_trace_data: symcctrace.TraceData = pickle.load(f)

    list_generated_test_cases(new_trace_data)

    # new_trace_data.trace = remove_additional_steps(old_trace_data.trace, new_trace_data.trace)
    # remove_memory_region(new_trace_data.trace, 'xmm_t0')
    # remove_memory_region(old_trace_data.trace, 'xmm_t0')
    #
    # missing = missing_path_constraints(old_trace_data, new_trace_data)
    # print(len(missing))
    # for path_constraint in missing:
    #     find_problematic_instruction(old_trace_data.trace, new_trace_data.trace, path_constraint)
    # #
    # print_steps_to_file(old_trace_data, old_dir / 'steps.txt')
    # print_steps_to_file(new_trace_data, new_dir / 'steps.txt')
    #
    # print("old")
    # print('xmm_t0', hex(relative_address('env', 'xmm_t0', old_trace_data)))
    # print('xmm_regs', hex(relative_address('env', 'xmm_regs', old_trace_data)))
    #
    # print("new")
    # print('xmm_t0', hex(relative_address('env', 'xmm_t0', new_trace_data)))
    # print('xmm_regs', hex(relative_address('env', 'xmm_regs', new_trace_data)))

    # path_constraint_subset_analysis(new_trace_data, old_trace_data)
    # symbolic_trace_subset_analysis(old_trace_data.trace, new_trace_data.trace)
