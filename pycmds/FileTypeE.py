from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, Set

from loguru import logger
import magic


class FileTypeE(Enum):
    block_device = "b"
    char_unbuffered_special = "c"
    directory = "d"
    regular_file = "f"
    symbolic_link = "l"
    mount = "m"
    fifo = "o"
    socket = "s"

    @classmethod
    def all_chars(cls) -> str:
        return "".join([_v.value for _v in cls])

    @classmethod
    def hint_dict(cls) -> Dict[str, str]:
        return {_v.value: _v.name for _v in cls}

    @classmethod
    def from_str(cls, s: str | None) -> Set[FileTypeE] | None:
        if s is None:
            return None
        _set: Set[FileTypeE] = set()
        _all_chars: str = cls.all_chars()
        for _c in s:
            if _c not in _all_chars:
                _msg: str = f"{_c} is not a valid file type. It should be one of {cls.hint_dict()}"
                logger.error(_msg)
                raise ValueError(_msg)
            _set.add(cls(_c))
        return _set

    @classmethod
    def from_path(cls, p: Path) -> FileTypeE:
        if p.is_char_device():
            return cls.char_unbuffered_special
        elif p.is_dir():
            return cls.directory
        elif p.is_symlink():
            return cls.symbolic_link
        elif p.is_socket():
            return cls.socket
        elif p.is_mount():
            return cls.mount
        elif p.is_block_device():
            return cls.block_device
        elif p.is_fifo():
            return cls.fifo
        elif p.is_file():
            return cls.regular_file
        else:
            _msg: str = f"Cannot decide type of {p}"
            logger.error(_msg)
            raise ValueError(_msg)
    
    @staticmethod
    def is_text_file(p: Path) -> bool:
        _mime_ftype: str = magic.from_file(p, mime=True)
        if _mime_ftype.startswith("text"):
            return True
        else:
            return False
    
    @staticmethod
    def mime_type(p: Path) -> str:
        return magic.from_file(p, mime=True)