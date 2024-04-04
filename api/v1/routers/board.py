from typing_extensions import Annotated, Dict, List
from fastapi import (
    APIRouter, Depends, Request, Path, HTTPException,
    status, UploadFile, File, Form, Body
)
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder

from core.database import db_session
from core.models import Board, Group, Member
from lib.board_lib import insert_board_new, set_write_delay
from lib.dependencies import common_search_query_params
from api.v1.models import responses
from api.v1.dependencies.board import (
    get_current_member, get_board, get_group,
    validate_write
)
from api.v1.models.board import WriteModel, CommentModel, ResponseWriteModel, ResponseBoardModel
from service.board import(
    ListPostServiceAPI, CreatePostServiceAPI, ReadPostServiceAPI,
    UpdatePostServiceAPI, DeletePostServiceAPI, GroupBoardListServiceAPI,
    CommentServiceAPI, DeleteCommentServiceAPI, ListDeleteServiceAPI,
    MoveUpdateServiceAPI, DownloadFileServiceAPI
)


router = APIRouter()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

@router.get("/group/{gr_id}",
            summary="게시판그룹 목록 조회",
            responses={**responses}
            )
async def api_group_board_list(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    group: Annotated[Group, Depends(get_group)],
    gr_id: str = Path(...),
) -> Dict:
    """
    게시판그룹의 모든 게시판 목록을 보여줍니다.
    """
    group_board_list_service = GroupBoardListServiceAPI(
        request, db, gr_id, member
    )
    group = group_board_list_service.group
    group_board_list_service.check_mobile_only()
    boards = group_board_list_service.get_boards_in_group()

    # 데이터 유효성 검증 및 불필요한 데이터 제거한 게시판 목록 얻기
    filtered_boards = []
    for board in boards:
        board_json = jsonable_encoder(board)
        board_api = ResponseBoardModel.model_validate(board_json)
        filtered_boards.append(board_api)

    return jsonable_encoder({"group": group, "boards": filtered_boards})


@router.get("/{bo_table}",
            summary="게시판 조회",
            responses={**responses}
            )
async def api_list_post(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    search_params: Annotated[dict, Depends(common_search_query_params)],
    bo_table: str = Path(...),
) -> Dict:
    """
    게시판 정보, 글 목록을 반환합니다.
    """
    list_post_service = ListPostServiceAPI(
        request, db, bo_table, board, member, search_params
    )

    board_json = jsonable_encoder(board)
    board = ResponseBoardModel.model_validate(board_json)

    content = {
        "categories": list_post_service.categories,
        "board": board,
        "writes": list_post_service.get_writes(search_params),
        "total_count": list_post_service.get_total_count(),
        "current_page": search_params['current_page'],
        "prev_spt": list_post_service.prev_spt,
        "next_spt": list_post_service.next_spt,
    }
    
    return jsonable_encoder(content)


@router.get("/{bo_table}/{wr_id}",
            summary="게시판 개별 글 조회",
            response_model=ResponseWriteModel,
            responses={**responses}
            )
