import os

# module_name 는 플러그인의 폴더 이름입니다.
module_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))

# 라우터 접두사는 /로 시작합니다.
router_prefix = "/ctx_product_collect"
admin_router_prefix = router_prefix

TEMPLATE_PATH = f"{module_name}/templates"

# 관리자 메뉴를 설정합니다.
admin_menu = {
    f"{module_name}": [
        {
            "name": "CTX 상품수집",
            "url": "",
            "tag": "",
        },
        {
            "id": module_name + "_dashboard",
            "name": "대시보드",
            "url": f"/admin{admin_router_prefix}/",
            "tag": module_name + "_dashboard",
        },
        {
            "id": module_name + "_collect",
            "name": "수집",
            "url": f"/admin{admin_router_prefix}/collect",
            "tag": module_name + "_collect",
        },
    ]
}
