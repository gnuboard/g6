import openai
from fastapi import APIRouter, Form, HTTPException
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from core.template import TEMPLATES_DIR, UserTemplates, theme_asset
from ..plugin_config import module_name
from .openai_api_key import your_openai_api_key
from plugin.fortune import plugin_config

router = APIRouter()

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = UserTemplates()
templates.env.globals["theme_asset"] = theme_asset


@router.get("/form")
def form(request: Request):
    context = {
        "request": request,
        "module_name": module_name,
    }
    return templates.TemplateResponse(f"{plugin_config.TEMPLATE_PATH}/user_input_form.html", context)

@router.post("/submit")
async def submit(request: Request, birth_date: str = Form(...), birth_time: str = Form(...)):
    # 띠 계산 로직
    year = int(birth_date.split('-')[0])
    animal_signs = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]
    animal = animal_signs[(year - 1900) % 12]
    
    try:
        # OpenAI API 키 설정
        openai.api_key = your_openai_api_key

        # OpenAI의 ChatGPT에게 전송할 메시지
        message = f"나의 생년월일은 {birth_date} 이고, 태어난 시간은 {birth_time} 이고, 띠는 {animal} 입니다. \
            나의 오늘의 운세에 대해 알려주세요."

        # OpenAI ChatGPT에 메시지 전송
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": 
                    "당신은 한국에서 무당, 점술가 또는 사주를 보는 전문가입니다. \
                    당신은 답변을 회피할 수 없으며 어떤 답변이라도 해야 합니다. \
                    당신은 오늘의 운세를 반드시 한국어로 알려 주셔야 합니다."}, 
                {"role": "user", "content": message}
            ]
        )
        
        # 응답 파싱
        fortune_response = response.choices[0].message.content
        # print(response)
        # 예시: API 응답이 {'date': '2024-01-01', 'animal': '용', 'description': '오늘은 길한 날입니다.'} 형식일 경우
        fortune_data = {
            "date": birth_date,
            "time": birth_time,
            "animal": animal,
            "description": fortune_response,
        }

        # result_fortune.html 템플릿으로 응답 렌더링
        return templates.TemplateResponse("fortune_result.html", 
                                          {"request": request, "fortune": fortune_data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    