from typing_extensions import Annotated, List
from fastapi import (
    APIRouter, Depends, Request, Path, HTTPException,
    status, UploadFile, File, Form, Body
)
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder

from core.database import db_session
from core.models import Member
from lib.board_lib import insert_board_new, set_write_delay
from api.v1.models.response import (
    response_401, response_403, response_404, response_422
)
from api.v1.dependencies.member import get_current_member
from api.v1.models.board import (
    WriteModel, CommentModel, ResponseWriteModel, ResponseBoardModel,
    ResponseBoardListModel, ResponseGroupBoardsModel, ResponseNormalModel
)
from api.v1.lib.board import (
    GroupBoardListServiceAPI, ListPostServiceAPI, ReadPostServiceAPI,
    CreatePostServiceAPI, UpdatePostServiceAPI, DownloadFileServiceAPI,
    DeletePostServiceAPI, CommentServiceAPI, DeleteCommentServiceAPI,
    MoveUpdateServiceAPI
)
from service.board import(
    ListDeleteServiceAPI,
)


router = APIRouter()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

@router.get("/group/{gr_id}",
            summary="게시판그룹 목록 조회",
            responses={**response_401, **response_422}
            )
async def api_group_board_list(
    group_board_list_service: Annotated[GroupBoardListServiceAPI, Depends()],
) -> ResponseGroupBoardsModel:
    """
    게시판그룹의 모든 게시판 목록을 보여줍니다.
    """
    group = group_board_list_service.group
    group_board_list_service.check_mobile_only()
    boards = group_board_list_service.get_boards_in_group()
    return {"group": group, "boards": boards}


@router.get("/{bo_table}",
            summary="게시판 조회",
            responses={**response_401, **response_422}
            )
async def api_list_post(
    list_post_service: Annotated[ListPostServiceAPI, Depends()],
) -> ResponseBoardListModel:
    """
    게시판 정보, 글 목록을 반환합니다.
    """
    content = {
        "categories": list_post_service.categories,
        "board": list_post_service.board,
        "writes": list_post_service.get_writes(),
        "total_count": list_post_service.get_total_count(),
        "current_page": list_post_service.search_params['current_page'],
        "prev_spt": list_post_service.prev_spt,
        "next_spt": list_post_service.next_spt,
    }
    
    return jsonable_encoder(content)


@router.get("/{bo_table}/{wr_id}",
            summary="게시판 개별 글 조회",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_read_post(
    db: db_session,
    read_post_service: Annotated[ReadPostServiceAPI, Depends()],
) -> ResponseWriteModel:
    """
    지정된 게시판의 글을 개별 조회합니다.
    """
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
    db.commit()
    return content


@router.post("/{bo_table}",
             summary="게시판 글 작성",
             responses={**response_401, **response_403,
                        **response_404, **response_422}
             )
async def api_create_post(
    db: db_session,
    create_post_service: Annotated[CreatePostServiceAPI, Depends()],
    wr_data: WriteModel,
) -> ResponseNormalModel:
    """
    지정된 게시판에 새 글을 작성합니다.

    ### Request Body
    - **wr_subject**: 글 제목
    - **wr_content**: 글 내용
    - **wr_name**: 작성자 이름 (비회원일 경우)
    - **wr_password**: 비밀번호
    - **wr_email**: 작성자 메일
    - **wr_homepage**: 작성자 홈페이지
    - **wr_link1**: 링크1
    - **wr_link2**: 링크2
    - **wr_option**: 글 옵션
    - **html**: HTML 사용 여부
    - **mail**: 메일발송 여부
    - **secret**: 비밀글 여부
    - **ca_name"**: 카테고리명 
    - **notice**: 공지글 여부
    - **parent_id**: 부모글 ID (답글/댓글일 경우)
    - **wr_comment**: 댓글 사용 여부
    """
    create_post_service.validate_secret_board(wr_data.secret, wr_data.html, wr_data.mail)
    create_post_service.validate_post_content(wr_data.wr_subject)
    create_post_service.validate_post_content(wr_data.wr_content)
    create_post_service.is_write_level()
    create_post_service.arrange_data(wr_data, wr_data.secret, wr_data.html, wr_data.mail)
    write = create_post_service.save_write(wr_data.parent_id, wr_data)
    insert_board_new(create_post_service.bo_table, write)
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
            responses={**response_401, **response_403,
                        **response_404, **response_422}
            )
