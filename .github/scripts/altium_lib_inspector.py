import os
from pathlib import Path
import json
import glob
import olefile
from jinja2 import Environment, FileSystemLoader, select_autoescape


def schlib_parse(input):
    fullPath = input
    ole = olefile.OleFileIO(fullPath)
    components = []
    for entry in ole.listdir(streams=True, storages=False):
        if "Data" in entry:
            stream = ole.openstream(entry)
            params = stream.read()[5:-1]
            pairs = params.split(b"|")
            component = {}
            model = {}
            for pair in pairs:
                data = pair.split(b"=")
                keyword = data[0].decode("utf-8", "ignore").upper()
                if keyword in [
                    "LIBREFERENCE",
                    "COMPONENTDESCRIPTION",
                    "MODELNAME",
                    "DESCRIPTION",
                ]:
                    if keyword in ["MODELNAME", "DESCRIPTION"]:
                        if "Models" not in component:
                            component["Models"] = []
                        if data[0].decode() in model:
                            component["Models"].append(dict(reversed(model.items())))
                            model.clear()
                        model[data[0].decode()] = data[1].decode("utf-8", "ignore")
                    else:
                        component[data[0].decode()] = data[1].decode("utf-8", "ignore")
            if bool(model):
                component["Models"].append(dict(reversed(model.items())))
            components.append(component)
    return components


def pcblib_parse(input):
    fullPath = input
    ole = olefile.OleFileIO(fullPath)
    components = []
    for entry in ole.listdir(streams=True, storages=False):
        if "PARAMETERS" in [e.upper() for e in entry]:
            stream = ole.openstream(entry)
            params = stream.read()[5:-1]
            pairs = params.split(b"|")
            component = {}
            for pair in pairs:
                data = pair.split(b"=")
                component[data[0].decode()] = data[1].decode("utf-8", "ignore")
            components.append(component)
    return components


def inspect_libraries():
    libraries = {}
    libraries["schlibs"] = {}
    libraries["pcblibs"] = {}
    schlib_path = "AltiumSCHLIB/"
    for filepath in glob.iglob(schlib_path + "**/*.??????", recursive=True):
        filename = Path(filepath).stem
        if Path(filepath).suffix.lower() == ".schlib":
            libraries["schlibs"][filename] = schlib_parse(filepath)
    pcblib_path = "AltiumPCBLIB/"
    for filepath in glob.iglob(pcblib_path + "**/*.??????", recursive=True):
        filename = Path(filepath).stem
        if Path(filepath).suffix.lower() == ".pcblib":
            libraries["pcblibs"][filename] = pcblib_parse(filepath)
    return libraries


def generate_json(libraries):
    json_file = open("inspect_result.json", "w")
    json.dump(libraries, json_file, indent=4)


def get_total_comp(libs):
    sum = 0
    for comps in libs.values():
        sum = sum + len(comps)
    return sum


def get_webpage_subdomain():
    return os.environ["BROWSING_WEBPAGE_SUBDOMAIN"]


def get_webpage_path():
    return os.environ["BROWSING_WEBPAGE_PATH"]


def render_template(libraries, file_path):
    env = Environment(loader=FileSystemLoader("."), autoescape=select_autoescape())
    env.filters["get_total_comp"] = get_total_comp
    env.globals["get_webpage_subdomain"] = get_webpage_subdomain
    env.globals["get_webpage_path"] = get_webpage_path
    template_dir_path = (
        Path(__file__).resolve().parent.relative_to(Path.cwd().as_posix()).as_posix()
        + "/"
    )
    template_file = env.get_template(template_dir_path + file_path)
    return template_file.render(libraries=libraries)


def generate_readme(libraries):
    readme = render_template(libraries, "README.md.template")
    with open("README.md", "w") as readme_fhdl:
        readme_fhdl.write(readme)


def generate_browsing_webpage(libraries):
    browsing_webpage = render_template(libraries, "index.html.template")
    with open("index.html", "w") as browsing_webpage_fhdl:
        browsing_webpage_fhdl.write(browsing_webpage)


def main():
    libraries = inspect_libraries()
    generate_json(libraries)
    generate_readme(libraries)
    generate_browsing_webpage(libraries)


if __name__ == "__main__":
    main()