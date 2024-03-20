import os
from typing_extensions import Annotated, Dict, List

from fastapi import APIRouter, Depends, Request, Path, HTTPException, status, UploadFile, File, Form
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, update, inspect

from core.database import db_session
from core.models import Board, Group, WriteBaseModel
from lib.board_lib import (
    BoardConfig, get_next_num, generate_reply_character,
    insert_board_new, send_write_mail, BoardFileManager
)
from lib.common import dynamic_create_write_table, FileCache
from lib.dependencies import common_search_query_params
from lib.member_lib import get_admin_type
from lib.template_filters import number_format
from lib.point import insert_point
from lib.g5_compatibility import G5Compatibility
from api.v1.dependencies.board import (
    get_member_info, get_board, get_group,
    validate_write, validate_update_write,
    validate_comment, validate_update_comment, validate_delete_comment,
    validate_upload_file_write, get_write, get_parent_write
)
from api.v1.models.board import WriteModel, CommentModel, ResponseWriteModel
from routers.board import ListPostAPI, ReadPostAPI, DeletePostAPI


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
    list_post_api = ListPostAPI(
        request, db, bo_table, board, member_info["member"], search_params
    )
    return list_post_api.response()



@router.get("/{bo_table}/{wr_id}",
            summary="게시판 개별 글 조회",
            response_description="게시판 개별 글을 반환합니다.",
            response_model=ResponseWriteModel,
            )
