import html as htmllib
import re

from core.exception import AlertException
from core.formclass import AfterValidationContent
from lib.common import filter_words
from lib.html_cleaner import HTMLCleaner


def remove_script_tags(input_str):
    """
    아래 함수는 정규식을 사용하여 <script>와 </script> 태그를 제거합니다.
    이 함수는 대소문자를 무시하며, <script> 태그 사이의 모든 내용도 제거합니다.
    `</script>` 태그 하나만 없애는 방법도 있지만.. 굳이..? 라는 판단으로 통으로 날립니다.
    """
    script_pattern = re.compile('< *script[^>]*>([^<]+)< */ *script *>|< *script[^>]*>', re.IGNORECASE)
    return script_pattern.sub('', input_str)


def validate_and_clean_data(request, subject_field, content_field):
    subject_filter_word = filter_words(request, subject_field)
    content_filter_word = filter_words(request, content_field)

    if subject_filter_word or content_filter_word:
        word = subject_filter_word if subject_filter_word else content_filter_word
        raise AlertException(f"제목/내용에 금지단어({word})가 포함되어 있습니다.", 400)

    cleaned_subject = htmllib.escape(subject_field)
    # cleaned_content = remove_script_tags(content_field)
    cleaned_content = HTMLCleaner().clean(content_field)

    return AfterValidationContent(subject_field=cleaned_subject, content_field=cleaned_content)

