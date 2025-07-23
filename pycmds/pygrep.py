#!/usr/bin/env python3

from __future__ import annotations
import argparse
from enum import Enum
import multiprocessing
import os
from pathlib import Path
import re
import sys
from typing import Generator, Iterable, List, TextIO, Tuple
from loguru import logger


sys.path.insert(0, str(Path(__file__).parent))
from FileTypeE import FileTypeE


class PyGrepColorWhenE(Enum):
    NEVER = "never"
    ALWAYS = "always"
    AUTO = "auto"


class PyGrep(object):
    def __init__(
        self,
        regex_patterns: Iterable[str],
        fixed_string_patterns: Iterable[str],
        fpaths_with_patterns: Iterable[Path],
        fpaths_with_fixed_strings: Iterable[Path],
        no_message: bool,
        quit_on_error: bool,
        files: Iterable[Path | TextIO],
        debug_info: bool,
        sequential_processing: bool,
    ):
        self.no_message: bool = no_message
        self.quit_on_error: bool = quit_on_error
        self.debug_info: bool = debug_info
        self.sequential_processing: bool = sequential_processing
        self._prepare_regex(regex_patterns, fpaths_with_patterns)
        self._prepare_fixed_strings(fixed_string_patterns, fpaths_with_fixed_strings)
        self.files: Iterable[Path | TextIO] = files

    def _prepare_regex(
        self,
        regex_patterns: Iterable[str],
        fpaths_with_patterns: Iterable[Path],
    ) -> None:
        if self.debug_info:
            logger.debug(f"{self._prepare_regex.__name__}: {regex_patterns}")
        self.regex_patterns: List[re.Pattern[str]] = list()
        for _s in regex_patterns:
            try:
                _pattern: re.Pattern[str] = re.compile(_s)
                self.regex_patterns.append(_pattern)
            except Exception as _e:
                _msg: str = f"Failed to compile regex: {_s} ; due to error: {_e}"
                if not self.no_message:
                    logger.error(_msg)
                if self.quit_on_error:
                    raise ValueError(_msg)

        for _fpath in fpaths_with_patterns:
            try:
                with open(_fpath, "r") as _f:
                    for _line in _f:
                        _line = _line.rstrip(os.linesep)
                        _pattern: re.Pattern[str] = re.compile(_line)
                        self.regex_patterns.append(_pattern)
            except Exception as _e:
                _msg: str = (
                    f"Failed to compile regex from file: {_fpath} ; due to error: {_e}"
                )
                if not self.no_message:
                    logger.error(_msg)
                if self.quit_on_error:
                    raise RuntimeError(_msg)

    def _prepare_fixed_strings(
        self,
        fixed_string_patterns: Iterable[str],
        fpaths_with_fixed_strings: Iterable[Path],
    ) -> None:
        self.fixed_string_patterns: List[str] = list(fixed_string_patterns)

        for _fpath in fpaths_with_fixed_strings:
            try:
                with open(_fpath, "r") as _f:
                    for _line in _f:
                        _line = _line.rstrip(os.linesep)
                        self.fixed_string_patterns.append(_line)
            except Exception as _e:
                _msg: str = f"Failed to read fixed-string patterns from file: {_fpath} ; due to error: {_e}"
                if not self.no_message:
                    logger.error(_msg)
                if self.quit_on_error:
                    raise RuntimeError(_msg)

    def _generate_files(
        self, files: Iterable[Path | TextIO]
    ) -> Generator[Path | TextIO, None, None]:
        for _fpath in files:
            if isinstance(_fpath, Path):
                if not _fpath.exists():
                    _msg: str = f"{_fpath} does not exist."
                    if not self.no_message:
                        logger.error(_msg)
                    if self.quit_on_error:
                        raise ValueError(_msg)
                else:
                    _ftype: FileTypeE = FileTypeE.from_path(_fpath)
                    if _ftype == FileTypeE.regular_file:
                        yield _fpath
                    elif _ftype == FileTypeE.directory:
                        for _dir_str, _, _fnames in os.walk(_fpath):
                            _dir: Path = Path(_dir_str)
                            for _fname in _fnames:
                                yield _dir / _fname
                    else:
                        _msg: str = (
                            f"Unhandled file path: {_fpath} of type {_ftype.value}"
                        )
                        if not self.no_message:
                            logger.error(_msg)
                        if self.quit_on_error:
                            raise ValueError(_msg)
            elif isinstance(_fpath, TextIO):
                yield _fpath
            else:
                _msg: str = f"Unhandled file path: {_fpath} of type {type(_fpath)}"
                if not self.no_message:
                    logger.error(_msg)
                if self.quit_on_error:
                    raise ValueError(_msg)

    def search_line(self, fpath: Path | TextIO, line_num: int, line: str) -> bool:
        for _regex in self.regex_patterns:
            if _regex.search(line) is not None:
                return True
        for _str in self.fixed_string_patterns:
            if _str in line:
                return True
        return False

    def search_file(self, fpath: Path | TextIO) -> Tuple[Path | TextIO, bool]:
        if isinstance(fpath, Path):
            try:
                if self.debug_info:
                    logger.debug(
                        f"{self.search_file.__name__}: {fpath} -> {FileTypeE.mime_type(fpath)}"
                    )
                if not FileTypeE.is_text_file(fpath):
                    _msg: str = f"Ignoring non-text file: {fpath}"
                    if not self.no_message:
                        logger.warning(_msg)
                    return (fpath, False)
                with open(fpath, "r") as _f:
                    for _line_num, _line in enumerate(_f):
                        if self.search_line(fpath, _line_num, _line):
                            return (fpath, True)
                return (fpath, False)
            except Exception as _e:
                _msg: str = f"Failed to handle file {fpath} ; due to error {_e}"
                if not self.no_message:
                    logger.error(_msg)
                if self.quit_on_error:
                    raise RuntimeError(_msg)
        elif isinstance(fpath, TextIO):
            for _line_num, _line in enumerate(fpath):
                if self.search_line(fpath, _line_num, _line):
                    return (fpath, True)
                return (fpath, False)
        else:
            _msg: str = f"Unsupported file path: {fpath} of type {type(fpath)}"
            if not self.no_message:
                logger.error(_msg)
            if self.quit_on_error:
                raise ValueError(_msg)
        return (fpath, False)

    def search_files(self) -> None:
        _cpu_count: int | None = os.cpu_count()
        if self.sequential_processing or _cpu_count is None:
            if self.debug_info:
                logger.warning(
                    f"{self.search_files.__name__}: Process sequentially, with cpu_count={_cpu_count}"
                )
            for _fpath in self._generate_files(self.files):
                if self.search_file(_fpath):
                    print(_fpath, file=sys.stdout)
        else:
            _num_processes: int = max((_cpu_count // 2, 1))
            if self.debug_info:
                logger.debug(
                    f"{self.search_files.__name__}: parallel handling with {_num_processes} processes."
                )
            with multiprocessing.Pool(processes=_num_processes) as _pool:
                # _pool.imap_unordered(self.search_file, self._generate_files(self.files), chunksize=_num_processes)
                # _pool.map(self.search_file, self._generate_files(self.files))
                for _fpath, _has_match in _pool.imap_unordered(
                    self.search_file,
                    self._generate_files(self.files),
                    chunksize=_num_processes,
                ):
                    if _has_match:
                        print(_fpath, file=sys.stdout)


if __name__ == "__main__":
    _arg_parser = argparse.ArgumentParser(description="""A Python version of grep.""")

    _regex_group = _arg_parser.add_argument_group("Specify patterns")
    _regex_group.add_argument(
        "-e",
        "--python-regexp",
        type=str,
        action="append",
        help="Interpret PATTERNS as extended pythong regular expressions.",
    )
    _regex_group.add_argument(
        "-f",
        "--fixed-string",
        type=str,
        action="append",
        help="Interpret PATTERNS as fixed strings, not regular expressions.",
    )
    _regex_group.add_argument(
        "-fr",
        "--file-regex",
        type=Path,
        action="append",
        help="Obtain  patterns  from  FILE,  one per line.",
    )
    _regex_group.add_argument(
        "-ff",
        "--file-fixed-string",
        type=Path,
        action="append",
        help="Obtain  fixed string patterns  from  FILE,  one per line.",
    )

    _arg_parser.add_argument(
        "file",
        type=str,
        nargs="*",
        default=None,
        help="A FILE of “-” stands for standard input.  If no FILE is given, recursive searches examine the working directory, and nonrecursive searches read standard input.",
    )

    _match_ctrl_group = _arg_parser.add_argument_group("Match control")
    _match_ctrl_group.add_argument(
        "-i",
        "--ignore-case",
        action="store_true",
        help="Ignore case distinctions in patterns and input data, so that characters that differ only in case match each other.",
    )
    _match_ctrl_group.add_argument(
        "-v",
        "--invert-match",
        action="store_true",
        help="Invert the sense of matching, to select non-matching lines.",
    )

    _output_ctrl_group = _arg_parser.add_argument_group("Output control")
    _output_ctrl_group.add_argument(
        "-c",
        "--count",
        action="store_true",
        help="Suppress normal output; instead print a count of matching lines for each input file.  With the -v, --invert-match option (see above), count non-matching lines.",
    )
    _output_ctrl_group.add_argument(
        "--color",
        "--colour",
        type=PyGrepColorWhenE,
        metavar="WHEN",
        help=f"Surround the matched (non-empty) strings, matching lines, context lines, file names, line numbers, byte offsets, and separators (for fields  and  groups  of  context lines)  with  escape  sequences to display them in color on the terminal.  The colors are defined by the environment variable GREP_COLORS.  WHEN is {[_v.value for _v in PyGrepColorWhenE]}.",
    )
    _output_ctrl_group.add_argument(
        "-L",
        "--files-without-match",
        action="store_true",
        help="Suppress normal output; instead print the name of each input file from which no output would normally have been printed.",
    )
    _output_ctrl_group.add_argument(
        "-l",
        "--files-with-match",
        action="store_true",
        help="Suppress normal output; instead print the name of each input file from which output would normally have been printed. Scanning each input file stops upon first match.",
    )
    _output_ctrl_group.add_argument(
        "-m",
        "--max-count",
        type=int,
        metavar="NUM",
        help="Stop reading a file after NUM matching lines. If NUM is zero, grep stops right away without reading input. A NUM of -1 is treated as infinity and grep does not stop; this is the default.  If the input is standard input from a regular file, and NUM matching lines are output, grep ensures that the standard input is positioned to just after the last matching line before exiting, regardless of the presence of trailing context lines.  This enables a calling process to resume a search.  When grep stops after NUM matching lines, it outputs any trailing context lines.  When the -c or --count option is also used, grep does not output a count greater than NUM.  When the -v or --invert-match option is also used, grep stops after outputting NUM non-matching lines.",
    )
    _output_ctrl_group.add_argument(
        "-o",
        "--only-matching",
        action="store_true",
        help="Print only the matched (non-empty) parts of a matching line, with each such part on a separate output line.",
    )
    _output_ctrl_group.add_argument(
        "-q",
        "--quiet",
        "--silent",
        action="store_true",
        help="Quiet; do not write anything to standard output.  Exit immediately with zero status if any match is found, even if an error was detected. Also see the -s or --no-messages option.",
    )
    _output_ctrl_group.add_argument(
        "-s",
        "--no-message",
        action="store_true",
        help="Suppress error messages about nonexistent or unreadable files.",
    )
    _output_ctrl_group.add_argument(
        "--quit-on-error",
        action="store_true",
        help="Exit whenever an error occurs.",
    )

    _arg_parser.add_argument(
        "--debug-info", action="store_true", help="Enable debug logs."
    )
    _arg_parser.add_argument(
        "--sequential-processing",
        action="store_true",
        help="Force sequential processing of files.",
    )

    _args = _arg_parser.parse_args()

    _files: Iterable[Path | TextIO] = list()
    if _args.file is None:
        _files.append(sys.stdin)
    else:
        _files.extend([Path(_v) for _v in _args.file])

    if _args.debug_info:
        logger.debug(f"_args: {_args}")
    _py_grep: PyGrep = PyGrep(
        regex_patterns=_args.python_regexp
        if _args.python_regexp is not None
        else list(),
        fixed_string_patterns=_args.fixed_string
        if _args.fixed_string is not None
        else list(),
        fpaths_with_patterns=_args.file_regex
        if _args.file_regex is not None
        else list(),
        fpaths_with_fixed_strings=_args.file_fixed_string
        if _args.file_fixed_string is not None
        else list(),
        no_message=_args.no_message,
        quit_on_error=_args.quit_on_error,
        files=_files,
        debug_info=_args.debug_info,
        sequential_processing=_args.sequential_processing,
    )
    _py_grep.search_files()
