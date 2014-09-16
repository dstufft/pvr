# Copyright 2014 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import absolute_import, division, print_function

import os.path
import shutil

import appdirs
import click

from .builder import EnvBuilder
from .installer import PipInstaller


@click.group()
@click.pass_context
def cli(ctx):
    # Ensure that our context object is initialized to an empty dictionary.
    if ctx.obj is None:
        ctx.obj = {}

    # Compute the various directories that pvr will require.
    dirs = appdirs.AppDirs(appname="pvr", appauthor=False, multipath=True)
    ctx.obj["dirs"] = {
        "cache": os.path.join(dirs.user_cache_dir),
        "environments": os.path.expanduser("~/.pvr/envs"),
    }


@cli.command(
    short_help="Creates a new virtual environment.",
    help="Create a new virtual environment with the given name.",
)
@click.argument("name")
@click.pass_context
def create(ctx, name):
    # Compute the target path for this environment.
    target = os.path.join(ctx.obj["dirs"]["environments"], name)

    # Determine if this environment already exists.
    if os.path.exists(target):
        raise click.ClickException(
            "An environment named {} already exists.".format(name)
        )

    # Create the new virtual environment
    builder = EnvBuilder(system_site_packages=False, clear=False)
    builder.create(target)

    # Install pip into the virtual environment.
    with PipInstaller(target, cache_dir=ctx.obj["dirs"]["cache"]) as installer:
        installer.install()


@cli.command(
    short_help="Removes an existing virtual environment.",
    help="Remove a virtual environment with the given name.",
)
@click.argument("name")
@click.pass_context
def remove(ctx, name):
    # Compute the target path for this environment.
    target = os.path.join(ctx.obj["dirs"]["environments"], name)

    # Remove the directory
    shutil.rmtree(target)


@cli.command(
    "exec",
    short_help="Execute a command inside a virtual environment.",
    help="Execute the given command inside the named virtual environment.",
    context_settings={
        "ignore_unknown_options": True,
        "allow_interspersed_args": False,
    }
)
@click.argument("name")
@click.argument("command", nargs=-1, required=True)
@click.pass_context
def exec_(ctx, name, command):
    # Compute the target path and bin dir for this environment.
    target = os.path.join(ctx.obj["dirs"]["environments"], name)
    # TODO: This is called "Scripts" on Windows, at least in venv, is it the
    #       same in virtualenv? Also it's likely python.exe on Windows as well.
    bin_dir = os.path.join(target, "bin")

    # If our target doesn't exist, then we need to bomb out
    if not os.path.exists(target):
        raise click.ClickException("No environment named {0}".format(name))

    # Compute what would be our $PATH directory.
    path = bin_dir + os.pathsep + os.environ.get("PATH", os.defpath)

    # Duplicate our environment, and modify our $PATH environment variable to
    # include our virtual environment.
    env = os.environ.copy()
    env["PATH"] = path

    # Run our command, replacing the current process with the new process
    # of our command.
    os.execvpe(command[0], command, env)
