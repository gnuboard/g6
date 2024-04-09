"""스크랩 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Path, Query, Request
from fastapi.responses import RedirectResponse

from core.models import Board, Member, WriteBaseModel
from core.template import UserTemplates
from lib.common import get_paging_info, remove_query_params, set_url_query_params
from lib.dependencies import get_board, get_write, validate_token
from lib.dependency.auth import get_login_member
from lib.dependency.scrap import validate_create_scrap
from lib.template_filters import datetime_format
from lib.template_functions import get_paging
from service.scrap_service import ScrapService

router = APIRouter()
templates = UserTemplates()
templates.env.filters["datetime_format"] = datetime_format


@router.get("/scrap_popin/{bo_table}/{wr_id}",
            dependencies=[Depends(validate_create_scrap)])
async def scrap_form(
    request: Request,
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
):
    """
    스크랩 등록 폼(팝업창)
    """
    context = {
        "request": request,
        "bo_table": board.bo_table,
        "write": write,
    }
    return templates.TemplateResponse("bbs/scrap_popin.html", context)


@router.post("/scrap_popin_update/{bo_table}/{wr_id}",
             dependencies=[Depends(validate_create_scrap),
                           Depends(validate_token)])
async def scrap_form_update(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    scrap_service: Annotated[ScrapService, Depends()],
    wr_content: str = Form(None),
):
    """
    회원 스크랩 등록
    """
    bo_table = board.bo_table
    wr_id = write.wr_id

    scrap_service.create_scrap(member, bo_table, wr_id)
    scrap_service.update_scrap_count(member)

    # # 댓글 추가 => 공용 코드로 분리
    # if wr_content and board_config.is_comment_level():
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
    #         wr_content=wr_content,
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
    #     insert_board_new(bo_table, comment)

    #     # 포인트 부여
    #     content = f"{board.bo_subject} {write.wr_id}-{comment.wr_id} 댓글쓰기(스크랩)"
    #     insert_point(request, member.mb_id, board.bo_comment_point,
    #                  content, board.bo_table, comment.wr_id, '댓글')

    #     db.commit()

    #     # 최신글 캐시 삭제
    #     FileCache().delete_prefix(f'latest-{bo_table}')

    return RedirectResponse(request.url_for('scrap_list'), 302)


@router.get("/scrap")
async def scrap_list(
    request: Request,
    scrap_service: Annotated[ScrapService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    current_page: int = Query(default=1, alias="page")
):
    """
    스크랩 목록
    """
    config = request.state.config
    page_rows = getattr(config, "cf_page_rows", 10)

    total_records = scrap_service.fetch_total_records(member)
    paging_info = get_paging_info(current_page, page_rows, total_records)
    scraps = scrap_service.fetch_scraps(member,
                                        paging_info["offset"], page_rows)
    scraps = scrap_service.set_subjects(scraps)

    for scrap in scraps:
        scrap.num = (total_records
                     - paging_info["offset"]
                     - (scraps.index(scrap)))

    context = {
        "request": request,
        "scraps": scraps,
        "total_records": total_records,
        "page": current_page,
        "paging": get_paging(request, current_page, total_records),
    }
    return templates.TemplateResponse("bbs/scrap_list.html", context)


@router.get("/scrap_delete/{ms_id}", dependencies=[Depends(validate_token)])
async def scrap_delete(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    scrap_service: Annotated[ScrapService, Depends()],
    ms_id: int = Path(...)
):
    """
    스크랩 삭제
    """
    scrap_service.delete_scrap(ms_id, member)
    scrap_service.update_scrap_count(member)

    url = request.url_for('scrap_list').path
    query_params = remove_query_params(request, "token")
    return RedirectResponse(set_url_query_params(url, query_params), 302)
