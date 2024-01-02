import asyncio

from fastapi import APIRouter, Request
from sse_starlette import EventSourceResponse

from core.database import db_session
from core.template import AdminTemplates
from lib.common import *

router = APIRouter()
templates = AdminTemplates()

CACHE_MENU_KEY = "100900"


@router.get("/cache_file_delete")
async def cache_file_delete(request: Request, db: db_session):
    """
    캐시파일 일괄삭제 화면
    """
    request.session["menu_key"] = CACHE_MENU_KEY

    return templates.TemplateResponse("cache_file_delete.html", {"request": request})


@router.get("/cache_file_deleting")
async def cache_file_deleting(request: Request, db: db_session):
    """
    캐시파일 일괄삭제 처리
    """
    async def send_events():
        count = 0
        cache_directory = "data/cache"
        try:
            # 캐시 디렉토리가 존재하는지 확인
            if os.path.exists(cache_directory):
                # 디렉토리 내의 모든 파일 및 폴더 삭제
                for filename in os.listdir(cache_directory):
                    file_path = os.path.join(cache_directory, filename)
                    # 파일이나 디렉토리를 삭제
                    file_dir = ""
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                        file_dir = "파일"
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        file_dir = "디렉토리"

                    count += 1
                    # 10명마다 1초씩 쉬어줍니다.
                    if count % 10 == 0:
                        await asyncio.sleep(0.1)  # 비동기 sleep 사용

                    # return {"status": "Cache cleared successfully"}
                    yield f"data: ({count}) {filename} {file_dir} 삭제 \n\n"
            else:
                yield f"data: {cache_directory} 디렉토리가 존재하지 않습니다. \n\n"
                # return {"status": "Cache directory does not exist"}
        except Exception as e:
            yield f"data: 오류가 발생했습니다. {str(e)} \n\n"
            # return {"status": "Error occurred", "details": str(e)}

        # 종료 메시지 전송
        yield f"data: 총 {count}개의 파일과 디렉토리를 삭제했습니다.\n\n"
        yield "data: [끝]\n\n"

    return EventSourceResponse(send_events())
