import os

# module_name 는 플러그인의 폴더 이름입니다.
module_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
# 라우터 접두사는 /로 시작합니다. 붙이지 않을 때는 "" 빈문자열로 지정해야합니다.
router_prefix = "/bbs"
admin_router_prefix = router_prefix

TEMPLATE_PATH = f"{module_name}/templates"

# 관리자 메뉴를 설정합니다.
admin_menu = {
        f"{module_name}": [
            {
                "name": "플러그인 베이직",
                "url": "",
                "tag": "",
            },
            {
                "id": module_name + "1",  # 메뉴 아이디
                "name": "데모 플러그인 메뉴1",
                "url": f"{admin_router_prefix}/test_demo_admin_template", # 라우터 prefix 가 / 로시작하므로 / 붙일 필요가 없습니다.
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