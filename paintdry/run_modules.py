import pathlib
from subprocess import Popen, PIPE, STDOUT

from paintdry.utils import JsonFile
from paintdry.lib import get_config_filename


def run_module(name: str, command: str):
    print(f"Running '{name}' module")
    module_folder = f"./mount-state/modules/{name}"
    cache_folder = "./mount-state/"
    input_folder = f"{module_folder}/requests"
    output_folder = f"{module_folder}/responses"
    pathlib.Path(input_folder).mkdir(parents=True, exist_ok=True)
    pathlib.Path(output_folder).mkdir(parents=True, exist_ok=True)
    pathlib.Path(cache_folder).mkdir(parents=True, exist_ok=True)

    full_command = f"{command} '{input_folder}' '{output_folder}' '{cache_folder}'"
    process = Popen(
        full_command,
        shell=True,
        text=True,
        encoding="utf-8",
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
    )
    (out, err) = process.communicate()
    out = out.strip()
    if out:
        print(f"Output from {name} module:")
        print(out)
    if err:
        print(f"Stderr from {name} module:")
        print(err)
    r = process.wait()
    if r != 0:
        print(f"Module {name} exited with error: {r}")
    else:
        print(f"Module {name} finished successfully")


def run_modules():
    config = JsonFile(get_config_filename())
    for name in config["modules"]:
        module = config["modules"][name]
        command = module["command"]
        run_module(name, command)


if __name__ == "__main__":
    run_modules()
