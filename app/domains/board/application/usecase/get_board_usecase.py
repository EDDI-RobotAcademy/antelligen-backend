from app.common.exception.app_exception import AppException
from app.domains.board.application.port.out.board_repository_port import BoardRepositoryPort
from app.domains.board.application.response.read_board_response import ReadBoardResponse


class GetBoardUseCase:
    def __init__(self, board_repository: BoardRepositoryPort):
        self._repo = board_repository

    async def execute(self, board_id: int, nickname: str) -> ReadBoardResponse:
        board = await self._repo.find_by_id(board_id)
        if not board:
            raise AppException(status_code=404, message="게시물을 찾을 수 없습니다.")
        return ReadBoardResponse(
            board_id=board.board_id,
            title=board.title,
            content=board.content,
            nickname=nickname,
            created_at=board.created_at,
            updated_at=board.updated_at,
        )
