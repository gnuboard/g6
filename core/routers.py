"""Template 라우터 모듈"""
from fastapi import APIRouter, Depends

from bbs.index import router as index_router
from bbs.board import router as board_router
from bbs.register import router as register_router
from bbs.content import router as content_router
from bbs.faq import router as faq_router
from bbs.qa import router as qa_router
from bbs.member_profile import router as user_profile_router
from bbs.profile import router as profile_router
from bbs.memo import router as memo_router
from bbs.poll import router as poll_router
from bbs.point import router as point_router
from bbs.scrap import router as scrap_router
from bbs.board_new import router as board_new_router
from bbs.ajax_good import router as good_router
from bbs.ajax_autosave import router as autosave_router
from bbs.member_leave import router as member_leave_router
from bbs.member_find import router as member_find_router
from bbs.social import router as social_router
from bbs.password import router as password_router
from bbs.search import router as search_router
from bbs.current_connect import router as current_connect_router
from bbs.formmail import router as formmail_router
from lib.dependency.dependencies import (
    check_use_template, set_template_basic_data
)
from lib.editor.ckeditor4 import router as editor_router

router = APIRouter(dependencies=[Depends(check_use_template),
                                 Depends(set_template_basic_data)],
                   include_in_schema=False)
router.include_router(index_router, tags=["index"])
router.include_router(board_router, prefix="/board", tags=["board"])
router.include_router(register_router, prefix="/bbs", tags=["register"])
router.include_router(user_profile_router, prefix="/bbs", tags=["profile"])
router.include_router(profile_router, prefix="/bbs", tags=["profile"])
router.include_router(member_leave_router, prefix="/bbs",tags=["member_leave"])
router.include_router(member_find_router, prefix="/bbs", tags=["member_find"])
router.include_router(content_router, prefix="/bbs", tags=["content"])
router.include_router(faq_router, prefix="/bbs", tags=["faq"])
router.include_router(qa_router, prefix="/bbs", tags=["qa"])
router.include_router(memo_router, prefix="/bbs", tags=["memo"])
router.include_router(poll_router, prefix="/bbs", tags=["poll"])
router.include_router(point_router, prefix="/bbs", tags=["point"])
router.include_router(scrap_router, prefix="/bbs", tags=["scrap"])
router.include_router(board_new_router, prefix="/bbs", tags=["board_new"])
router.include_router(good_router, prefix="/bbs/ajax", tags=["good"])
router.include_router(autosave_router, prefix="/bbs/ajax", tags=["autosave"])
router.include_router(social_router, prefix="/bbs", tags=["social"])
router.include_router(password_router, prefix="/bbs", tags=["password"])
router.include_router(search_router, prefix="/bbs", tags=["search"])
router.include_router(current_connect_router, prefix="/bbs", tags=["current_connect"])
router.include_router(formmail_router, prefix="/bbs", tags=["formmail"])
router.include_router(editor_router, prefix="/editor", tags=["editor"])
