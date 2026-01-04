from shutil import rmtree
from zipfile import ZIP_DEFLATED, ZipFile
from icecream import ic
from invoke.tasks import call, task
from invoke.context import Context
from pathlib import Path
from re import compile, Pattern
from fnmatch import translate
import os
import tempfile
from dotenv import dotenv_values, set_key

from invoke.exceptions import UnexpectedExit
from invoke.runners import Promise

frontend_path = Path.cwd() / "front-end"
loaders = "--loader:.css=css --loader:.png=file --loader:.svg=file"


@task
def dev(ctx: Context):
    try:
        ts: Promise = ctx.run("inv watch-ts", asynchronous=True, hide=True)  # pyright: ignore[reportAssignmentType]
        serve: Promise = ctx.run("inv serve", asynchronous=True, hide=True)  # pyright: ignore[reportAssignmentType]
        ic("serving and watching...")
        ts.join()
        serve.join()
    except UnexpectedExit:
        ic("exiting...")


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


@task(pre=[check_node_modules, clean_js])  # pyright: ignore[reportUntypedFunctionDecorator]
def build_ts(ctx: Context, dev: bool = False):
    ts_files = list((frontend_path / "ts").glob("*.ts"))
    if len(ts_files) == 0:
        ic("no ts files found")
        return
    with ctx.cd(frontend_path):
        ctx.run("node esbuild.config.mjs")
        # ctx.run(f'npx esbuild {" ".join(map(lambda x:x.as_posix(), ts_files))} --bundle {'--sourcemap'if dev else '--minify'} --outdir=../chrono_des_vignes/static/js --splitting {loaders} --public-path=/static/js --format=esm')


@task(pre=[check_node_modules, clean_js])  # pyright: ignore[reportUntypedFunctionDecorator]
def watch_ts(ctx: Context, split: bool = False):
    ts_files = list((frontend_path / "ts").glob("*.ts"))
    if len(ts_files) == 0:
        ic("no ts files found")
        return
    with ctx.cd(frontend_path):
        ctx.run("node esbuild.config.mjs --watch")
        # ctx.run(f'npx esbuild {" ".join(map(lambda x:x.as_posix(), ts_files))} --bundle --sourcemap --outdir=../chrono_des_vignes/static/js {'--splitting'if split else ''} {loaders} --public-path=/static/js --format=esm --watch')


@task
def serve(ctx: Context):
    ctx.run("flask --app chrono_des_vignes run --debug")


@task
def build_doc(ctx: Context, dev: bool = True):
    build_path = Path.cwd() / "chrono_des_vignes" / "static" / "doc"
    config_path = Path.cwd() / "front-end" / "mkdocs.yml"
    doc_dir = Path.cwd() / "front-end" / "docs"
    with tempfile.NamedTemporaryFile() as f:
        with config_path.open() as conf:
            c = conf.read().replace("<<docs_dir>>", doc_dir.as_posix())
            if not dev:
                c = c.replace(
                    "<<site_url>>", "https://chronodesvignes.eu.pythonanywhere.com"
                )
            else:
                c = c.replace("<<site_url>>", "http://localhost:5000")
            f.write(c.encode("utf-8"))
            f.flush()
        print(f.name)
        with open(f.name) as fs:
            print(fs.read())
        ctx.run(f"mkdocs build --config-file {f.name} --site-dir {build_path}")


@task
def requirements(ctx: Context):
    ctx.run(
        "uv export --no-hashes --format requirements.txt --no-dev > requirements.txt"
    )


@task(pre=[build_doc, requirements, build_ts])  # pyright: ignore[reportUntypedFunctionDecorator]
def release(ctx: Context, output: str = "release.zip"):
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
        zipf.write("requirements.txt", "requirements.txt")


@task
def env(ctx: Context):
    # Define your variables
    default_env = {
        "db_password": "",
        "db_user": "",
        "db_host": "",
        "db_name": "",
        "SERVER_NAME": "",
        "SECRET_KEY": "",
        "mail_host": '["", 587]',
        "from_addr": "",
        "mail_token": "",
        "to_addrs": '[""]',
    }
    # Load existing .env file if it exists
    env_file = ".env"
    existing_env = dotenv_values(env_file) if os.path.exists(env_file) else {}

    # Merge existing values with defaults (existing values take precedence)
    env_vars = {**default_env, **existing_env}
    for key in env_vars:
        current_value = env_vars[key]
        user_input = input(
            f"Enter value for {key} (current: '{current_value}'): "
        ).strip()

        if user_input != "" or key not in existing_env:
            set_key(env_file, key, user_input)
            env_vars[key] = user_input

    print(f".env file has been updated successfully at {os.path.abspath(env_file)}!")


@task(post=[build_ts, call(build_doc, dev=True)])  # pyright: ignore[reportUntypedFunctionDecorator, reportArgumentType]
def sync(ctx: Context, dev: bool = False):
    ctx.run("uv sync")


@task(pre=[env, sync])  # pyright: ignore[reportUntypedFunctionDecorator, reportArgumentType]
def init(ctx: Context):
    ctx.run("pybabel compile -d chrono_des_vignes/translations -f")


@task
def build_db(ctx: Context):
    print("creating database")
    from chrono_des_vignes import app, db

    with app.app_context():
        db.create_all()


# ===========lib==================


def compile_patterns(patterns: list[str]):
    compiled: list[tuple[bool, Pattern[str]]] = []
    for p in patterns:
        pat = Path(p[1:] if p.startswith("!") else p).as_posix()
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
