import asyncio
from pathlib import Path
from typing import Optional

from app.domains.macro.application.port.out.study_note_port import StudyNotePort

_DEFAULT_PATH = Path(__file__).resolve().parents[5].parent / "study.md"


class StudyNoteFileReader(StudyNotePort):
    def __init__(self, file_path: Optional[Path] = None):
        self._file_path = file_path or _DEFAULT_PATH

    async def read(self) -> str:
        print(f"[macro.note_reader] 파일 읽기 시도 path={self._file_path}")
        text = await asyncio.to_thread(self._read_sync)
        print(f"[macro.note_reader] 읽은 길이 = {len(text)}자")
        return text

    def _read_sync(self) -> str:
        path = self._file_path
        if not path.exists() or not path.is_file():
            print(f"[macro.note_reader] ⚠ 파일 미존재 path={path}")
            return ""
        return path.read_text(encoding="utf-8")
