from fastapi import APIRouter, Depends, Request

from core.database import db_session
from core.models import Member, Point
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import check_admin_access
from lib.member_lib import get_member_level

router = APIRouter(dependencies=[Depends(check_admin_access)])
templates = AdminTemplates()

from admin.admin_config import router as admin_config_router
from admin.admin_member import router as admin_member_router
from admin.admin_board  import router as admin_board_router
from admin.admin_boardgroup import router as admin_boardgroup_router
from admin.admin_boardgroupmember import router as admin_boardgroupmember_router
from admin.admin_content import router as admin_content_router
from admin.admin_faq import router as admin_faq_router
from admin.admin_theme import router as admin_theme_router
from admin.admin_visit import router as admin_visit_router
from admin.admin_qa import router as admin_qa_router
from admin.admin_sendmail import router as admin_sendmail_router
from admin.admin_menu import router as admin_menu_router
from admin.admin_point import router as admin_point_router
from admin.admin_auth import router as admin_auth_router
from admin.admin_popular import router as admin_popular_router
from admin.admin_poll import router as admin_poll_router
from admin.admin_newwin import router as admin_newwin_router
from admin.admin_mail import router as admin_mail_router
from admin.admin_write_count import router as admin_write_count_router
from admin.admin_plugin import router as admin_plugin_router
from admin.admin_cache import router as admin_cache_router
from admin.admin_service import router as admin_service_router

router.include_router(admin_config_router, tags=["admin_config"])
router.include_router(admin_member_router, tags=["admin_member"])
router.include_router(admin_board_router, tags=["admin_board"])
router.include_router(admin_boardgroup_router, tags=["admin_boardgroup"])
router.include_router(admin_boardgroupmember_router, tags=["admin_boardgroupmember"])
router.include_router(admin_content_router, tags=["admin_content"])
router.include_router(admin_faq_router, tags=["admin_faq"])
router.include_router(admin_theme_router, tags=["admin_theme"])
router.include_router(admin_visit_router, tags=["admin_visit"])
router.include_router(admin_qa_router, tags=["admin_qa"])
router.include_router(admin_sendmail_router, tags=["admin_sendmail"])
router.include_router(admin_menu_router, tags=["admin_menu"])
router.include_router(admin_point_router, tags=["admin_point"])
router.include_router(admin_auth_router, tags=["admin_auth"])
router.include_router(admin_popular_router, tags=["admin_popular"])
router.include_router(admin_poll_router, tags=["admin_poll"])
router.include_router(admin_mail_router, tags=["admin_mail"])
router.include_router(admin_newwin_router, tags=["admin_newwin"])
router.include_router(admin_write_count_router, tags=["admin_write_count"])
router.include_router(admin_plugin_router, tags=["admin_plugin"])
router.include_router(admin_cache_router, tags=["admin_cache"])
router.include_router(admin_service_router, tags=["admin_service"])

MAIN_MENU_KEY = "100000"


@router.get("/")
async def base(request: Request, db: db_session):
    """
    관리자 메인
    """
    request.session["menu_key"] = MAIN_MENU_KEY

    new_member_rows = 5
    new_board_rows = 5
    new_point_rows = 5
    member_level = get_member_level(request)

    # 신규가입회원 내역
    query = select()
    if not request.state.is_super_admin:
        query = query.where(Member.mb_level <= member_level)

    # 전체 회원
    total_member_count = db.scalar(query.add_columns(func.count(Member.mb_id)))

    # 탈퇴 회원
    leave_count = db.scalar(
        query.add_columns(func.count(Member.mb_id))
        .where(Member.mb_leave_date != '')
    )

    # 차단 회원
    intercept_count = db.scalar(
        query.add_columns(func.count(Member.mb_id))
        .where(Member.mb_intercept_date != '')
    )

    # 신규 가입 회원
    new_members = db.scalars(
        query.add_columns(Member)
        .order_by(Member.mb_datetime.desc())
        .limit(new_member_rows)
    ).all()

    # 최근 게시물
    new_writes = db.scalars(
        select(BoardNew)
        .order_by(BoardNew.bn_id.desc())
        .limit(new_board_rows)
    ).all()

    for new in new_writes:
        new.gr_id = new.board.gr_id
        new.gr_subject = new.board.group.gr_subject
        new.bo_subject = new.board.bo_subject

        write_model = dynamic_create_write_table(new.bo_table)
        new.write = db.get(write_model, new.wr_id)
        if not new.write:
            continue

        new.name = new.write.wr_name
        new.datetime = new.write.wr_datetime.strftime('%Y-%m-%d')
        # 게시글
        if new.wr_id == new.wr_parent:
            new.subject = new.write.wr_subject
            new.link = f"/board/{new.bo_table}/{new.wr_id}"
        # 댓글
        else:
            new.subject = f"[댓글] {new.write.wr_content}"
            new.link = f"/board/{new.bo_table}/{new.wr_parent}#c_{new.wr_id}"

    # 최근 포인트 발생 내역
    query = select()
    total_point_count = db.scalar(query.add_columns(func.count(Point.po_id)))
    new_points = db.scalars(
        query.add_columns(Point)
        .order_by(Point.po_id.desc())
        .limit(5)
    ).all()

    for point in new_points:
        rel_table = point.po_rel_table or ""
        rel_id = point.po_rel_id
        if (rel_id and rel_table
                and not "@" in rel_table):
            point.link = f"/board/{rel_table}/{rel_id}"

    context = {
        "request": request,
        "new_member_rows": new_member_rows,
        "total_member_count": total_member_count,
        "leave_count": leave_count,
        "intercept_count": intercept_count,
        "new_members": new_members,
        "new_writes": new_writes,
        "new_point_rows": new_point_rows,
        "total_point_count": total_point_count,
        "new_points": new_points,
    }
    return templates.TemplateResponse("index.html", context)
