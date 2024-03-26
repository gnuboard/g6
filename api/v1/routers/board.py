from typing_extensions import Annotated, Dict, List

from fastapi import APIRouter, Depends, Request, Path, HTTPException, status, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, update

from core.database import db_session
from core.models import Board, Group, WriteBaseModel, Member
from lib.board_lib import (
    BoardConfig, generate_reply_character,
    insert_board_new, send_write_mail, set_write_delay
)
from lib.common import dynamic_create_write_table
from lib.dependencies import common_search_query_params
from lib.member_lib import get_admin_type
from lib.point import insert_point
from lib.g5_compatibility import G5Compatibility
from api.v1.dependencies.board import (
    get_current_member, get_member_info, get_board, get_group,
    validate_write,
    validate_comment, validate_update_comment, validate_delete_comment,
    validate_upload_file_write, get_write, get_parent_write
)
from api.v1.models.board import WriteModel, CommentModel, ResponseWriteModel
from response_handlers.board import(
    ListPostServiceAPI, CreatePostServiceAPI, ReadPostServiceAPI,
    UpdatePostServiceAPI, DeletePostAPI
)


router = APIRouter()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

@router.get("/group/{gr_id}",
            summary="게시판그룹 목록 조회",
            response_description="게시판그룹 목록을 반환합니다."
            )
async def api_group_board_list(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    group: Annotated[Group, Depends(get_group)],
    gr_id: str = Path(...),
) -> Dict:
    """
    게시판그룹의 모든 게시판 목록을 보여줍니다.
    """
    mb_id = member_info["mb_id"]
    member_level = member_info["member_level"]
    admin_type = get_admin_type(request, mb_id, group=group)

    # 그룹별 게시판 목록 조회
    query = (
        select(Board)
        .where(
            Board.gr_id == gr_id,
            Board.bo_list_level <= member_level,
            Board.bo_device != 'mobile'
        )
        .order_by(Board.bo_order)
    )
    # 인증게시판 제외
    if not admin_type:
        query = query.filter_by(bo_use_cert="")

    boards = db.scalars(query).all()
    return jsonable_encoder({"group": group, "boards": boards})


@router.get("/{bo_table}",
            summary="게시판 조회",
            response_description="게시판 정보, 글 목록을 반환합니다."
            )
