import asyncio
from pathlib import Path
from typing import Optional

from app.domains.study.application.port.out.study_note_writer_port import StudyNoteWriterPort

_DEFAULT_PATH = Path(__file__).resolve().parents[5].parent / "study.md"
_HEADER = (
    "# 학습 노트\n\n"
    "study(UC2-YdiOkgqWzIdDwCYW1utw)의 '학습프로그램' 중 'back to the basic' / "
    "'리듬 시리즈' 영상 학습 결과를 누적 기록한다.\n\n"
)


class StudyNoteFileWriter(StudyNoteWriterPort):
    def __init__(self, file_path: Optional[Path] = None):
        self._file_path = file_path or _DEFAULT_PATH

    async def append(self, markdown: str) -> str:
        print(f"[study.writer] 파일 append 요청 path={self._file_path} 추가 길이={len(markdown)}자")
        path = await asyncio.to_thread(self._append_sync, markdown)
        print(f"[study.writer] 파일 append 완료 path={path}")
        return path

    def _append_sync(self, markdown: str) -> str:
        path = self._file_path
        path.parent.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            path.write_text(_HEADER + markdown, encoding="utf-8")
            return str(path)

        existing = path.read_text(encoding="utf-8")
        separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        with path.open("a", encoding="utf-8") as f:
            f.write(separator)
            f.write(markdown)
        return str(path)
