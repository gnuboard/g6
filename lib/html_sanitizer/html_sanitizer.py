import abc
from copy import deepcopy
from typing import Dict, Set
from lxml.html import fromstring, tostring
from lxml.html.clean import Cleaner
from lxml.html.defs import safe_attrs
from core.exception import AlertException
from .allowed_dict import *


class XSSCleaner(Cleaner):
    """
    lxml.html.clean.Cleaner 클래스를 상속받아
    필터링 대상이 되는 원본 데이터가 HTML tree가 아닌 경우에도
    필터링 이후 원본 형식이 유지될 수 있도록 합니다.

    strip_outer_div_tag
      - 최상단 부모 태그인 <div></div>를 제거합니다

    clean_html
      - 허용되지 않은 태그 삭제시, 원본 내용이 하나의 HTML Element가 아닌 경우
        원본 형식을 유지하기 위해 Cleaner.clean_html 메소드를 오버라이딩 한 메소드입니다.
    """

    def strip_outer_div_tag(self, html_string):
        html_string = html_string[5:-6]
        return html_string

    def clean_html(self, html: str):
        html = f'<div>{html}</div>'
        html_tree = fromstring(html)
        self(html_tree)
        cleaned_html = tostring(html_tree, encoding='unicode', with_tail=False)
        return self.strip_outer_div_tag(cleaned_html)


class BaseSanitizer(metaclass=abc.ABCMeta):
    """
    SubjectSanitizer, ContentSanitizer 클래스의 추상 클래스.
    공통 허용 태그 및 공통 허용 속성을 정의합니다.

    __init___
      - lxml.html.clean.Cleaner 클래스 및 공통 허용 태그, 공통 허용 속성을 초기화합니다.
      - is_with_library_attrs를 통해 lxml 라이브러리에서 제공하는
        html 속성을 허용할지 여부를 결정합니다. 기본값은 False입니다.

    get_combined_filter_dict
      - 공통 허용 태그 및 속성과 개별 허용 태그 및 속성을 합칩니다.

    get_cleaned_data
       - 상속받은 클래스에서 오버라이딩하여 사용합니다.
         최종적으로 허용된 HTML 태그와 속성만을 반환합니다.
    """

    def __init__(self, is_with_library_attrs=False):
        self.cleaner = XSSCleaner(safe_attrs_only=True, remove_unknown_tags=False)
        self.base_allowed_tags_dict = deepcopy(common_allowed_tags_dict)
        self.base_allowed_attrs_dict = deepcopy(common_allowed_attrs_dict)
        if is_with_library_attrs:
            self.base_allowed_attrs_dict['library'] = safe_attrs

    def get_combined_filter_dict(
        self,
        base_allowed_dict: Dict[str, Set[str]],
        private_allowed_dict: Dict[str, Set[str]],
    ) -> Dict[str, Set[str]]:
        for key, tags in private_allowed_dict.items():
            base_allowed_dict[key] = base_allowed_dict.get(key, set()).union(tags)
        return base_allowed_dict

    @abc.abstractmethod
    def get_cleaned_data(self, html_content: str):
        pass


class SubjectSanitizer(BaseSanitizer):
    """
    게시판 등의 '제목'에 삽입되는 HTML의 XSS 공격 방지를 위한 Sanitizer 클래스
    """

    def __init__(self, is_with_library_attrs: bool = False):
        super().__init__(is_with_library_attrs)
        
        combined_tags = self.get_combined_filter_dict(self.base_allowed_tags_dict, subject_private_allowed_tags_dict)
        combined_attrs = self.get_combined_filter_dict(self.base_allowed_attrs_dict, subject_private_allowed_attrs_dict)
        self.cleaner.allow_tags = {tag for tags in combined_tags.values() for tag in tags}
        self.cleaner.safe_attrs = {attr for attrs in combined_attrs.values() for attr in attrs}
    
    def get_cleaned_data(self, html_content: str) -> str:
        cleaned_html = self.cleaner.clean_html(html_content)

        if not cleaned_html:
            raise AlertException("허용되지 않는 HTML 태그들을 변경후 제목을 다시 작성해주세요.", 400)

        return cleaned_html


class ContentSanitizer(BaseSanitizer):
    """
    게시판 등의 '본문'에 삽입되는 HTML의 XSS 공격 방지를 위한 Sanitizer 클래스
    """

    def __init__(self, is_with_library_attrs: bool = False):
        super().__init__(is_with_library_attrs)
        combined_tags = self.get_combined_filter_dict(self.base_allowed_tags_dict, content_private_allowed_tags_dict)
        combined_attrs = self.get_combined_filter_dict(self.base_allowed_attrs_dict, content_private_allowed_attrs_dict)
        self.cleaner.allow_tags = {tag for tags in combined_tags.values() for tag in tags}
        self.cleaner.safe_attrs = {attr for attrs in combined_attrs.values() for attr in attrs}

    def get_cleaned_data(self, html_content: str) -> str:
        cleaned_html = self.cleaner.clean_html(html_content)
        return cleaned_html