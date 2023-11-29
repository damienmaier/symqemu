import pathlib
import pickle

import data

# new = data.build_data(
#     binary_name='printf',
#     qemu_executable=pathlib.Path('/home/ubuntu/symqemu-new-version/build/x86_64-linux-user/qemu-x86_64'),
#     additional_args='-cpu qemu64 -d op'
# )
#
# with open(pathlib.Path(__file__).parent.parent / 'new' / 'trace.pickle', 'wb') as file:
#     pickle.dump(new, file)
#
# old = data.build_data(
#     binary_name='printf',
#     qemu_executable=pathlib.Path('/home/ubuntu/symqemu/x86_64-linux-user/symqemu-x86_64'),
#     additional_args='-cpu qemu64 -d op'
# )
#
# with open(pathlib.Path(__file__).parent.parent / 'old' / 'trace.pickle', 'wb') as file:
#     pickle.dump(old, file)


with open(pathlib.Path(__file__).parent.parent / 'new' / 'trace.pickle', 'rb') as file:
    new: data.TraceData = pickle.load(file)

with open(pathlib.Path(__file__).parent.parent / 'old' / 'trace.pickle', 'rb') as file:
    old: data.TraceData = pickle.load(file)

for step_index, old_step in enumerate(old.trace):
    while old_step.pc != new.trace[step_index].pc:
        new.trace.pop(step_index)

(pathlib.Path(__file__).parent.parent / 'new' / 'stdout_stderr').write_text(new.debug_text)
(pathlib.Path(__file__).parent.parent / 'old' / 'stdout_stderr').write_text(old.debug_text)


target_constraint = old.path_constraints[6]
print(target_constraint.new_input_value)


def depends_on(symbol_a: data.Symbol, symbol_b: data.Symbol) -> bool:
    return symbol_a is symbol_b or any(depends_on(arg, symbol_b) for arg in symbol_a.args)

with open(pathlib.Path(__file__).parent.parent / 'old' / 'trace_dependencies', 'w') as file:
    for step in old.trace:
        for location, symbol in step.memory_to_symbol_mapping.items():
            if depends_on(target_constraint.symbol, symbol):
                print(location, symbol, id(symbol), file=file)

        print(f"PC {hex(step.pc)}", file=file)
        print("------------------", file=file)
        if step is target_constraint.after_step:
            break

def is_equivalent(symbol_a: data.Symbol, symbol_b: data.Symbol) -> bool:
    return symbol_a.kind == symbol_b.kind \
        and len(symbol_a.args) == len(symbol_b.args) \
        and all(is_equivalent(arg_a, arg_b) for arg_a, arg_b in zip(symbol_a.args, symbol_b.args))


with open(pathlib.Path(__file__).parent.parent / 'old' / 'comparison', 'w') as file:
    for old_step, new_step in zip(old.trace, new.trace):
        assert (old_step.pc == new_step.pc)

        for location, symbol in old_step.memory_to_symbol_mapping.items():
            if location not in new_step.memory_to_symbol_mapping or not is_equivalent(new_step.memory_to_symbol_mapping[location], symbol):
                if depends_on(target_constraint.symbol, symbol):
                    print(f'At PC {hex(old_step.pc)}, location {location} is not equivalent', file=file)

        if old_step is target_constraint.after_step:
            break
