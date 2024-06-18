from typing_extensions import Annotated, List
from fastapi import (
    APIRouter, Depends, Path, HTTPException, status, Body
)
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder

from core.database import db_session
from lib.board_lib import insert_board_new, set_write_delay, get_list_thumbnail
from api.v1.models.response import (
    response_401, response_403, response_404, response_422
)
from api.v1.dependencies.board import arange_file_data
from api.v1.models.board import (
    WriteModel, CommentModel, ResponseWriteModel, ResponseBoardModel,
    ResponseBoardListModel, ResponseNormalModel, ResponseCreateWriteModel
)
from api.v1.service.board import (
    ListPostServiceAPI, ReadPostServiceAPI,
    CreatePostServiceAPI, UpdatePostServiceAPI, DownloadFileServiceAPI,
    DeletePostServiceAPI, CommentServiceAPI, DeleteCommentServiceAPI,
    MoveUpdateServiceAPI, ListDeleteServiceAPI
)
from service.board_file_service import BoardFileService
from service.ajax import AJAXService


router = APIRouter()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


@router.get("/{bo_table}/writes",
            summary="게시판 조회",
            responses={**response_401, **response_422}
            )
async def api_list_post(
    service: Annotated[ListPostServiceAPI, Depends(ListPostServiceAPI.async_init)],
) -> ResponseBoardListModel:
    """
    게시판 정보, 글 목록을 반환합니다.
    """
    content = {
        "categories": service.categories,
        "board": service.board,
        "writes": service.get_writes(with_files=True),
        "total_count": service.get_total_count(),
        "current_page": service.search_params['current_page'],
        "prev_spt": service.prev_spt,
        "next_spt": service.next_spt,
    }
    return jsonable_encoder(content)


