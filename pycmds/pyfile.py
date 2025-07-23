#!/usr/bin/env python3

from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys
from typing import Tuple
from loguru import logger


sys.path.insert(0, str(Path(__file__).parent))
from FileReader import FileTypeCodec


def guess_file_type_and_codec(
    target: Path, print_type: bool, print_codec: bool, print_path: bool
) -> None:
    _type_codec: Tuple[str, str] | None = FileTypeCodec.magic_from_file(target)
    if _type_codec is None:
        logger.error(f"Cannot decide type and codec of file: {target}")
        return
    _type, _codec = _type_codec
    if (print_type and print_codec) or (not print_type and not print_codec):
        print(f"{str(target) + ': ' if print_path else ''}{_type}; {_codec}")
    elif print_type:
        print(f"{str(target) + ': ' if print_path else ''}{_type}")
    elif print_codec:
        print(f"{str(target) + ': ' if print_path else ''}{_codec}")


if __name__ == "__main__":
    _arg_parser = argparse.ArgumentParser(description="""Guess file type and codec.""")
    _arg_parser.add_argument(
        "targets",
        type=Path,
        nargs="+",
        help="targets to check, can be files or directories; if a directory is given, will search recursively.",
    )
    _arg_parser.add_argument(
        "--type",
        "-type",
        "-t",
        action="store_true",
        help="Print type of file.",
    )
    _arg_parser.add_argument(
        "--codec",
        "-codec",
        "-c",
        action="store_true",
        help="Print codec of file.",
    )
    _arg_parser.add_argument(
        "-maxdepth",
        type=int,
        default=-1,
        help="Descend at most levels (a non-negative integer) levels of directories below the starting-points. Using -maxdepth 0 means only apply the tests and actions to the starting-points themselves.",
    )
    _arg_parser.add_argument(
        "-mindepth",
        type=int,
        default=-1,
        help="Do not apply any tests or actions at levels less than levels (a non-negative integer). Using -mindepth 1 means process all files except the starting-points.",
    )
    _arg_parser.add_argument(
        "--path",
        "-p",
        action="store_true",
        help="Print path of file.",
    )

    _args = _arg_parser.parse_args()

    try:
        for _target in _args.targets:
            _target = _target.resolve()
            logger.debug(f"Processing target: {_target}")
            if not _target.exists():
                continue
            if _target.is_file():
                guess_file_type_and_codec(_target, _args.type, _args.codec, _args.path)
            elif _target.is_dir():
                for _dir_str, _, _fnames in os.walk(_target):
                    if (
                        _args.maxdepth >= 0
                        and len(Path(_dir_str).relative_to(_target).parts)
                        > _args.maxdepth
                    ):
                        continue
                    for _fname in _fnames:
                        _fpath: Path = Path(_dir_str) / _fname
                        if not _fpath.exists():
                            continue
                        if (
                            _args.mindepth >= 0
                            and len(Path(_fpath).relative_to(_target).parts)
                            < _args.mindepth
                        ):
                            continue
                        guess_file_type_and_codec(
                            _fpath, _args.type, _args.codec, _args.path
                        )
    except KeyboardInterrupt:
        sys.exit(1)
    except ValueError:
        sys.exit(2)
    sys.exit(0)
