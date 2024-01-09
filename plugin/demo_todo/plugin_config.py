import os

# module_name 는 플러그인의 폴더 이름입니다.
module_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
router_prefix = "todo"
admin_router_prefix = router_prefix

# 관리자 메뉴를 설정합니다.
admin_menu = {
    f"{module_name}": [
        {
            "name": "플러그인 데모",
            "url": "",
        },
        {
            "id": module_name + "1",  # 메뉴 아이디
            "name": "todo 추가",
            "url": f"{admin_router_prefix}/create",
            "tag": "demo1"
        },
        {
            "id": module_name + "2",  # 메뉴 아이디
            "name": "todo 보기",
            "url": f"{admin_router_prefix}/todos",
            "tag": "demo2"
        },
    ]
}
