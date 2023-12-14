import os

# module_name 는 플러그인의 폴더 이름입니다.
module_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
router_prefix = "bbs"
admin_router_prefix = router_prefix


# 관리자 메뉴를 설정합니다.
admin_menu = {
        f"{module_name}": [
            {
                "name": "플러그인 데모",
                "url": "",
                "tag": "",
            },
            {
                "id": module_name + "1",  # 메뉴 아이디
                "name": "데모 플러그인 메뉴1",
                "url": f"{admin_router_prefix}/test_demo_admin_template",
                "tag": "demo1",
            },
            {
                "id": module_name + "2",  # 메뉴 아이디
                "name": "데모 플러그인 메뉴2",
                "url": f"{admin_router_prefix}/test_demo_admin",
                "tag": "demo2",
            },
        ]
    }