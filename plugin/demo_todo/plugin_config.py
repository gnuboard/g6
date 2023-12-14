import os

# plugin_config 는 플러그인의 루트에 있어야합니다.

# module_name 는 플러그인의 폴더 이름입니다.
module_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
router_prefix = "todo"
admin_router_prefix = router_prefix

admin_menu = {
    f"{module_name}": [
        {
            "name": "플러그인 데모",
            "url": "",
        },
        {
            "id": module_name + "1",  # 메뉴 아이디
            "name": "todo 추가",
            "url": "todo/create",
            "tag": "demo1"
        },
        {
            "id": module_name + "2",  # 메뉴 아이디
            "name": "todo 보기",
            "url": "todo/todos",
            "tag": "demo2"
        },
    ]
}
