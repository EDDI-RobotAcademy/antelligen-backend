import asyncio
import re
from pathlib import Path
from typing import Optional, Set

from app.domains.study.application.port.out.study_note_reader_port import StudyNoteReaderPort

_DEFAULT_PATH = Path(__file__).resolve().parents[5].parent / "study.md"
_VIDEO_ID_PATTERN = re.compile(r"video_id:\s*`([A-Za-z0-9_\-]{6,})`")


class StudyNoteFileReader(StudyNoteReaderPort):
    def __init__(self, file_path: Optional[Path] = None):
        self._file_path = file_path or _DEFAULT_PATH

    async def existing_video_ids(self) -> Set[str]:
        print(f"[study.reader] 기존 노트 파싱 path={self._file_path}")
        ids = await asyncio.to_thread(self._read_sync)
        print(f"[study.reader] 기존 video_id 수 = {len(ids)}")
        return ids

    def _read_sync(self) -> Set[str]:
        if not self._file_path.exists() or not self._file_path.is_file():
            return set()
        content = self._file_path.read_text(encoding="utf-8")
        return set(_VIDEO_ID_PATTERN.findall(content))
