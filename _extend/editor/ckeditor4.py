from fastapi import APIRouter, File
from starlette.responses import JSONResponse

from common import *

router = APIRouter(prefix="/ckeditor4")


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

        # 이미지 파일인지 체크하기 위해 pillow 사용
        # image_file: Image = Image.open(upload.file)
        # width, height = image_file.size
        # todo config 에 파일용량 체크필드 추가

        ext = upload.filename.split('.')[-1]
        if not ext in config.cf_image_extension:
            return JSONResponse(status_code=400, content="허용되지 않는 파일입니다.")

        # 파일 저장
        # todo pillow 사용시 변경
        static_path = "data"
        editor_image_path = f"{static_path}/editor"
        upload_date = datetime.now().strftime("%Y%m%d")
        upload_path = f"{editor_image_path}/{upload_date}"
        filename = f"{uuid.uuid4()}.{upload.filename.split('.')[-1]}"

        make_directory(upload_path)
        try:
            save_image(directory=upload_path, filename=filename, file=upload)
        except Exception as e:
            logging.critical(f"파일 저장에 실패했습니다.", exc_info=e)
            return JSONResponse(status_code=400, content="파일 저장에 실패했습니다.")

        url = request.base_url.__str__() + f"{editor_image_path}/{upload_date}/{filename}"
        # ckeditor4 에서 요구 포맷으로 출력
        result_data = {"url": url, "uploaded": "1", "fileName": filename}
        return JSONResponse(status_code=200, content=result_data)
