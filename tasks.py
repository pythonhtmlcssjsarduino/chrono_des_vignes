from zipfile import ZIP_DEFLATED, ZipFile
from icecream import ic
from invoke import task
from invoke.context import Context
from pathlib import Path
from re import compile, Pattern
from fnmatch import translate
import os

@task
def serve(ctx: Context):
    ctx.run('flask --app chrono_des_vignes run --debug')

@task
def build_doc(ctx: Context):
    config_path = Path.cwd()/'front-end/doc'/'mkdocs.yml'
    build_path = Path.cwd()/'chrono_des_vignes'/'static'/'doc'
    ctx.run(f"mkdocs build --config-file {config_path} --site-dir {build_path}")

@task
def requirements(ctx: Context):
    ctx.run("uv export --no-hashes --format requirements.txt --no-dev > requirements.txt")

@task(pre=[build_doc, requirements])  # pyright: ignore[reportUntypedFunctionDecorator]
def release(ctx: Context, output:str='release.zip'):
    output_file = Path(output).absolute()
    base_dir = Path.cwd()/'chrono_des_vignes'
    files_glob: list[str] = [
        '!**__pycache__**',
        '!dev/**',
        '!translations/ids/**',
        '!translations/pseudo/**',
        '!**/profil_pics/**',
        '**/profil_pics/icone.png',
        '!messages.pot',
        '!babel.cfg',
    ]
    with ZipFile(output_file, 'w', ZIP_DEFLATED) as zipf:
        for path in get_maching_files(base_dir, files_glob):
            zipf.write(path, 'chrono_des_vignes'/path.relative_to(base_dir))
            print(f"✔ Inclus : {path.relative_to(base_dir)}")
        # include the requirements.txt
        zipf.write('requirements.txt', 'requirements.txt')
#===========lib==================

def compile_patterns(patterns:list[str]):
    compiled: list[tuple[bool, Pattern[str]]] = []
    for p in patterns:
        pat =Path(p[1:] if p.startswith("!") else p).as_posix()
        regex = compile(translate(pat))
        compiled.append((p.startswith("!"), regex))
    return compiled

def matches(path: str, compiled_patterns:list[tuple[bool, Pattern[str]]]) -> bool:
    include = True
    for is_exclude, regex in compiled_patterns:
        if regex.match(path):
            include = not is_exclude
    return include

def get_maching_files(base_dir:Path, patterns:list[str]):
    compiled_patterns = compile_patterns(patterns)
    matching_files: list[Path] = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            full_path = Path(root, file)
            rel_path = full_path.relative_to(base_dir)
            if matches(rel_path.as_posix(), compiled_patterns):
                matching_files.append(full_path)
    return matching_files