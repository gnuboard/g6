import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Request, UploadFile
from PIL import Image
from starlette.responses import JSONResponse

from core.models import Config
from core.settings import settings
from lib.common import calculator_image_resize

router = APIRouter(prefix="/ckeditor4")

_IS_IMAGE_RESIZE = settings.UPLOAD_IMAGE_RESIZE
_IMAGE_RESIZE_LIMIT = settings.UPLOAD_IMAGE_SIZE_LIMIT * 1024 * 1024 # MB -> Byte
_IMAGE_RESIZE_WIDTH = settings.UPLOAD_IMAGE_RESIZE_WIDTH
_IMAGE_RESIZE_HEIGHT = settings.UPLOAD_IMAGE_RESIZE_HEIGHT
_IMAGE_RESIZE_QUALITY = settings.UPLOAD_IMAGE_QUALITY


@router.post("/upload")
async def image_upload(request: Request, upload: UploadFile = File(...)):
    """
    ckeditor4 업로드
    Args:
        request: Request
        upload: 파일
    Returns:
        JSONResponse
    """

    config: Config = request.state.config

    # 파일이 없으면 에러
    if upload and upload.filename:

        # jpeg -> jpg
        upload.filename = upload.filename.lower()
        if upload.filename.endswith(".jpeg"):
            upload.filename = upload.filename[:-4] + "jpg"

        ext = upload.filename.split('.')[-1]
        if ext not in config.cf_image_extension:
            return JSONResponse(status_code=400, content="허용되지 않는 파일입니다.")

        if os.path.getsize(upload.file.tell()) > _IMAGE_RESIZE_LIMIT:
            return JSONResponse(status_code=400, content="이미지 허용된 용량보다 큽니다.")

        # 파일 저장
        static_path = "data"
        editor_image_path = f"{static_path}/editor"
        upload_date = datetime.now().strftime("%Y%m%d")
        upload_path = f"{editor_image_path}/{upload_date}"
        filename = f"{uuid.uuid4()}.{upload.filename.split('.')[-1]}"
        os.makedirs(upload_path, exist_ok=True)

        try:
            image: Image.Image = Image.open(upload.file)
            if _IS_IMAGE_RESIZE:
                width, height = image.size
                size_result = calculator_image_resize(
                    width, height, _IMAGE_RESIZE_WIDTH, _IMAGE_RESIZE_HEIGHT)
                if size_result:
                    image = image.resize((size_result['width'], size_result['height']), Image.LANCZOS)
                image = image.convert("RGB")
                image.save(f"{upload_path}/{filename}",
                           format="JPEG",
                           quality=_IMAGE_RESIZE_QUALITY,
                           optimize=True)
            image.save(f"{upload_path}/{filename}")
            image.close()

        except Exception as e:
            logging.critical(f"파일 저장에 실패했습니다.", exc_info=e)
            return JSONResponse(status_code=400, content="파일 저장에 실패했습니다.")

        url = request.base_url.__str__() + f"{editor_image_path}/{upload_date}/{filename}"
        # ckeditor4 에서 요구 포맷으로 출력
        result_data = {"url": url, "uploaded": "1", "fileName": filename}
        return JSONResponse(status_code=200, content=result_data)
