#!/usr/bin/env python3

from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Generator, Iterable, List, Set
from loguru import logger

import builtins

sys.path.insert(0, str(Path(__file__).parent))
from FileTypeE import FileTypeE


def _fstr_eval(_s: str, raw_string=False, eval=builtins.eval) -> str:
    r"""str: Evaluate a string as an f-string literal.

    Args:
       _s (str): The string to evaluate.
       raw_string (bool, optional): Evaluate as a raw literal
           (don't escape \). Defaults to False.
       eval (callable, optional): Evaluation function. Defaults
           to Python's builtin eval.

    Raises:
        ValueError: Triple-apostrophes ''' are forbidden.
    """
    # Prefix all local variables with _ to reduce collisions in case
    # eval is called in the local namespace.
    _TA = "'''"  # triple-apostrophes constant, for readability
    if _TA in _s:
        raise ValueError(
            "Triple-apostrophes ''' are forbidden. " + 'Consider using """ instead.'
        )

    # Strip apostrophes from the end of _s and store them in _ra.
    # There are at most two since triple-apostrophes are forbidden.
    if _s.endswith("''"):
        _ra = "''"
        _s = _s[:-2]
    elif _s.endswith("'"):
        _ra = "'"
        _s = _s[:-1]
    else:
        _ra = ""
    # Now the last character of s (if it exists) is guaranteed
    # not to be an apostrophe.

    _prefix = "rf" if raw_string else "f"
    return eval(_prefix + _TA + _s + _TA) + _ra


class PyFinder(object):
    EXEC_CMD_SEPERATORS: Set[str] = set([";", "\\;"])
    EXEC_CMD_PLACEHOLDER: str = "{}"

    def __init__(
        self,
        ftypes: Set[FileTypeE] | None,
        name_patterns: Iterable[str] | None,
        cmds: List[str] | None,
        maxdepth: int,
        mindepth: int,
    ):
        self.ftypes: Set[FileTypeE] | None = ftypes
        if name_patterns is None:
            self.name_patterns: Set[re.Pattern[str]] | None = None
        else:
            self.name_patterns = set()
            for _s in name_patterns:
                try:
                    self.name_patterns.add(re.compile(_s))
                except re.error as e:
                    logger.error(f"Invalid regex pattern for {_s}: {e}")
                    raise ValueError(f"Invalid regex pattern: {e}")

        self.cmds: List[str] | None = cmds
        self.maxdepth: int = maxdepth
        self.mindepth: int = mindepth

    def _filter_on_ftypes(self, p: Path) -> bool:
        if self.ftypes is None:
            return True
        _t: FileTypeE = FileTypeE.from_path(p)
        if _t in self.ftypes:
            return True
        return False

    def _filter_on_name(self, p: Path) -> bool:
        if self.name_patterns is None:
            return True
        for _pattern in self.name_patterns:
            if _pattern.match(p.name) is not None:
                return True
        return False

    def find(self, root_dir: Path) -> Generator[Path, None, None]:
        for _dir_str, _, _fnames in os.walk(root_dir):
            _dir: Path = Path(_dir_str)
            if self.maxdepth >= 0 or self.mindepth >= 0:
                _depth: int = len(_dir.relative_to(root_dir).as_posix().split("/"))
                if _depth > self.maxdepth:
                    continue
                if _depth < self.mindepth:
                    continue

            if self._filter_on_ftypes(_dir) and self._filter_on_name(_dir):
                if self.cmds is not None:
                    self._exec_cmd(_dir)
                else:
                    yield _dir
            for _fname in _fnames:
                _fpath: Path = _dir / _fname
                if self._filter_on_ftypes(_fpath) and self._filter_on_name(_fpath):
                    if self.cmds is not None:
                        self._exec_cmd(_fpath)
                    else:
                        yield _fpath

    def _exec_cmd(self, p: Path) -> None:
        if self.cmds is None:
            return
        _cmds: List[List[str]] = list()
        _cmd: List[str] = list()
        for _s in self.cmds:
            if _s == self.EXEC_CMD_PLACEHOLDER:
                _cmd.append(str(p))
            elif _s in self.EXEC_CMD_SEPERATORS:
                _cmds.append(_cmd)
                _cmd = list()
            else:
                _cmd.append(_s)
        for _cmd in _cmds:
            subprocess.run(_cmd)


if __name__ == "__main__":
    _arg_parser = argparse.ArgumentParser(description="""Same as find in bash.""")
    _arg_parser.add_argument(
        "roots",
        type=Path,
        nargs="+",
        help="Root of directory to search, '{expr}' is evaluated to get root directory.",
    )
    _arg_parser.add_argument(
        "--type",
        "-type",
        "-t",
        type=str,
        default=None,
        help=f"Type of file: { {_v.value: _v.name for _v in FileTypeE} }",
    )
    _arg_parser.add_argument(
        "--name",
        "-name",
        "-n",
        type=str,
        nargs="+",
        default=None,
        help="Regex to use to match target's name. If multiple regex are given, any one of them match will be a match.",
    )
    _arg_parser.add_argument(
        "-maxdepth",
        type=int,
        default=-1,
        help="Descend at most levels (a non-negative integer) levels of directories below the starting-points.  Using -maxdepth 0 means only apply the tests and actions to the starting-points themselves.",
    )
    _arg_parser.add_argument(
        "-mindepth",
        type=int,
        default=-1,
        help="Do not apply any tests or actions at levels less than levels (a non-negative integer). Using -mindepth 1 means process all files except the starting-points.",
    )
    _arg_v: List[str] = sys.argv
    _exec: List[str] | None = None
    if "-exec" in _arg_v:
        _idx: int = sys.argv.index("-exec")
        if _idx == len(_arg_v) - 1:
            # no arg is given for -exec
            _msg: str = "At least one command is required for -exec"
            logger.error(_msg)
            raise ValueError(_msg)
        _exec = _arg_v[_idx + 1 :]
        _arg_v = _arg_v[:_idx]
    _arg_parser.add_argument(
        "-exec",
        nargs="+",
        default=[],
        help="Statement to execute for each found target.",
    )
    _args = _arg_parser.parse_args(_arg_v)

    try:
        _ftypes: Set[FileTypeE] | None = FileTypeE.from_str(_args.type)
        _pyfind: PyFinder = PyFinder(
            _ftypes, _args.name, _exec, _args.maxdepth, _args.mindepth
        )
        for _root_dir in _args.roots:
            for _path in _pyfind.find(_root_dir):
                print(_path, file=sys.stdout)
    except KeyboardInterrupt:
        sys.exit(1)
    except ValueError:
        sys.exit(2)
    sys.exit(0)
