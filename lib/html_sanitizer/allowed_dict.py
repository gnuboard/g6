from typing import Dict, Set

"""
allowed_attrs_dict에 정리된 태그 속성들은
허용되는 다른 태그(allowed_tags_dict에 정의된 태그)들에도 공통적으로 적용됩니다.
key와 value로 구성한 것은 시각적인 목록화를 위한 것입니다.
해당 태그에만 허용되는 속성이 아닌, 공통 허용 속성입니다.

lxml 라이브러리에서 allow_tags, allow_attrs에 대한 if 문 분기 처리 특성상
허용하려는 태그나, 속성이 없는 경우에 dict() 또는 set()으로 사용하면 blocklist 방식으로 동작하게 됩니다.
해당 코드는 allowlist 방식으로 동작하도록 작성되었으므로,
allow_tags, safe_attrs가 set()과 같이 빈값으로 넘어가지 않아야 합니다.
그에 따라 모든 태그 또는 모든 속성을 허용하지 않으려는 경우에는 {'None': {''}}와 같은 방식으로 설정합니다.
"""


# BaseSanitizer
common_allowed_tags_dict: Dict[str, Set[str]] = {'None': {''}}
common_allowed_attrs_dict: Dict[str, Set[str]] = {'None': {''}}


# SubjectSanitizer
subject_private_allowed_tags_dict: Dict[str, Set[str]] = {'None': {''}}
subject_private_allowed_attrs_dict: Dict[str, Set[str]] = {'None': {''}}


# ContentSanitizer
content_private_allowed_tags_dict: Dict[str, Set[str]] = {
    'text': {'span', 'p', 'em', 'i', 'b', 'u', 'small', 'mark', 'del', 'ins', 'sub', 'sup'},
    'h_tags': {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'},
    'list': {'ul', 'ol', 'li', 'dl', 'dt', 'dd'},
    'table': {'table', 'th', 'tr', 'td', 'thead', 'tbody', 'tfoot', 'caption', 'col', 'colgroup'},
    'block': {'div', 'main', 'section', 'article', 'aside', 'nav'},
    'formatting': {'blockquote', 'hr', 'br'},
    'media': {'img', 'audio', 'video', 'source', 'track'},
    'link': {'a'},
}
content_private_allowed_attrs_dict: Dict[str, Set[str]] = {
    'a': {'href', 'title', 'accesskey', 'class', 'dir', 'id', 'lang', 'name', 'rel', 'tabindex', 'type', 'target'},
    'table': {'border', 'cellspacing', 'cellpadding', 'align', 'bgcolor', 'summary'},
    'th': {'scope'},
    'img': {'src', 'alt', 'title', 'width', 'height', 'align'},
    'common': {'style'},
}