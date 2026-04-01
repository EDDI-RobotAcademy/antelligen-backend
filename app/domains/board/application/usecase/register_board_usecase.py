from app.domains.board.application.port.out.board_repository_port import BoardRepositoryPort
from app.domains.board.application.request.register_board_request import RegisterBoardRequest
from app.domains.board.application.response.register_board_response import RegisterBoardResponse
from app.domains.board.domain.entity.board import Board


class RegisterBoardUseCase:
    def __init__(self, board_repository: BoardRepositoryPort):
        self._repo = board_repository

    async def execute(self, account_id: int, request: RegisterBoardRequest) -> RegisterBoardResponse:
        board = Board(
            board_id=None,
            title=request.title,
            content=request.content,
            account_id=account_id,
            created_at=None,
            updated_at=None,
        )
        saved = await self._repo.save(board)
        return RegisterBoardResponse(
            board_id=saved.board_id,
            title=saved.title,
            content=saved.content,
            account_id=saved.account_id,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )
