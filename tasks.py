"""Automation for common tasks in the twitch chatbot project."""

# Copyright 2024 Curtis Sand
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
import venv

from dataclasses import dataclass
from pathlib import Path

from invoke import Collection
from invoke import task


@dataclass
class Config:

    repo = Path(Path(__file__).parent)

    pyproject = repo / 'pyproject.toml'
    src = repo / 'src'
    venv = repo / 'venv'

    bin = venv / 'bin'
    python = bin / 'python'
    pip = bin / 'pip'
    pylint = bin / 'pylint'
    pip_compile = bin / 'pip-compile'

    # relative paths only, strings are input to pathlib.Path.glob
    clean_paths = [*[topfile for topfile in ['venv', 'build', 'dist']], '**/*egg-info']

    venv_packages = None


def require_pip(ctx, package):
    """Require a package to be installed with pip in the venv."""
    if Config.venv_packages is None:
        result = ctx.run(f'{Config.pip} freeze', hide=True)
        Config.venv_packages = result.stdout

    if package in Config.venv_packages:
        return True

    return False


@task
def create_venv(ctx):
    if Config.venv.exists():
        return

    print(f'create venv: {str(Config.venv)}')
    venv.create(Config.venv, system_site_packages=False, with_pip=True)


@task(create_venv)
def install_build(ctx):
    if require_pip(ctx, 'build') and require_pip(ctx, 'pip-tools'):
        return

    ctx.run(f"{Config.pip} install -e '{Config.repo}[build]'")


@task(create_venv, aliases=['develop'])
def install_dev(ctx):
    if require_pip(ctx, 'pylint') and require_pip(ctx, 'pytest'):
        return

    ctx.run(f"{Config.pip} install -e '{Config.repo}[dev]'")


@task(create_venv)
def install(ctx):
    if require_pip(ctx, 'twitchio'):
        return

    ctx.run(f"{Config.pip} install -e {Config.repo}")


@task
def clean(ctx):
    print(f'cleaning...')

    for pattern in Config.clean_paths:
        for found_file in Config.repo.glob(pattern):
            print(f'.. removing: {str(found_file)}')
            if found_file.is_dir():
                shutil.rmtree(found_file)
            else:
                found_file.unlink()


@task(install_dev)
def lint(ctx):
    ctx.run(f'{Config.pylint} {Config.src}')


@task(install_build)
def build(ctx):
    ctx.run(f'{Config.python} -m build {Config.repo}')


@task(install_build, aliases=['requirements'])
def update_requirements(ctx):
    pip_compile_cmd = f'{Config.pip_compile} --strip-extras --annotation-style line --allow-unsafe'
    for extra in ['', 'dev', 'build']:
        req_file = Config.repo / f'requirements.{extra}{"." if extra else ""}txt'

        print(f'.. generating {req_file}')
        cmd = f"{pip_compile_cmd} {f'--extra {extra}' if extra else ''} --output-file {req_file} {Config.pyproject}"
        ctx.run(cmd, hide=True)