async def api_list_post(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    board: Annotated[Board, Depends(get_board)],
    search_params: Annotated[dict, Depends(common_search_query_params)],
    bo_table: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글 목록을 보여줍니다.
    """
    list_post_service = ListPostServiceAPI(
        request, db, bo_table, board, member_info["member"], search_params
    )

    content = {
        "categories": list_post_service.categories,
        "board": list_post_service.board,
        "writes": list_post_service.get_writes(search_params),
        "total_count": list_post_service.get_total_count(),
        "current_page": search_params['current_page'],
        "prev_spt": list_post_service.prev_spt,
        "next_spt": list_post_service.next_spt,
    }
    
    return jsonable_encoder(content)



@router.get("/{bo_table}/{wr_id}",
            summary="게시판 개별 글 조회",
            response_description="게시판 개별 글을 반환합니다.",
            response_model=ResponseWriteModel,
            )
async def api_read_post(
    request: Request,
    db: db_session,
    write: Annotated[WriteBaseModel, Depends(get_write)],
    board: Annotated[Board, Depends(get_board)],
    member: Annotated[Member, Depends(get_current_member)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글을 개별 조회합니다.
    """
    read_post_service = ReadPostServiceAPI(
        request, db, bo_table, board, wr_id, write, member
    )
    content = jsonable_encoder(read_post_service.write)
    additional_content = jsonable_encoder({
        "images": read_post_service.images,
        "normal_files": read_post_service.normal_files,
        "links": read_post_service.get_links(),
        "comments": read_post_service.get_comments(),
    })
    content.update(additional_content)
    read_post_service.validate_secret()
    read_post_service.validate_repeat()
    read_post_service.block_read_comment()
    read_post_service.validate_read_level()
    read_post_service.check_scrap()
    read_post_service.check_is_good()
    model_validated_content = ResponseWriteModel.model_validate(content)
    db.commit()
    return model_validated_content


@router.post("/{bo_table}",
             summary="게시판 글 작성",
             response_description="글 작성 성공 여부를 반환합니다."
             )
async def api_create_post(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    wr_data: Annotated[WriteModel, Depends(validate_write)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
) -> Dict:
    """
    지정된 게시판에 새 글을 작성합니다.
    """
    create_post_service = CreatePostServiceAPI(
        request, db, bo_table, board, member_info["member"]
    )
    create_post_service.validate_secret_board(wr_data.secret, wr_data.html, wr_data.mail)
    create_post_service.validate_post_content(wr_data.wr_subject, wr_data.wr_content)
    create_post_service.is_write_level()
    create_post_service.arrange_data(wr_data, wr_data.secret, wr_data.html, wr_data.mail)
    write = create_post_service.save_write(wr_data.parent_id, wr_data)
    insert_board_new(bo_table, write)
    create_post_service.add_point(write)
    create_post_service.send_write_mail_(write, wr_data.parent_id)
    create_post_service.set_notice(write.wr_id, wr_data.notice)
    set_write_delay(create_post_service.request)
    create_post_service.save_secret_session(write.wr_id, wr_data.secret)
    create_post_service.delete_cache()
    redirect_url = create_post_service.get_redirect_url(write)
    db.commit()
    return RedirectResponse(redirect_url, status_code=303)
    

@router.put("/{bo_table}/{wr_id}",
            summary="게시판 글 수정",
            response_description="글 수정 성공 여부를 반환합니다."
            )
async def api_update_post(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    wr_data: Annotated[WriteModel, Depends(validate_write)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글을 수정합니다.
    """
    update_post_service = UpdatePostServiceAPI(
        request, db, bo_table, board, member_info["member"], wr_id
    )
    update_post_service.validate_restrict_comment_count()
    write = get_write(update_post_service.db, update_post_service.bo_table, update_post_service.wr_id)
    
    update_post_service.validate_secret_board(wr_data.secret, wr_data.html, wr_data.mail)
    update_post_service.validate_post_content(wr_data.wr_subject, wr_data.wr_content)
    update_post_service.arrange_data(wr_data, wr_data.secret, wr_data.html, wr_data.mail)
    update_post_service.save_secret_session(wr_id, wr_data.secret)
    update_post_service.save_write(write, wr_data)
    update_post_service.set_notice(write.wr_id, wr_data.notice)
    update_post_service.update_children_category(wr_data)
    update_post_service.delete_cache()
    db.commit()
    return {"result": "updated"}


@router.delete("/{bo_table}/{wr_id}",
                summary="게시판 글 삭제",
                response_description="글 삭제 성공 여부를 반환합니다."
               )
async def api_delete_post(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글을 삭제합니다.
    """
    delete_post_api = DeletePostAPI(
        request, db, bo_table, board, wr_id, write, member_info["member"]
    )
    return delete_post_api.response()


@router.post("/uploadfile/{bo_table}/{wr_id}",
            summary="파일 업로드",
            response_description="파일 업로드 성공 여부를 반환합니다."
            )
async def api_upload_file(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(validate_upload_file_write)],
    bo_table: str = Path(...),
    files: List[UploadFile] = File(..., alias="bf_file[]"),
    file_content: list = Form(None, alias="bf_content[]"),
    file_dels: list = Form(None, alias="bf_file_del[]"),
) -> Dict:
    """
    파일 업로드
    """
    create_post_service = CreatePostServiceAPI(
        request, db, bo_table, board, member_info["member"]
    )
    create_post_service.upload_files(write, files, file_content, file_dels)
    return {"result": "uploaded"}


@router.post("/{bo_table}/{wr_parent}/comment",
            summary="댓글 작성",
            response_description="댓글 작성 성공 여부를 반환합니다."
            )
async def api_create_comment(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    board: Annotated[Board, Depends(get_board)],
    comment_data: Annotated[CommentModel, Depends(validate_comment)],
    parent_write: Annotated[WriteBaseModel, Depends(get_parent_write)],
    bo_table: str = Path(...),
    wr_parent: str = Path(...),
):
    """
    댓글 등록
    """
    board_config = BoardConfig(request, board)
    member = member_info["member"]
    mb_id = member_info["mb_id"] or ""
    write_model = dynamic_create_write_table(bo_table)

    # 댓글 객체 생성
    comment = write_model()

    if comment_data.comment_id:
        parent_comment = db.get(write_model, comment_data.comment_id)
        if not parent_comment:
            raise HTTPException(status_code=404, detail=f"{comment_data.comment_id} : 존재하지 않는 댓글입니다.")

        comment.wr_comment_reply = generate_reply_character(board, parent_comment)
        comment.wr_comment = parent_comment.wr_comment
    else:
        comment.wr_comment = db.scalar(
            select(func.coalesce(func.max(write_model.wr_comment), 0) + 1)
            .where(
                write_model.wr_parent == wr_parent,
                write_model.wr_is_comment == 1
            )
        )

    comment_data_dict = comment_data.model_dump()
    for key, value in comment_data_dict.items():
        setattr(comment, key, value)

    db.add(comment)

    # 게시글에 댓글 수 증가
    parent_write.wr_comment += 1
    db.commit()

    # 새글 추가
    insert_board_new(bo_table, comment)

    # 포인트 처리
    if member:
        insert_point(request, mb_id, board.bo_comment_point, f"{board.bo_subject} {wr_parent}-{comment.wr_id} 댓글쓰기", board.bo_table, comment.wr_id, "댓글")

    # 메일 발송
    if board_config.use_email:
        send_write_mail(request, board, comment, parent_write)

    return {"result": "created"}


@router.put("/{bo_table}/{wr_parent}/comment/{wr_id}",
            summary="댓글 수정",
            response_description="댓글 수정 성공 여부를 반환합니다."
            )
async def api_update_comment(
    request: Request,
    db: db_session,
    comment_data: Annotated[CommentModel, Depends(validate_update_comment)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    댓글 수정
    """
    write_model = dynamic_create_write_table(bo_table)

    # 댓글 수정
    comment = db.get(write_model, wr_id)
    if not comment:
        raise HTTPException(status_code=404, detail=f"{wr_id} : 존재하지 않는 댓글입니다.")

    comment_data_dict = comment_data.model_dump()

    # 수정시 작성자명이 변경되지 않도록 wr_name 제거
    del comment_data_dict["wr_name"]

    for key, value in comment_data_dict.items():
        setattr(comment, key, value)

    # 댓글 wr_last의 경우 gnuboard5와의 호환성을 위해 아래와 같이 now를 받아옴
    compatible_instance = G5Compatibility(db)
    now = compatible_instance.get_wr_last_now(write_model.__tablename__)
    comment.wr_last = now

    comment.wr_ip = request.client.host

    db.commit()

    return {"result": "updated"}


@router.delete("/{bo_table}/{wr_parent}/comment/{wr_id}",
                summary="댓글 삭제",
                response_description="댓글 삭제 성공 여부를 반환합니다."
               )
async def api_delete_comment(
    db: db_session,
    comment: Annotated[WriteBaseModel, Depends(validate_delete_comment)],
    bo_table: str = Path(...),
):
    """
    댓글 삭제
    """
    write_model = dynamic_create_write_table(bo_table)

    # 댓글 삭제
    db.delete(comment)

    # 게시글에 댓글 수 감소
    db.execute(
        update(write_model).values(wr_comment=write_model.wr_comment - 1)
        .where(write_model.wr_id == comment.wr_parent)
    )

    db.commit()

    return {"result": "deleted"}