async def api_update_post(
    db: db_session,
    update_post_service: Annotated[UpdatePostServiceAPI, Depends()],
    wr_data: WriteModel,
    wr_id: str = Path(..., title="글 아이디", description="글 아이디"),
) -> ResponseNormalModel:
    """
    지정된 게시판의 글을 수정합니다.

    ### Request Body
    - **wr_subject**: 글 제목
    - **wr_content**: 글 내용
    - **wr_name**: 작성자 이름 (비회원일 경우)
    - **wr_password**: 비밀번호
    - **wr_email**: 작성자 메일
    - **wr_homepage**: 작성자 홈페이지
    - **wr_link1**: 링크1
    - **wr_link2**: 링크2
    - **wr_option**: 글 옵션
    - **html**: HTML 사용 여부
    - **mail**: 메일발송 여부
    - **secret**: 비밀글 여부
    - **ca_name"**: 카테고리명 
    - **notice**: 공지글 여부
    - **parent_id**: 부모글 ID (답글/댓글일 경우)
    """
    update_post_service.validate_restrict_comment_count()
    write = update_post_service.get_write(update_post_service.wr_id)
    
    update_post_service.validate_author(write, wr_data.wr_password)
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
                responses={**response_401, **response_403,
                           **response_404, **response_422}
               )
async def api_delete_post(
    delete_post_api: Annotated[DeletePostServiceAPI, Depends()],
) -> ResponseNormalModel:
    """
    지정된 게시판의 글을 삭제합니다.
    """
    delete_post_api.validate_level(with_session=False)
    delete_post_api.validate_exists_reply()
    delete_post_api.validate_exists_comment()
    delete_post_api.delete_write()
    return {"result": "deleted"}


@router.post("/list_delete/{bo_table}",
            summary="게시글 일괄 삭제",
            responses={**response_401, **response_403, **response_422}
            )
async def api_list_delete(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    wr_ids: Annotated[list, Body(..., alias="chk_wr_id[]")],
    bo_table: str = Path(..., title="게시판 테이블명", description="게시판 테이블명"),
) -> ResponseNormalModel:
    """
    게시글을 일괄 삭제합니다.
    - wr_ids: 삭제할 게시글 wr_id 리스트

    ### Request Body
    - 삭제할 게시글 리스트 (예: [1, 2, 3])
    """
    list_delete_service = ListDeleteServiceAPI(
        request, db, bo_table, member
    )
    list_delete_service.validate_admin_authority()
    list_delete_service.delete_writes(wr_ids)
    return {"result": "deleted"}


