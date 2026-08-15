import os
import tempfile
import tomllib
from fnmatch import translate
from pathlib import Path
from re import Pattern, compile
from shutil import rmtree
from zipfile import ZIP_DEFLATED, ZipFile

from icecream import ic
from invoke.context import Context
from invoke.tasks import call, task

with open("cdv.toml", "rb") as f:
    config = tomllib.load(f)

frontend_path = Path.cwd() / "front-end"
loaders = "--loader:.css=css --loader:.png=file --loader:.svg=file"


@task
def check_node_modules(ctx: Context):
    if not (frontend_path / "node_modules").exists():
        with ctx.cd(frontend_path):
            ctx.run("npm install")
        ic("node_modules installed")
    else:
        ic("node_modules already installed")


@task
def clean_js(ctx: Context):
    rmtree(Path.cwd() / "chrono_des_vignes" / "static" / "js", ignore_errors=True)


@task(pre=[check_node_modules, clean_js])
def build_ts(ctx: Context, dev: bool = False):
    ts_files = list((frontend_path / "ts").glob("*.ts"))
    if len(ts_files) == 0:
        ic("no ts files found")
        return
    with ctx.cd(frontend_path):
        ctx.run("node esbuild.config.mjs")


@task
def build_doc(ctx: Context, dev: bool = True):
    build_path = Path.cwd() / "chrono_des_vignes" / "static" / "doc"
    config_path = Path.cwd() / "front-end" / "mkdocs.yml"
    doc_dir = Path.cwd() / "front-end" / "docs"

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".yml") as f:
        with config_path.open() as conf:
            content: str = conf.read()

        # Remplacements clairement typés
        replacements: dict[str, str] = {
            "<<docs_dir>>": doc_dir.as_posix(),
            "<<site_url>>": config["build"]["url"]
            if not dev
            else f"http://{config['dev']['host']}:{config['dev']['port']}",
        }

        # Appliquer tous les remplacements
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        f.write(content)
        f.flush()
        temp_file = f.name

    try:
        print(temp_file)
        with open(temp_file) as fs:
            print(fs.read())
        ctx.run(f"mkdocs build --config-file {temp_file} --site-dir {build_path}")
    finally:
        os.unlink(temp_file)


@task
def requirements(ctx: Context):
    if not Path("build").exists():
        os.mkdir("build")
    ctx.run(
        "uv export --no-hashes --format requirements.txt --no-dev > build/requirements.txt"
    )


@task(pre=[call(build_doc, dev=False), requirements, build_ts])  # pyright: ignore[reportArgumentType]
def release(ctx: Context, output: str = "build/release.zip"):
    output_file = Path(output).absolute()
    base_dir = Path.cwd() / "chrono_des_vignes"
    files_glob: list[str] = [
        "!**__pycache__**",
        "!dev/**",
        "!translations/ids/**",
        "!translations/pseudo/**",
        "!**/profil_pics/**",
        "**/profil_pics/icone.png",
        "!messages.pot",
        "!babel.cfg",
    ]
    with ZipFile(output_file, "w", ZIP_DEFLATED) as zipf:
        for path in get_maching_files(base_dir, files_glob):
            zipf.write(path, "chrono_des_vignes" / path.relative_to(base_dir))
            print(f"✔ Inclus : {path.relative_to(base_dir)}")
        # include the requirements.txt
        zipf.write("build/requirements.txt", "requirements.txt")
        zipf.write(".python-version", ".python-version")


@task(post=[build_ts, call(build_doc, dev=True)])  # pyright: ignore[reportUntypedFunctionDecorator, reportArgumentType]
def sync(ctx: Context, dev: bool = False):
    ctx.run("uv sync")


@task(pre=[sync])
def init(ctx: Context):
    ctx.run("pybabel compile -d chrono_des_vignes/translations -f")


# ===========lib==================


def compile_patterns(patterns: list[str]):
    compiled: list[tuple[bool, Pattern[str]]] = []
    for p in patterns:
        pat = Path(p.removeprefix("!")).as_posix()
        regex = compile(translate(pat))
        compiled.append((p.startswith("!"), regex))
    return compiled


def matches(path: str, compiled_patterns: list[tuple[bool, Pattern[str]]]) -> bool:
    include = True
    for is_exclude, regex in compiled_patterns:
        if regex.match(path):
            include = not is_exclude
    return include


def get_maching_files(base_dir: Path, patterns: list[str]):
    compiled_patterns = compile_patterns(patterns)
    matching_files: list[Path] = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            full_path = Path(root, file)
            rel_path = full_path.relative_to(base_dir)
            if matches(rel_path.as_posix(), compiled_patterns):
                matching_files.append(full_path)
    return matching_files
