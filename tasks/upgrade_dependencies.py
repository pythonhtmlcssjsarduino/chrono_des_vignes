#! /usr/bin/env -S uv run --script
#
# Source:
# https://gist.github.com/yhoiseth/c80c1e44a7036307e424fce616eed25e?permalink_comment_id=5387642#gistcomment-5387642
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "typer>=0.15.3",
#   "tomlkit>=0.13.2",
# ]
# ///


"""
A stand-alone utility script to upgrade dependencies in pyproject.toml to their latest available versions.

This script addresses the common need to update all dependencies (including dependency groups)
in your pyproject.toml file to their latest compatible versions and updates the pyproject.toml file itself as well.
This script preserves the original order of your dependencies and can handle complex dependency
specifications with extras.

Requirements
- uv

How it works:
1. Recording the original order of dependencies
2. Upgrading all dependencies using uv's lock functionality
3. Removing and re-adding dependencies to ensure they're properly updated
4. Restoring the original order of dependencies in the pyproject.toml file

Usage:
    uv run upgrade_dependencies_uv_pyproject.py [OPTIONS] [PATH]

Arguments:
    [PATH]  Path to pyproject.toml file (default: ./pyproject.toml)

Options:
    -S, --sort  Sort dependencies alphabetically instead of preserving original order
    -V, --verbose  Enable verbose output showing all uv commands being executed

Examples:
    # Upgrade dependencies in the current directory's pyproject.toml
    uv run upgrade_dependencies_uv_pyproject.py

    # Upgrade dependencies in a specific pyproject.toml file
    uv run upgrade_dependencies_uv_pyproject.py /path/to/pyproject.toml

    # Upgrade dependencies and sort them alphabetically
    uv run upgrade_dependencies_uv_pyproject.py --sort

    # Upgrade with verbose output to see all uv commands
    uv run upgrade_dependencies_uv_pyproject.py --verbose

    # Combine options
    uv run upgrade_dependencies_uv_pyproject.py /path/to/pyproject.toml --sort --verbose

Note:
    - Follows PEP 723 convention
    - Dependencies with pinned versions (using ==) are not upgraded
    - By default, the original order of dependencies is preserved
"""

# ruff: noqa: S603
import functools
import subprocess  # noqa: S404
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, Self

import tomlkit
import typer
from tomlkit.items import Array as TomlArray

type DependencyMap = dict[str | None, list[str]]  # [GroupName, Dependencies]


@dataclass
class PackageSpec:
    name: str
    extras: str | None

    @classmethod
    def from_dependency(cls, dependency: str) -> Self:
        """parse package spec from dependency string

        examples:
        - requests>=1.0
        - fastapi[all]>=0.115.4
        - pandas[excel,plot]>=2.2.2
        - sqlacodegen==3.0.0rc5
        """

        for separator in (">=", "==", "<=", "~=", ">", "<", "!="):
            if separator in dependency:
                name_part = dependency.split(separator)[0].strip()
                break
        else:
            name_part = dependency.strip()

        if "[" in name_part:
            name, extras = name_part.split("[", 1)
            extras = f"[{extras}"
        else:
            name = name_part
            extras = None

        return cls(name=name, extras=extras)

    def __str__(self) -> str:
        """convert to dependency string"""
        return f"{self.name}{self.extras or ''}"


def get_original_order(pyproject_path: Path) -> DependencyMap:
    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    return {
        None: pyproject["project"]["dependencies"],
        **pyproject.get("dependency-groups", {}),
    }


