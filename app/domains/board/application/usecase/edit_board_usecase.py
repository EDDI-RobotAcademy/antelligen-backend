from app.common.exception.app_exception import AppException
from app.domains.board.application.port.out.board_repository_port import BoardRepositoryPort
from app.domains.board.application.request.edit_board_request import EditBoardRequest
from app.domains.board.application.response.edit_board_response import EditBoardResponse


class EditBoardUseCase:
    def __init__(self, board_repository: BoardRepositoryPort):
        self._repo = board_repository

    async def execute(self, board_id: int, account_id: int, nickname: str, request: EditBoardRequest) -> EditBoardResponse:
        board = await self._repo.find_by_id(board_id)
        if not board:
            raise AppException(status_code=404, message="게시물을 찾을 수 없습니다.")

        if board.account_id != account_id:
            raise AppException(status_code=403, message="본인이 작성한 게시물만 수정할 수 있습니다.")

        board.title = request.title
        board.content = request.content

        updated = await self._repo.update(board)
        return EditBoardResponse(
            board_id=updated.board_id,
            title=updated.title,
            content=updated.content,
            nickname=nickname,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