async def api_read_post(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    member: Annotated[Member, Depends(get_current_member)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글을 개별 조회합니다.
    """
    read_post_service = ReadPostServiceAPI(
        request, db, bo_table, board, wr_id, member
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
             responses={**responses}
             )
async def api_create_post(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    wr_data: Annotated[WriteModel, Depends(validate_write)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
) -> Dict:
    """
    지정된 게시판에 새 글을 작성합니다.
    """
    create_post_service = CreatePostServiceAPI(
        request, db, bo_table, board, member
    )
    create_post_service.validate_secret_board(wr_data.secret, wr_data.html, wr_data.mail)
    create_post_service.validate_post_content(wr_data.wr_subject)
    create_post_service.validate_post_content(wr_data.wr_content)
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
    db.commit()
    return {"result": "created"}
    

@router.put("/{bo_table}/{wr_id}",
            summary="게시판 글 수정",
            responses={**responses}
            )
async def api_update_post(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    wr_data: Annotated[WriteModel, Depends(validate_write)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글을 수정합니다.
    """
    update_post_service = UpdatePostServiceAPI(
        request, db, bo_table, board, member, wr_id
    )
    update_post_service.validate_restrict_comment_count()
    write = update_post_service.get_write(update_post_service.wr_id)
    
    update_post_service.validate_author(write)
    update_post_service.validate_secret_board(wr_data.secret, wr_data.html, wr_data.mail)
    update_post_service.validate_post_content(wr_data.wr_subject)
    update_post_service.validate_post_content(wr_data.wr_content)
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
                responses={**responses}
               )
async def api_delete_post(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글을 삭제합니다.
    """
    delete_post_api = DeletePostServiceAPI(
        request, db, bo_table, board, wr_id, member
    )
    delete_post_api.validate_level(with_session=False)
    delete_post_api.validate_exists_reply()
    delete_post_api.validate_exists_comment()
    delete_post_api.delete_write()
    return {"result": "deleted"}


@router.post("/list_delete/{bo_table}",
            summary="게시글 일괄 삭제",
            responses={**responses}
            )
async def api_list_delete(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    wr_ids: Annotated[list, Body(..., alias="chk_wr_id[]")],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
):
    """
    게시글을 일괄 삭제합니다.
    - wr_ids: 삭제할 게시글 wr_id 리스트
    """
    list_delete_service = ListDeleteServiceAPI(
        request, db, bo_table, board, member
    )
    list_delete_service.validate_admin_authority()
    list_delete_service.delete_writes(wr_ids)
    return {"result": "deleted"}


@router.post("/move_update/{bo_table}",
            summary="게시글 복사/이동",
            responses={**responses}
            )
async def api_move_update(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    sw: str = Body(...),
    wr_ids: str = Body(...),
    target_bo_tables: list = Body(...),
):
    """
    게시글을 복사/이동합니다.
    - Scrap, File등 연관된 데이터들도 함께 수정합니다.
    """
    move_update_service = MoveUpdateServiceAPI(
        request, db, bo_table, board, member, sw
    )
    move_update_service.validate_admin_authority()
    origin_writes = move_update_service.get_origin_writes(wr_ids)
    move_update_service.move_copy_post(target_bo_tables, origin_writes)
    return {"result": f"해당 게시물을 선택한 게시판으로 {move_update_service.act} 하였습니다."}
 

@router.post("/uploadfile/{bo_table}/{wr_id}",
            summary="파일 업로드",
            responses={**responses}
            )
async def api_upload_file(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
    files: List[UploadFile] = File(...),
    file_content: list = Form(None),
    file_dels: list = Form(None),
) -> Dict:
    """
    파일을 업로드합니다.
    """
    if not member:
        raise HTTPException(status_code=403, detail="로그인 후 이용해주세요.")

    create_post_service = CreatePostServiceAPI(
        request, db, bo_table, board, member
    )
    write = create_post_service.get_write(wr_id)
    create_post_service.upload_files(write, files, file_content, file_dels)
    return {"result": "uploaded"}


@router.post("/{bo_table}/{wr_id}/download/{bf_no}",
            summary="파일 다운로드",
            responses={**responses}
            )
async def api_download_file(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    bf_no: int = Path(...),
):
    """
    게시글의 파일을 다운로드합니다.
    bo_table: 게시글 테이블명
    wr_id: 게시글 아이디
    bf_no: 첨부된 파일의 순번
    """
    download_file_service = DownloadFileServiceAPI(
        request, db, bo_table, board, request.state.login_member, wr_id, bf_no
    )
    download_file_service.validate_download_level()
    board_file = download_file_service.get_board_file()
    download_file_service.validate_point(board_file)
    return FileResponse(board_file.bf_file, filename=board_file.bf_source)


@router.post("/{bo_table}/{wr_parent}/comment",
            summary="댓글 작성",
            responses={**responses}
            )
async def api_create_comment(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    comment_data: CommentModel,
    bo_table: str = Path(...),
    wr_parent: str = Path(...),
):
    """
    댓글 등록
    """
    comment_service = CommentServiceAPI(
        request, db, bo_table, board, member
    )
    parent_write = comment_service.get_parent_post(wr_parent, is_reply=False)
    comment_service.validate_comment_level()
    comment_service.validate_point()
    comment_service.validate_post_content(comment_data.wr_content)
    comment = comment_service.save_comment(comment_data, parent_write)
    comment_service.add_point(comment)
    comment_service.send_write_mail_(comment, parent_write)
    insert_board_new(bo_table, comment)
    db.commit()
    return {"result": "created"}


@router.put("/{bo_table}/{wr_parent}/comment/{wr_id}",
            summary="댓글 수정",
            responses={**responses}
            )
async def api_update_comment(
    request: Request,
    db: db_session,
    comment_data: CommentModel,
    board: Annotated[Board, Depends(get_board)],
    member: Annotated[Member, Depends(get_current_member)],
    bo_table: str = Path(...),
    wr_parent: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    댓글을 수정합니다.
    """
    comment_service = CommentServiceAPI(
        request, db, bo_table, board, member, wr_id
    )
    write_model = comment_service.write_model
    comment_service.get_parent_post(wr_parent, is_reply=False)
    comment = db.get(write_model, wr_id)
    if not comment:
        raise HTTPException(status_code=404, detail=f"{wr_id} : 존재하지 않는 댓글입니다.")

    comment_service.validate_author(comment)
    comment_service.validate_post_content(comment_data.wr_content)
    comment.wr_content = comment_service.get_cleaned_data(comment_data.wr_content)
    comment.wr_option = comment_data.wr_option or "html1"
    comment.wr_last = comment_service.g5_instance.get_wr_last_now(write_model.__tablename__)
    db.commit()

    return {"result": "updated"}


@router.delete("/{bo_table}/{wr_parent}/comment/{wr_id}",
                summary="댓글 삭제",
                responses={**responses}
               )
async def api_delete_comment(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
):
    """
    댓글을 삭제합니다.
    """
    delete_comment_service = DeleteCommentServiceAPI(
        request, db, bo_table, board, wr_id, member
    )
    delete_comment_service.check_authority(with_session=False)
    delete_comment_service.delete_comment()
    return {"result": "deleted"}