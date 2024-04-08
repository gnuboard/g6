"""스크랩 API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Path

from core.models import Board, Member, WriteBaseModel
from lib.common import get_paging_info

from api.v1.dependencies.board import get_board, get_write
from api.v1.dependencies.member import get_current_member
from api.v1.dependencies.scrap import validate_create_scrap
from api.v1.lib.scrap import ScrapServiceAPI
from api.v1.models import ViewPageModel, responses
from api.v1.models.scrap import CreateScrapModel, ResponseScrapListModel

router = APIRouter()


@router.get("/scraps",
            summary="회원 스크랩 목록 조회",
            response_model=ResponseScrapListModel,
            responses={**responses})
async def read_member_scraps(
    scrap_service: Annotated[ScrapServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[ViewPageModel, Depends()]
):
    """회원 스크랩 목록을 조회합니다."""
    total_records = scrap_service.fetch_total_records(member)
    paging_info = get_paging_info(data.page, data.per_page, total_records)
    scraps = scrap_service.fetch_scraps(member,
                                        paging_info["offset"], data.per_page)
    scraps = scrap_service.set_subjects(scraps)

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "scraps": scraps
    }


@router.get("/scraps/{bo_table}/{wr_id}",
            dependencies=[Depends(validate_create_scrap)])
async def scrap_form(
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
):
    """
    스크랩 등록 페이지 설정 조회
    """
    return {
        "board": board,
        "write": write,
    }


@router.post("/scraps/{bo_table}/{wr_id}",
             dependencies=[Depends(validate_create_scrap)],
             summary="회원 스크랩 등록",
             responses={**responses})
async def create_member_scrap(
    scrap_service: Annotated[ScrapServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    data: Annotated[CreateScrapModel, Depends()]
):
    """
    회원 스크랩 등록
    TODO: 댓글 등록 프로세스를 템플릿 부분과 통합해야함
    """
    bo_table = board.bo_table
    wr_id = write.wr_id

    scrap_service.create_scrap(member, bo_table, wr_id)
    scrap_service.update_scrap_count(member)

    # # 댓글 추가 => 공용 코드로 분리
    # if data.wr_content and board_config.is_comment_level():
    #     # 글쓰기 간격 검증
    #     if not is_write_delay(request):
    #         raise AlertException("너무 빠른 시간내에 게시글을 연속해서 올릴 수 없습니다.", 400)

    #     max_comment = db.scalar(
    #         select(func.max(write_model.wr_comment).label('max_comment'))
    #         .where(write_model.wr_parent == wr_id, write_model.wr_is_comment == 1)
    #     )
    #     # TODO: 게시글/댓글을 등록하는 공용함수를 만들어서 사용하도록 수정
    #     comment_model = dynamic_create_write_table(bo_table)
    #     comment = comment_model(
    #         mb_id=member.mb_id,
    #         wr_content=data.wr_content,
    #         ca_name=write.ca_name,
    #         wr_option="",
    #         wr_num=write.wr_num,
    #         wr_reply="",
    #         wr_parent=wr_id,
    #         wr_comment=max_comment + 1 if max_comment else 1,
    #         wr_is_comment=1,
    #         wr_name=board_config.set_wr_name(member),
    #         wr_password=member.mb_password,
    #         wr_email=member.mb_email,
    #         wr_homepage=member.mb_homepage,
    #         wr_datetime=datetime.now(),
    #         wr_ip=request.client.host,
    #     )
    #     db.add(comment)
    #     db.commit()

    #     # 글 작성 시간 기록
    #     set_write_delay(request)

    #     # 게시판&스크랩 글에 댓글 수 증가
    #     board.bo_count_comment += 1
    #     write.wr_comment += 1

    #     # 새글 테이블에 추가
    #     insert_board_new(board.bo_table, comment)

    #     # 포인트 부여
    #     insert_point(request, member.mb_id, board.bo_comment_point,
    #                  f"{board.bo_subject} {write.wr_id}-{comment.wr_id} 댓글쓰기(스크랩)", board.bo_table, comment.wr_id,
    #                  '댓글')
    #     db.commit()

    #    # 최신글 캐시 삭제
    #    FileCache().delete_prefix(f'latest-{bo_table}')

    return {"detail": "스크랩을 추가하였습니다."}


@router.delete("/scraps/{ms_id}",
               summary="회원 스크랩 삭제",
               responses={**responses})
async def delete_member_scrap(
    scrap_service: Annotated[ScrapServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    ms_id: Annotated[int, Path(title="스크랩 아이디")]
):
    """회원 스크랩을 삭제합니다."""
    scrap_service.delete_scrap(ms_id, member)
    scrap_service.update_scrap_count(member)

    return {"detail": "스크랩을 삭제하였습니다."}
