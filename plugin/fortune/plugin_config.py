import os

# module_name 는 플러그인의 폴더 이름입니다.
module_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
router_prefix = "fortune"
admin_router_prefix = router_prefix

TEMPLATE_PATH = f"{module_name}/templates"

# 관리자 메뉴를 설정합니다.
admin_menu = {
    f"{module_name}": [
        {
            "name": "오늘의 운세",
            "url": "",
        },
        {
            "id": module_name + "1",
            "name": "오늘의 운세 목록",
            "url": f"{admin_router_prefix}/list",
            "tag": "tag1"
        },
    ]
}