@router.post("/move/{bo_table}/{sw}",
            summary="게시글 복사/이동 가능 목록 조회",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_move_post(
    move_update_service: Annotated[MoveUpdateServiceAPI, Depends()],
) -> List[ResponseBoardModel]:
    """
    게시글을 복사/이동 가능한 게시판 목록을 반환합니다.
    sw: copy(게시글 복사) 또는 move(게시글 이동)
    """
    move_update_service.validate_admin_authority()
    boards = move_update_service.get_admin_board_list()
    return boards


@router.post("/move_update/{bo_table}/{sw}",
            summary="게시글 복사/이동",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_move_update(
    move_update_service: Annotated[MoveUpdateServiceAPI, Depends()],
    wr_ids: str = Body(..., title="글 아이디 목록"),
    target_bo_tables: list = Body(..., title="복사/이동할 게시판 테이블 목록"),
) -> ResponseNormalModel:
    """
    게시글을 복사/이동합니다.
    - Scrap, File등 연관된 데이터들도 함께 수정합니다.

    ### Request Body
    - **sw**: copy(게시글 복사) 또는 move(게시글 이동)
    - **wr_ids**: 복사/이동할 게시글 wr_id 목록 (예: "1,2,3")
    - **target_bo_tables**: 복사/이동할 게시판 목록 (예: ["free", "qa"])
    """
    move_update_service.validate_admin_authority()
    origin_writes = move_update_service.get_origin_writes(wr_ids)
    move_update_service.move_copy_post(target_bo_tables, origin_writes)
    return {"result": f"해당 게시물을 선택한 게시판으로 {move_update_service.act} 하였습니다."}
 

@router.post("/uploadfile/{bo_table}/{wr_id}",
            summary="파일 업로드",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_upload_file(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    bo_table: str = Path(..., title="게시판 테이블명", description="게시판 테이블명"),
    wr_id: str = Path(..., title="글 아이디", description="글 아이디"),
    files: List[UploadFile] = File(...),
    file_content: list = Form(None),
    file_dels: list = Form(None),
) -> ResponseNormalModel:
    """
    파일을 업로드합니다.
    - multipart/form-data로 전송해야 합니다.
    """
    create_post_service = CreatePostServiceAPI(request, db, bo_table, member)
    write = create_post_service.get_write(wr_id)
    create_post_service.upload_files(write, files, file_content, file_dels)
    return {"result": "uploaded"}


@router.post("/{bo_table}/{wr_id}/download/{bf_no}",
            summary="파일 다운로드",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_download_file(
    download_file_service: Annotated[DownloadFileServiceAPI, Depends()],
):
    """
    게시글의 파일을 다운로드합니다.
    - bo_table: 게시글 테이블명
    - wr_id: 게시글 아이디
    - bf_no: 첨부된 파일의 순번
    """
    download_file_service.validate_download_level()
    board_file = download_file_service.get_board_file()
    download_file_service.validate_point(board_file)
    return FileResponse(board_file.bf_file, filename=board_file.bf_source)


@router.post("/{bo_table}/{wr_id}/comment",
            summary="댓글 작성",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_create_comment(
    db: db_session,
    comment_service: Annotated[CommentServiceAPI, Depends()],
    comment_data: CommentModel,
    bo_table: str = Path(..., title="게시판 테이블명", description="게시판 테이블명"),
    wr_id: str = Path(..., title="부모글 아이디", description="부모글 아이디"),
) -> ResponseNormalModel:
    """
    댓글 등록

    ### Request Body
    - **wr_content**: 댓글 내용
    - **wr_name**: 작성자 이름 (비회원일 경우)
    - **wr_password**: 비밀번호
    - **wr_option**: 글 옵션
    - **wr_id**: 부모글 ID
    - **comment_id**" 댓글 ID (대댓글 작성시 댓글 id)
    wr_id만 입력 - 댓글작성
    wr_id, comment_id 입력 - 대댓글 작성
    """
    parent_write = comment_service.get_parent_post(wr_id, is_reply=False)
    comment_service.validate_comment_level()
    comment_service.validate_point()
    comment_service.validate_post_content(comment_data.wr_content)
    comment = comment_service.save_comment(comment_data, parent_write)
    comment_service.add_point(comment)
    comment_service.send_write_mail_(comment, parent_write)
    insert_board_new(bo_table, comment)
    db.commit()
    return {"result": "created"}


@router.put("/{bo_table}/{wr_id}/comment",
            summary="댓글 수정",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_update_comment(
    db: db_session,
    comment_service: Annotated[CommentServiceAPI, Depends()],
    comment_data: CommentModel,
) -> ResponseNormalModel:
    """
    댓글을 수정합니다.

    ### Request Body
    - **wr_content**: 댓글 내용
    - **wr_name**: 작성자 이름 (비회원일 경우)
    - **wr_password**: 비밀번호
    - **wr_option**: 글 옵션
    - **comment_id**: 댓글 ID (대댓글 수정일 경우 comment_id는 대댓글 id)
    """
    write_model = comment_service.write_model
    comment_service.get_parent_post(comment_service.wr_id, is_reply=False)
    comment = db.get(write_model, comment_data.comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail=f"{comment_data.comment_id} : 존재하지 않는 댓글입니다.")

    comment_service.validate_author(comment, comment_data.wr_password)
    comment_service.validate_post_content(comment_data.wr_content)
    comment.wr_content = comment_service.get_cleaned_data(comment_data.wr_content)
    comment.wr_option = comment_data.wr_option or "html1"
    comment.wr_last = comment_service.g5_instance.get_wr_last_now(write_model.__tablename__)
    db.commit()

    return {"result": "updated"}


@router.delete("/{bo_table}/{wr_id}/comment/{comment_id}",
                summary="댓글 삭제",
                responses={**response_401, **response_403,
                           **response_404, **response_422}
               )
async def api_delete_comment(
    delete_comment_service: Annotated[DeleteCommentServiceAPI, Depends()],
) -> ResponseNormalModel:
    """
    댓글을 삭제합니다.
    """
    delete_comment_service.check_authority(with_session=False)
    delete_comment_service.delete_comment()
    return {"result": "deleted"}