@router.get("/{bo_table}/writes/{wr_id}",
            summary="게시판 개별 글 조회",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_read_post(
    db: db_session,
    service: Annotated[ReadPostServiceAPI, Depends(ReadPostServiceAPI.async_init)],
    ajax_service: Annotated[AJAXService, Depends(AJAXService.async_init)],
) -> ResponseWriteModel:
    """
    지정된 게시판의 글을 개별 조회합니다.
    """
    ajax_good_data = ajax_service.get_ajax_good_data(service.bo_table, service.write)
    thumbnail = get_list_thumbnail(
        service.request,
        service.board,
        service.write,
        service.gallery_width,
        service.gallery_height
    )
    content = jsonable_encoder(service.write)
    additional_content = jsonable_encoder({
        "thumbnail": thumbnail,
        "images": service.images,
        "normal_files": service.normal_files,
        "links": service.get_links(),
        "comments": service.get_comments(),
        "good": ajax_good_data["good"],
        "nogood": ajax_good_data["nogood"],
    })
    content.update(additional_content)
    service.validate_secret()
    service.validate_repeat()
    service.block_read_comment()
    service.validate_read_level()
    service.check_scrap()
    service.check_is_good()
    db.commit()
    return content


@router.post("/{bo_table}/writes/{wr_id}",
            summary="게시판 개별 글 조회(비밀글)",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_read_post(
    db: db_session,
    service: Annotated[ReadPostServiceAPI, Depends(ReadPostServiceAPI.async_init)],
    ajax_service: Annotated[AJAXService, Depends(AJAXService.async_init)],
    wr_password: str = Body(..., title="비밀번호", description="비밀글 비밀번호")
) -> ResponseWriteModel:
    """
    지정된 게시판의 비밀글을 개별 조회합니다.

    ### Request Body
    - **wr_password**: 게시글 비밀번호
    """
    write_password = service.get_write_password()
    service.validate_read_wr_password(wr_password, write_password)
    ajax_good_data = ajax_service.get_ajax_good_data(service.bo_table, service.write)
    thumbnail = get_list_thumbnail(
        service.request,
        service.board,
        service.write,
        service.gallery_width,
        service.gallery_height
    )
    content = jsonable_encoder(service.write)
    additional_content = jsonable_encoder({
        "thumbnail": thumbnail,
        "images": service.images,
        "normal_files": service.normal_files,
        "links": service.get_links(),
        "comments": service.get_comments(),
        "good": ajax_good_data["good"],
        "nogood": ajax_good_data["nogood"],
    })
    content.update(additional_content)
    service.validate_repeat()
    service.block_read_comment()
    service.check_scrap()
    service.check_is_good()
    db.commit()
    return content


@router.post("/{bo_table}/writes",
             summary="게시판 글 작성",
             responses={**response_401, **response_403,
                        **response_404, **response_422}
             )
async def api_create_post(
    db: db_session,
    service: Annotated[CreatePostServiceAPI, Depends(CreatePostServiceAPI.async_init)],
    wr_data: WriteModel,
) -> ResponseCreateWriteModel:
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
    service.validate_secret_board(wr_data.secret, wr_data.html, wr_data.mail)
    service.validate_post_content(wr_data.wr_subject)
    service.validate_post_content(wr_data.wr_content)
    service.validate_write_level()
    service.arrange_data(wr_data, wr_data.secret, wr_data.html, wr_data.mail)
    write = service.save_write(wr_data.parent_id, wr_data)
    insert_board_new(service.bo_table, write)
    service.add_point(write)
    parent_write = service.get_parent_post(wr_data.parent_id)
    service.send_write_mail_(write, parent_write)
    service.set_notice(write.wr_id, wr_data.notice)
    set_write_delay(service.request)
    service.delete_cache()
    db.commit()
    return {"result": "created", "wr_id": write.wr_id}
    

@router.put("/{bo_table}/writes/{wr_id}",
            summary="게시판 글 수정",
            responses={**response_401, **response_403,
                        **response_404, **response_422}
            )
async def api_update_post(
    db: db_session,
    service: Annotated[UpdatePostServiceAPI, Depends(UpdatePostServiceAPI.async_init)],
    wr_data: WriteModel,
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
    service.validate_restrict_comment_count()
    write = service.get_write(service.wr_id)
    service.validate_author(write, wr_data.wr_password)
    service.validate_secret_board(wr_data.secret, wr_data.html, wr_data.mail)
    service.validate_post_content(wr_data.wr_subject)
    service.validate_post_content(wr_data.wr_content)
    service.arrange_data(wr_data, wr_data.secret, wr_data.html, wr_data.mail)
    service.save_write(write, wr_data)
    service.set_notice(write.wr_id, wr_data.notice)
    service.update_children_category(wr_data)
    service.delete_cache()
    db.commit()
    return {"result": "updated"}


@router.delete("/{bo_table}/writes/{wr_id}",
                summary="게시판 글 삭제",
                responses={**response_401, **response_403,
                           **response_404, **response_422}
               )
async def api_delete_post(
    service: Annotated[DeletePostServiceAPI, Depends(DeletePostServiceAPI.async_init)],
) -> ResponseNormalModel:
    """
    지정된 게시판의 글을 삭제합니다.
    """
    service.validate_level(with_session=False)
    service.validate_exists_reply()
    service.validate_exists_comment()
    service.delete_write()
    return {"result": "deleted"}


@router.post("/{bo_table}/writes/delete",
            summary="게시글 일괄 삭제",
            responses={**response_401, **response_403, **response_422}
            )
async def api_list_delete(
    service: Annotated[ListDeleteServiceAPI, Depends()],
    wr_ids: Annotated[List[int], Body(...)],
) -> ResponseNormalModel:
    """
    게시글을 일괄 삭제합니다.

    ### Request Body
    - **wr_ids**: 삭제할 게시글 wr_id 리스트 (예: [1, 2, 3])
    """
    service.validate_admin_authority()
    service.delete_writes(wr_ids)
    return {"result": "deleted"}


@router.get("/{bo_table}/{sw}",
            summary="게시글 복사/이동 가능 목록 조회",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_move_post(
    service: Annotated[MoveUpdateServiceAPI, Depends(MoveUpdateServiceAPI.async_init)],
) -> List[ResponseBoardModel]:
    """
    게시글을 복사/이동 가능한 게시판 목록을 반환합니다.
    sw: copy(게시글 복사) 또는 move(게시글 이동)
    """
    service.validate_admin_authority()
    boards = service.get_admin_board_list()
    return boards


@router.post("/{bo_table}/{sw}",
            summary="게시글 복사/이동",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_move_update(
    service: Annotated[MoveUpdateServiceAPI, Depends(MoveUpdateServiceAPI.async_init)],
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
    service.validate_admin_authority()
    origin_writes = service.get_origin_writes(wr_ids)
    service.move_copy_post(target_bo_tables, origin_writes)
    return {"result": f"해당 게시물을 선택한 게시판으로 {service.act} 하였습니다."}
 

@router.post("/{bo_table}/writes/{wr_id}/files",
            summary="파일 업로드",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_upload_file(
    service: Annotated[CreatePostServiceAPI, Depends(CreatePostServiceAPI.async_init)],
    file_service: Annotated[BoardFileService, Depends()],
    data: Annotated[dict, Depends(arange_file_data)],
    wr_id: int = Path(..., title="글 아이디", description="글 아이디"),
) -> ResponseNormalModel:
    """
    파일을 업로드합니다.
    - multipart/form-data로 전송해야 합니다.
    """
    write = service.get_write(wr_id)
    service.upload_files(
        file_service, write, data["files"], data["file_contents"], data["file_dels"]
    )
    return {"result": "uploaded"}


@router.get("/{bo_table}/writes/{wr_id}/files/{bf_no}",
            summary="파일 다운로드",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_download_file(
    service: Annotated[DownloadFileServiceAPI, Depends(DownloadFileServiceAPI.async_init)],
):
    """
    게시글의 파일을 다운로드합니다.

    - **bo_table**: 게시글 테이블명
    - **wr_id**: 게시글 아이디
    - **bf_no**: 첨부된 파일의 순번
    """
    service.validate_download_level()
    board_file = service.get_board_file()
    service.validate_point(board_file)
    return FileResponse(board_file.bf_file, filename=board_file.bf_source)


@router.post("/{bo_table}/writes/{wr_id}/comments",
            summary="댓글 작성",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_create_comment(
    db: db_session,
    service: Annotated[CommentServiceAPI, Depends(CommentServiceAPI.async_init)],
    comment_data: CommentModel,
    bo_table: str = Path(..., title="게시판 테이블명", description="게시판 테이블명"),
    wr_id: int = Path(..., title="부모글 아이디", description="부모글 아이디"),
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
    parent_write = service.get_parent_post(wr_id, is_reply=False)
    service.validate_comment_level()
    service.validate_point()
    service.validate_post_content(comment_data.wr_content)
    comment = service.save_comment(comment_data, parent_write)
    service.add_point(comment)
    service.send_write_mail_(comment, parent_write)
    insert_board_new(bo_table, comment)
    db.commit()
    return {"result": "created"}


@router.put("/{bo_table}/writes/{wr_id}/comments",
            summary="댓글 수정",
            responses={**response_401, **response_403,
                       **response_404, **response_422}
            )
async def api_update_comment(
    db: db_session,
    service: Annotated[CommentServiceAPI, Depends(CommentServiceAPI.async_init)],
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
    write_model = service.write_model
    service.get_parent_post(service.wr_id, is_reply=False)
    comment = db.get(write_model, comment_data.comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail=f"{comment_data.comment_id} : 존재하지 않는 댓글입니다.")

    service.validate_author(comment, comment_data.wr_password)
    service.validate_post_content(comment_data.wr_content)
    comment.wr_content = service.get_cleaned_data(comment_data.wr_content)
    comment.wr_option = comment_data.wr_option or "html1"
    comment.wr_last = service.g5_instance.get_wr_last_now(write_model.__tablename__)
    db.commit()
    return {"result": "updated"}


@router.delete("/{bo_table}/writes/{wr_id}/comments/{comment_id}",
                summary="댓글 삭제",
                responses={**response_401, **response_403,
                           **response_404, **response_422}
               )
async def api_delete_comment(
    service: Annotated[DeleteCommentServiceAPI, Depends(DeleteCommentServiceAPI.async_init)],
) -> ResponseNormalModel:
    """
    댓글을 삭제합니다.
    """
    service.check_authority(with_session=False)
    service.delete_comment()
    return {"result": "deleted"}