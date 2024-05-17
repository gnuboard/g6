from fastapi import Depends
from lib.dependency.dependencies import check_use_template, set_template_basic_data
from main import app
from .user_router import router
from ..plugin_config import module_name, router_prefix


def register_user_router():
    app.include_router(router,
                       prefix=router_prefix,
                       tags=[module_name],
                       include_in_schema=False,
                       dependencies=[Depends(check_use_template),
                                     Depends(set_template_basic_data)])