async def api_read_post(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글을 개별 조회합니다.
    """
    read_post_api = ReadPostAPI(
        request, db, bo_table, board, wr_id, write, member_info["member"]
    )
    return read_post_api.response()


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

    config = request.state.config
    board_config = BoardConfig(request, board)

    # 게시판 관리자 확인

    member = member_info["member"]
    mb_id = member_info["mb_id"]
    admin_type = get_admin_type(request, mb_id, board=board)

    # 비밀글 사용여부 체크
    if not admin_type:
        if not board.bo_use_secret and "secret" in wr_data.secret and "secret" in wr_data.html and "secret" in wr_data.mail:
            raise HTTPException(status_code=403, detail="비밀글 미사용 게시판 이므로 비밀글로 등록할 수 없습니다.")

    # 게시글 테이블 정보 조회
    write_model = dynamic_create_write_table(bo_table)

    # 글 작성 권한 검증
    if wr_data.parent_id:
        if not board_config.is_reply_level():
            raise HTTPException(status_code=403, detail="답변글을 작성할 권한이 없습니다.")
        parent_write = db.get(write_model, wr_data.parent_id)
        if not parent_write:
            raise HTTPException(status_code=404, detail="답변할 글이 존재하지 않습니다.")
    else:
        if not board_config.is_write_level():
            raise HTTPException(status_code=403, detail="글을 작성할 권한이 없습니다.")
        parent_write = None
    
    # 포인트 검사
    if config.cf_use_point:
        write_point = board.bo_write_point
        if not board_config.is_write_point():
            point = number_format(abs(write_point))
            message = f"글 작성에 필요한 포인트({point})가 부족합니다."
            if not member:
                message += f"\\n로그인 후 다시 시도해주세요."

            raise HTTPException(status_code=403, detail=message)

    category_list = board.bo_category_list.split("|") if board.bo_category_list else []
    if wr_data.ca_name and category_list and wr_data.ca_name not in category_list:
        raise HTTPException(
            status_code=400,
            detail=f"ca_name: {wr_data.ca_name}, 잘못된 분류입니다. 분류는 {','.join(category_list)} 중 하나여야 합니다."
        )

    wr_data_dict = wr_data.model_dump()
    model_fields = inspect(write_model).c.keys()
    filtered_wr_data = {key: value for key, value in wr_data_dict.items() if key in model_fields}

    write = write_model(**filtered_wr_data)
    write.wr_num = parent_write.wr_num if parent_write else get_next_num(bo_table)
    write.wr_reply = generate_reply_character(board, parent_write) if parent_write else ""
    write.mb_id = mb_id if mb_id else ''
    write.wr_ip = request.client.host

    db.add(write)
    db.commit()

    write.wr_parent = write.wr_id  # 부모아이디 설정
    board.bo_count_write = board.bo_count_write + 1  # 게시판 글 갯수 1 증가

    db.commit()

    # 새글 추가
    insert_board_new(bo_table, write)

    # 글작성 포인트 부여(답변글은 댓글 포인트로 부여)
    if member:
        point = board.bo_comment_point if parent_write else board.bo_write_point
        content = f"{board.bo_subject} {write.wr_id} 글" + ("답변" if parent_write else "쓰기")
        insert_point(request, member.mb_id, point, content, board.bo_table, write.wr_id, "쓰기")

    # 메일 발송
    if board_config.use_email:
        send_write_mail(request, board, write, parent_write)

    # 공지글 설정
    board.bo_notice = board_config.set_board_notice(write.wr_id, wr_data.notice)
    db.commit()

    FileCache().delete_prefix(f'latest-{bo_table}')

    return {"result": "created"}
    

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
    write: Annotated[WriteBaseModel, Depends(validate_update_write)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글을 수정합니다.
    """
    board_config = BoardConfig(request, board)
    mb_id = member_info["mb_id"]
    admin_type = get_admin_type(request, mb_id, board=board)

    # 비밀글 사용여부 체크
    if not admin_type:
        if not board.bo_use_secret and "secret" in wr_data.secret and "secret" in wr_data.html and "secret" in wr_data.mail:
            raise HTTPException(status_code=403, detail="비밀글 미사용 게시판 이므로 비밀글로 등록할 수 없습니다.")
        # 비밀글 옵션에 따라 비밀글 설정
        if board.bo_use_secret == 2:
            wr_data.secret = "secret"

    # 게시글 테이블 정보 조회
    write_model = dynamic_create_write_table(bo_table)

    # 공지글 설정
    board.bo_notice = board_config.set_board_notice(wr_id, wr_data.notice)

    FileCache().delete_prefix(f'latest-{bo_table}')

    if not board_config.is_modify_by_comment(wr_id):
        raise HTTPException(status_code=403, detail=f"이 글과 관련된 댓글이 {board.bo_count_modify}건 이상 존재하므로 수정 할 수 없습니다.")

    wr_data_dict = wr_data.model_dump()
    for key, value in wr_data_dict.items():
        setattr(write, key, value)

    write.wr_ip = request.client.host
    db.commit()

    # 분류 수정 시 댓글/답글도 같이 수정
    if wr_data.ca_name:
        db.execute(
            update(write_model).where(write_model.wr_parent == wr_id)
            .values(ca_name=wr_data.ca_name)
        )
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
) -> Dict:
    """
    파일 업로드
    """
    FILE_DIRECTORY = "data/file/"
    mb_id = member_info["mb_id"]
    admin_type = get_admin_type(request, mb_id, board=board)
    file_manager = BoardFileManager(board, write.wr_id)
    directory = os.path.join(FILE_DIRECTORY, bo_table)
    wr_file = write.wr_file
    exclude_file = {"size": [], "ext": []}
    for file in files:
        index = files.index(file)
        if file.filename:
            # 관리자가 아니면서 설정한 업로드 사이즈보다 크거나 업로드 가능 확장자가 아니면 업로드하지 않음
            if not admin_type:
                if not file_manager.is_upload_size(file):
                    exclude_file["size"].append(file.filename)
                    continue
                if not file_manager.is_upload_extension(request, file):
                    exclude_file["ext"].append(file.filename)
                    continue

            board_file = file_manager.get_board_file(index)
            filename = file_manager.get_filename(file.filename)
            bf_content = file_content[index] if file_content else ""
            if board_file:
                # 기존파일 삭제
                file_manager.remove_file(board_file.bf_file)
                # 파일 업로드 및 정보 업데이트
                file_manager.upload_file(directory, filename, file)
                file_manager.update_board_file(board_file, directory, filename, file, bf_content)
            else:
                # 파일 업로드 및 정보 추가
                file_manager.upload_file(directory, filename, file)
                file_manager.insert_board_file(index, directory, filename, file, bf_content)
                wr_file += 1
    # 파일 개수 업데이트
    write.wr_file = wr_file
    db.commit()

    if exclude_file:
        msg = ""
    if exclude_file.get("size"):
        msg += f"{','.join(exclude_file['size'])} 파일은 업로드 용량({board.bo_upload_size}byte)을 초과하였습니다.\\n"
    if exclude_file.get("ext"):
        msg += f"{','.join(exclude_file['ext'])} 파일은 업로드 가능 확장자가 아닙니다.\\n"
    if msg:
        raise HTTPException(status_code=400, detail=msg)
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