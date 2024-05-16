"""게시판 파일 관련 기능을 제공하는 서비스 모듈입니다."""
import os
import shutil
from typing import List
from fastapi import Request, UploadFile
from sqlalchemy import exists, func, insert, select

from core.database import db_session
from core.models import Board, BoardFile


class BoardFileService():
    """
    게시판 파일 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """
    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.config = request.state.config
        self.db = db

    def is_exist(self, bo_table: str, wr_id: int):
        """게시글에 파일이 있는지 확인

        Returns:
            bool: 파일이 존재하면 True, 없으면 False
        """
        return self.db.scalar(
            exists(BoardFile)
            .where(BoardFile.bo_table == bo_table, BoardFile.wr_id == wr_id)
            .select()
        )

    def is_upload_extension(self, file: UploadFile) -> bool:
        """업로드 파일 확장자를 확인한다.

        Args:
            file (UploadFile): 업로드 파일

        Returns:
            bool: 파일 확장자가 업로드 가능하면 True, 아니면 False
        """
        ext = file.filename.split(".")[-1]
        content = file.content_type

        if (("image" in content and not ext in self.config.cf_image_extension)
                or ("x-shockwave-flash" in content and not ext in self.config.cf_flash_extension)
                or (("audio" in content or "video" in content) and not ext in self.config.cf_movie_extension)):
            return False

        return True

    def is_upload_size(self, board: Board, file: UploadFile) -> bool:
        """업로드 파일 사이즈를 확인한다.

        Args:
            file (UploadFile): 업로드 파일

        Returns:
            bool: 업로드 파일 사이즈가 설정된 값보다 작으면 True, 크면 False
        """
        if file.size <= 0:
            return False

        if not board.bo_upload_size:
            return True

        return file.size <= board.bo_upload_size

    def get_board_files(self, bo_table: str, wr_id: int) -> List[BoardFile]:
        """업로드된 파일 목록을 가져온다."""
        return self.db.scalars(
            select(BoardFile).where(
                BoardFile.bo_table == bo_table,
                BoardFile.wr_id == wr_id
            )
        ).all()

    def get_board_files_by_form(self, board: Board, wr_id: int = None) -> List[BoardFile]:
        """입력/수정 폼에서 사용할 파일 목록을 가져온다.

        Returns:
            list[BoardFile]: 업로드된 파일 목록 
        """
        config_count = int(board.bo_upload_count) or 0
        if wr_id:
            query = select().where(BoardFile.bo_table == board.bo_table, BoardFile.wr_id == wr_id)
            uploaded_count = self.db.scalar(query.add_columns(func.count()).select_from(BoardFile).order_by(None))
            uploaded_files = self.db.scalars(query.add_columns(BoardFile)).all()
            # 파일 카운트는 업로드된 파일 수와 설정된 값 중 큰 수로 설정한다.
            upload_count = (uploaded_count if uploaded_count > config_count else config_count) - uploaded_count
        else:
            uploaded_files = []
            upload_count = config_count

        # 업로드 파일 + 빈 객체
        files = uploaded_files + [BoardFile() for _ in range(upload_count)]

        return files

    def get_board_files_by_type(self, bo_table: str, wr_id: int):
        """업로드된 파일 목록을 파일과 이미지로 분리한다.

        Args:
            request (Request): Request 객체

        Returns:
            list[BoardFile]: 파일 목록
            list[BoardFile]: 이미지 목록
        """
        board_files = self.get_board_files(bo_table, wr_id)
        images = []
        files = []
        for file in board_files:
            ext = file.bf_source.split('.')[-1]
            if ext in self.config.cf_image_extension:
                images.append(file)
            else:
                files.append(file)

        return images, files

    def get_board_file(self, bo_table: str, wr_id: int, bf_no: int):
        """업로드된 파일을 가져온다.

        Args:
            bf_no (int): 파일 순번

        Returns:
            BoardFile: 업로드된 파일
        """
        return self.db.get(BoardFile, {"bo_table": bo_table, "wr_id": wr_id, "bf_no": bf_no})

    def get_filename(self, filename: str):
        """파일이름을 생성한다.

        Args:
            filename (str): 업로드 파일이름

        Returns:
            str: 파일이름
        """
        return os.urandom(16).hex() + "." + filename.split(".")[-1]

    def insert_board_file(self, bo_table: str, wr_id: int, bf_no: int, directory: str, filename: str, file: UploadFile, content: str = ""):
        """게시글의 파일을 추가한다.

        Args:
            bf_no (int): 파일 순번
            directory (str): 파일 저장 경로
            file (UploadFile): 업로드 파일
            content (str, optional): 파일 설명. Defaults to "".
            bo_table (str, optional): 게시판 테이블명. Defaults to None.
            wr_id (int, optional): 게시글 아이디. Defaults to None.
        """
        self.db.execute(
            insert(BoardFile)
            .values(
                bo_table=bo_table,
                wr_id=wr_id,
                bf_no=bf_no,
                bf_source=file.filename,
                bf_file=f"{directory}/{filename}",
                bf_download=0,
                bf_content=content,
                bf_filesize=file.size
            )
        )
        self.db.commit()

    def update_board_file(self, board_file: BoardFile,
                          directory: str, filename: str, file: UploadFile,
                          content: str = "", bo_table: str = None, wr_id: int = None):
        """게시글의 파일을 수정한다.

        Args:
            board_file (BoardFile): 게시판 파일 인스턴스
            directory (str): 파일 저장 경로
            file (UploadFile): 업로드 파일
            content (str, optional): 파일 설명. Defaults to "".
        """
        if bo_table:
            board_file.bo_table = bo_table
        if wr_id:
            board_file.wr_id = wr_id
        board_file.bf_source = file.filename
        board_file.bf_file = f"{directory}/{filename}"
        board_file.bf_download = 0
        board_file.bf_content = content
        board_file.bf_filesize = file.size
        self.db.commit()

    def update_download_count(self, board_file: BoardFile):
        """다운로드 횟수를 증가시킨다.

        Args:
            board_file (BoardFile): 게시판 파일 인스턴스
        """
        board_file.bf_download += 1
        self.db.commit()

    def move_board_files(self, directory: str,
                         origin_bo_table: str, origin_wr_id: int,
                         target_bo_table: str, target_wr_id: int):
        """게시글의 파일을 이동한다.

        Args:
            target_bo_table (str): 이동할 게시판 테이블명
            target_wr_id (int): 이동할 게시글 아이디
        """
        board_directory = os.path.join(directory, target_bo_table)
        os.makedirs(board_directory, exist_ok=True)

        board_files = self.get_board_files(origin_bo_table, origin_wr_id)
        for board_file in board_files:
            file = self.create_upload_file_from_path(board_file.bf_file)
            file.filename = board_file.bf_source
            file.size = board_file.bf_filesize
            filename = self.get_filename(file.filename)

            # 파일 이동 및 정보 업데이트
            self.move_file(board_file.bf_file, f"{directory}/{filename}")
            self.update_board_file(board_file, directory, filename, file,
                                   board_file.bf_content, target_bo_table, target_wr_id)
            board_file.bo_table = target_bo_table
            board_file.wr_id = target_wr_id

        self.db.commit()

    def copy_board_files(self, directory: str,
                         origin_bo_table: str, origin_wr_id: int,
                         target_bo_table: str, target_wr_id: int) -> None:
        """게시글의 파일을 복사한다."""
        board_directory = os.path.join(directory, target_bo_table)
        os.makedirs(board_directory, exist_ok=True)

        board_files = self.get_board_files(origin_bo_table, origin_wr_id)
        for board_file in board_files:
            file = self.create_upload_file_from_path(board_file.bf_file)
            if not file:
                continue
            file.filename = board_file.bf_source
            file.size = board_file.bf_filesize
            filename = self.get_filename(file.filename)

            # 파일 복사 및 정보 추가
            self.copy_file(board_file.bf_file, f"{board_directory}/{filename}")
            self.insert_board_file(target_bo_table, target_wr_id, board_file.bf_no,
                                   board_directory, filename, file, board_file.bf_content)

    def delete_board_file(self, bo_table: str, wr_id: int, bf_no: int):
        """게시글의 파일을 삭제한다."""
        board_file = self.get_board_file(bo_table, wr_id, bf_no)
        if not board_file:
            return
        self.remove_file(board_file.bf_file)
        self.db.delete(board_file)
        self.db.commit()

    def delete_board_files(self, bo_table: str, wr_id: int):
        """게시글의 파일 전부를 삭제한다."""
        board_files = self.get_board_files(bo_table, wr_id)
        for board_file in board_files:
            # 파일 삭제
            self.remove_file(board_file.bf_file)
            # 동일한 경로에 있는 파일 중 파일이름으로 끝나는 파일들 삭제
            directory = os.path.dirname(board_file.bf_file)
            filename = os.path.basename(board_file.bf_file)
            for file in os.listdir(directory):
                if file.endswith(filename):
                    self.remove_file(os.path.join(directory, file))
            # 파일 정보 삭제
            self.db.delete(board_file)
        self.db.commit()

    def upload_file(self, directory: str, filename: str, file: UploadFile):
        """파일을 업로드한다.

        Args:
            directory (str): 파일 저장 경로
            filename (str): 파일이름
            file (UploadFile): 업로드 파일
        """
        if file and file.filename:
            with open(f"{directory}/{filename}", "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

    def move_file(self, origin: str, target: str):
        """파일을 이동한다.

        Args:
            origin (str): 원본 파일 경로
            target (str): 이동할 파일 경로
        """
        if os.path.exists(origin):
            shutil.move(origin, target)

    def copy_file(self, origin: str, target: str):
        """파일을 복사한다.

        Args:
            origin (str): 원본 파일 경로
            target (str): 복사할 파일 경로
        """
        if os.path.exists(origin):
            shutil.copy(origin, target)

    def remove_file(self, path: str):
        """파일을 삭제한다.

        Args:
            path (str): 파일 경로
        """
        if os.path.exists(path):
            os.remove(path)

    def create_upload_file_from_path(self, path: str):
        """파일 경로로 UploadFile 객체를 생성한다.

        Args:
            path (str): 파일 경로

        Returns:
            UploadFile: 업로드 파일
        """
        if os.path.exists(path):
            with open(path, "rb") as f:
                return UploadFile(f, filename=os.path.basename(path))
