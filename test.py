from fastapi import FastAPI, Request
from jinja2 import Environment, FileSystemLoader, Template

env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('test_combined.html')

# 파이썬 코드를 실행하여 동적 내용을 생성
contents = ["cont 1", "cont 2", "cont 3"]

# 템플릿에 전달할 컨텍스트 변수
context = {
    'contents': contents
}

app = FastAPI()

# 템플릿 렌더링
# output = template.render(context)
# print(output)
@app.get("/test")
def test():
    return Template.TemplateResponse("test_combined.html", context)