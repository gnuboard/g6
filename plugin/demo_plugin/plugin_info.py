import os
# plugin_info 는 플러그인의 루트에 있어야합니다.

# module_name 는 플러그인의 폴더 이름입니다.
module_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
router_prefix = "bbs"
