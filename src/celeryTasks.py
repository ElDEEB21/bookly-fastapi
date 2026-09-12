from celery import Celery
from src.config import Config
from src.mail import mail, create_message
from asgiref.sync import async_to_sync

c_app = Celery(
    "bookly",
    broker=Config.REDIS_URL,
    backend=Config.REDIS_URL,
)

c_app.config_from_object("src.config")


@c_app.task(name="src.celeryTasks.send_email")
def send_email(recipients: list[str], subject: str, body: str):
    message = create_message(recipients=recipients, subject=subject, body=body)
    async_to_sync(mail.send_message)(message)
    return "Email sent"