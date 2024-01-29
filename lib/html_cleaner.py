import re

import bleach
import cssutils
from bs4 import BeautifulSoup

from lib.exec_time import timeit


class HTMLCleaner:
    def __init__(self):
        self.allowed_tags = {
            'p', 'br', 'strong', 'em', 'b', 'i', 'u', 'span', 'blockquote',
            'ul', 'ol', 'li', 'a', 'img',
            'table', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot',
            'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'style'  # style 태그는 cssutils 를 통해 검증하기 때문에 여기서 허용 목록에 넣어줍니다.
            # TODO : 필요한 태그 정책 수립해서 추가. 이 곳에 적용되어 있지 않은 태그는 모두 삭제 됨
        }

        self.allowed_attrs = {
            '*': ['class'],
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt', 'title', 'width', 'height']
            # TODO : 태그 내에 허용 할 속성들 추가. 이 곳에 적용되어 있지 않으면 역시 모두 삭제 됨
        }

    @staticmethod
    def __validate_css(css_code):
        parsed_css = cssutils.parseString(css_code)
        for rule in parsed_css:
            if rule.type == rule.STYLE_RULE:
                for _prop in rule.style:
                    # css 요소 내에 javascript 라는 값이 있다면 삭제합니다.
                    # 만약 url(...) 요소도 배제하고 싶으시다면 아래와 같은 방식으로 계속 추가해 나가면 됩니다.
                    #   `if 'url' in _prop.value or 'javascript' in _prop.value:`
                    if 'javascript' in _prop.value:
                        rule.style.removeProperty(_prop.name)
        return parsed_css.cssText.decode('utf-8')

    @staticmethod
    def __step1_cleanse_html(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        # <script> 태그 삭제
        for _tag in soup.find_all('script'):
            _tag.decompose()

        # 모든 이미지 태그(<img>)에 대해 반복
        for _tag in soup.find_all('img'):
            src = _tag.get('src', '')
            if re.search(r'javascript:', src, re.IGNORECASE):
                _tag.decompose()
        return str(soup)

    def __step2_extract_and_validate_styles(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        for style_tag in soup.find_all('style'):
            clean_css = self.__validate_css(style_tag.string)
            style_tag.string = clean_css
        return str(soup)

    def __step3_bleach_clean(self, clean_html):
        return bleach.clean(clean_html, tags=self.allowed_tags, attributes=self.allowed_attrs, strip=True)

    @timeit
    def clean(self, raw_html):
        """
        HTML 값을 빡빡 닦아서 돌려주는 함수 입니다.
        함수 이름을 step으로 적어둔 이유는 바뀌면 문자열 처리 과정에서 에러가 발생합니다.
        의도를 전달 할 수 있는 코드 스타일을 좋아하다보니 이렇게 명명한 점 참고해주시고 언제든 바꾸셔도 좋습니다.
            - 그렇다고 함수형 패러다임을 적용하는 것도 이 프로젝트 구조상 안맞는것 같기도해서 😅
        Args:
            raw_html:
                - 원본 HTML 문자열 변수입니다.
        Returns:
            - script 태그, `javascript:` 소스, CSS 내 위험요소 등을 삭제 한 html 문자열 값
        """
        clean_html = self.__step1_cleanse_html(raw_html)
        clean_html = self.__step2_extract_and_validate_styles(clean_html)
        clean_html = self.__step3_bleach_clean(clean_html)
        return clean_html


if __name__ == '__main__':
    # FIXME: @author ej31 -> 테스트 코드(?) 입니다. PR 후 삭제하셔도 무방합니다.
    cleaner = HTMLCleaner()
    _raw_html = """
    <script>악성 스크립트</script>
    <p>안전한 콘텐츠</p>
    <a href='http://example.com'>링크</a>
    <img src='javascript:alert(\'XSS\');'>
    <img src='https://abc.com/ee.jpg;'>
    <IMG SRC=JaVaScRiPt:alert('XSS')>
    <IMG SRC=javascript:alert('XSS')>
    <IMG SRC=javascript:alert(&quot;XSS&quot;);>
    <style>
    body {
        background-image: url("javascript:alert('XSS')");
        width: 100%;
    }
    p {
        background-image: url("https://safe.com/a.font");
        width: 100%;
    }
    a {
        color: red;
    }
    </style>
    """
    cleaned_html = cleaner.clean(_raw_html)
    print(cleaned_html)