def restore_order(pyproject_path: Path, original_orders: DependencyMap) -> None:
    """restore the order of dependencies in pyproject.toml"""

    def create_toml_array(dependencies: list[str]) -> TomlArray:
        array = tomlkit.array()
        array.multiline(True)
        array.extend(dependencies)
        return array

    with pyproject_path.open("rb") as updated_file:
        updated_data = tomllib.load(updated_file)

    with pyproject_path.open("r", encoding="utf-8") as f:
        doc = tomlkit.load(f)

    # update main dependencies
    updated_deps = {
        PackageSpec.from_dependency(dep).name: dep
        for dep in updated_data["project"]["dependencies"]
    }

    new_deps = create_toml_array(
        [
            updated_deps[PackageSpec.from_dependency(orig_dep).name]
            for orig_dep in original_orders[None]
            if PackageSpec.from_dependency(orig_dep).name in updated_deps
        ]
    )

    doc["project"]["dependencies"] = new_deps  # type: ignore[index]

    # update dependency groups
    if "dependency-groups" in updated_data:
        for group, orig_deps in original_orders.items():
            if group is None or group not in updated_data["dependency-groups"]:
                continue

            updated_group_deps = {
                PackageSpec.from_dependency(dep).name: dep
                for dep in updated_data["dependency-groups"][group]
            }

            new_group_deps = create_toml_array(
                [
                    updated_group_deps[PackageSpec.from_dependency(orig_dep).name]
                    for orig_dep in orig_deps
                    if PackageSpec.from_dependency(orig_dep).name in updated_group_deps
                ]
            )

            doc["dependency-groups"][group] = new_group_deps  # type: ignore[index]

    with pyproject_path.open("w", encoding="utf-8") as f:
        tomlkit.dump(doc, f)


def print_format_command(command: list[str]) -> None:
    cmd = command.copy()

    cmd[0] = typer.style(cmd[0], fg=typer.colors.GREEN)  # uv
    cmd[1] = typer.style(cmd[1], fg=typer.colors.YELLOW)  # action

    flag_idx = next((i for i, v in enumerate(cmd) if v.startswith("--")), len(cmd))

    # package name
    cmd[2:flag_idx] = [typer.style(t, bold=True) for t in cmd[2:flag_idx]]

    # action options
    cmd[flag_idx:] = [typer.style(t, fg=typer.colors.CYAN) for t in cmd[flag_idx:]]

    print(" ".join(cmd))


def uv_action(
    action: Literal["add", "remove", "sync", "lock"],
    verbose: bool = False,
    *,
    package_spec: list[PackageSpec] | None = None,
    group: str | None = None,
) -> None:
    if action == "sync":
        command = ["uv", "sync", "--all-groups"]
        print("=" * 40)
    elif action == "lock":
        command = ["uv", "lock", "--upgrade"]
    else:
        if package_spec is None:
            raise ValueError("package_spec is required")
        packages = [str(pkg) if action == "add" else pkg.name for pkg in package_spec]
        group_arg = ["--group", group] if group else []
        command = ["uv", action, *packages, "--no-sync", *group_arg]

    if verbose:
        print_format_command(command)
        subprocess.check_call(command)
    elif action in {"sync", "lock"}:
        subprocess.check_call(command)
    else:
        subprocess.check_call(command, stderr=subprocess.DEVNULL)


def run_uv_command(all_dependencies: DependencyMap, verbose: bool = False) -> None:
    run_uv_action = functools.partial(uv_action, verbose=verbose)

    run_uv_action("lock")

    for group, dependencies in all_dependencies.items():
        # filter out packages with pinned versions
        packages = [
            PackageSpec.from_dependency(dep) for dep in dependencies if "==" not in dep
        ]

        run_uv_action("remove", package_spec=packages, group=group)
        run_uv_action("add", package_spec=packages, group=group)

    run_uv_action("sync")


def main(
    path: Annotated[Path, typer.Argument(help="Path to pyproject.toml file")] = Path(
        "./pyproject.toml"
    ),
    sort_deps: Annotated[
        bool,
        typer.Option("--sort", "-S", help="sort dependencies in pyproject.toml"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-V",
            help="Enable verbose output showing all uv commands being executed",
        ),
    ] = False,
) -> None:
    """
    A utility script to upgrade dependencies in pyproject.toml to their latest available versions.

    This script addresses the common need to update all dependencies (including dependency groups)
    in your pyproject.toml file to their latest compatible versions and updates the pyproject.toml file itself as well.
    """
    if path.name != "pyproject.toml":
        raise typer.BadParameter("file must be pyproject.toml")

    original_orders = get_original_order(path)
    run_uv_command(original_orders, verbose)
    if not sort_deps:
        restore_order(path, original_orders)


if __name__ == "__main__":
    typer.run(main)
