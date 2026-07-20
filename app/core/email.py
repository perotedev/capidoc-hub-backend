from functools import lru_cache

import resend
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings

settings = get_settings()


class EmailService:
    """Thin wrapper around the Resend API for transactional emails."""

    def __init__(self) -> None:
        resend.api_key = settings.resend_api_key
        self._from_address = settings.email_from_address

    async def send_email(self, to: str, subject: str, html: str) -> None:
        await run_in_threadpool(
            resend.Emails.send,
            {"from": self._from_address, "to": [to], "subject": subject, "html": html},
        )

    async def send_password_recovery_email(self, to: str, reset_link: str) -> None:
        html = (
            "<p>Você solicitou a recuperação de senha do CapiDoc.</p>"
            f'<p><a href="{reset_link}">Clique aqui para redefinir sua senha</a></p>'
            "<p>Se você não solicitou isso, ignore este email.</p>"
        )
        await self.send_email(to, "Recuperação de senha — CapiDoc", html)

    async def send_welcome_email(self, to: str, name: str) -> None:
        html = (
            f"<p>Olá, {name}!</p>"
            "<p>Sua conta no CapiDoc foi criada. Faça login para definir sua senha de acesso.</p>"
        )
        await self.send_email(to, "Bem-vindo ao CapiDoc", html)


@lru_cache
def get_email_service() -> EmailService:
    return EmailService()
