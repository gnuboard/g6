from fastapi import APIRouter, File
from starlette.responses import JSONResponse

from common import *

router = APIRouter(prefix="/ckeditor4")

UPLOAD_IMAGE_RESIZE = os.getenv("UPLOAD_IMAGE_RESIZE", True)  # True or False
UPLOAD_IMAGE_SIZE_LIMIT = os.getenv("UPLOAD_IMAGE_SIZE_LIMIT", 1024 * 1024 * 20)  # 20 MB
UPLOAD_IMAGE_WIDTH_LIMIT = os.getenv("UPLOAD_IMAGE_WIDTH_LIMIT", 1200)  # px
UPLOAD_IMAGE_HEIGHT_LIMIT = os.getenv("UPLOAD_IMAGE_HEIGHT_LIMIT", 2800)  # px
UPLOAD_IMAGE_QUALITY = os.getenv("UPLOAD_IMAGE_QUALITY", 80)  # (0~100) default 80


@router.post("/upload")
def image_upload(request: Request, upload: UploadFile = File(...)):
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

        if os.path.getsize(upload.file.tell()) > UPLOAD_IMAGE_SIZE_LIMIT:
            return JSONResponse(status_code=400, content="이미지 허용된 용량보다 큽니다.")

        image: Image = Image.open(upload.file)
        width, height = image.size
        if width > UPLOAD_IMAGE_WIDTH_LIMIT:
            image.close()
            return JSONResponse(status_code=400, content="이미지 가로 크기가 허용된 것 보다 큽니다.")

        if height > UPLOAD_IMAGE_HEIGHT_LIMIT:
            image.close()
            return JSONResponse(status_code=400, content="이미지 세로 크기가 허용된 것 보다 큽니다.")

        # 파일 저장
        static_path = "data"
        editor_image_path = f"{static_path}/editor"
        upload_date = datetime.now().strftime("%Y%m%d")
        upload_path = f"{editor_image_path}/{upload_date}"
        filename = f"{uuid.uuid4()}.{upload.filename.split('.')[-1]}"
        make_directory(upload_path)

        try:
            if UPLOAD_IMAGE_RESIZE:
                image = image.resize(image.size, Image.LANCZOS).convert("RGB")
                image.save(f"{upload_path}/{filename}", format="JPEG", quality=UPLOAD_IMAGE_QUALITY, optimize=True)
            image.save(f"{upload_path}/{filename}")
            image.close()

        except Exception as e:
            logging.critical(f"파일 저장에 실패했습니다.", exc_info=e)
            return JSONResponse(status_code=400, content="파일 저장에 실패했습니다.")

        url = request.base_url.__str__() + f"{editor_image_path}/{upload_date}/{filename}"
        # ckeditor4 에서 요구 포맷으로 출력
        result_data = {"url": url, "uploaded": "1", "fileName": filename}
        return JSONResponse(status_code=200, content=result_data)
