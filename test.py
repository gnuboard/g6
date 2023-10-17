from fastapi import FastAPI
import aiosmtplib
from email.message import EmailMessage

app = FastAPI()

# SMTP 서버 설정
SMTP_SERVER = "localhost"  # 로컬 SMTP 서버 주소로 변경
SMTP_PORT = 25  # SMTP 서버의 포트 번호로 변경

@app.post("/send-email")
async def send_email(recipient_email: str, subject: str, message: str):
    try:
        # 이메일 메시지 생성
        email_message = EmailMessage()
        email_message["From"] = "your_email@example.com"  # 이메일 발신자 주소 변경
        email_message["To"] = recipient_email
        email_message["Subject"] = subject
        email_message.set_content(message)

        # SMTP 서버에 연결하고 이메일 전송
        server = aiosmtplib.SMTP(hostname=SMTP_SERVER, port=SMTP_PORT)
        await server.connect()
        await server.send_message(email_message)
        await server.quit()

        return {"message": "Email sent successfully"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__test__":
    print("test")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
