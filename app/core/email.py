from functools import lru_cache

import resend
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings

settings = get_settings()


class EmailService:
    """Thin wrapper around the Resend API for transactional emails.

    Gated by `settings.email_enabled` — when disabled (the dev default), emails
    are printed to the backend logs instead of sent, so local/dev environments
    never need a real Resend API key and reset codes are visible directly in
    `docker compose logs api`."""

    def __init__(self) -> None:
        resend.api_key = settings.resend_api_key
        self._from_address = settings.email_from_address

    async def send_email(self, to: str, subject: str, html: str) -> None:
        if not settings.email_enabled:
            print(f"[email disabled] to={to} subject={subject!r}\n{html}")
            return
        await run_in_threadpool(
            resend.Emails.send,
            {"from": self._from_address, "to": [to], "subject": subject, "html": html},
        )

    async def send_password_reset_code(self, to: str, code: str) -> None:
        html = (
            "<p>Use o código abaixo para redefinir sua senha do CapiDoc:</p>"
            f"<p style=\"font-size:28px;font-weight:bold;letter-spacing:4px\">{code}</p>"
            f"<p>Esse código expira em {settings.password_reset_code_expire_minutes} minutos.</p>"
            "<p>Se você não solicitou isso, ignore este email.</p>"
        )
        await self.send_email(to, "Seu código de redefinição de senha — CapiDoc", html)

    async def send_welcome_email(self, to: str, name: str) -> None:
        html = (
            f"<p>Olá, {name}!</p>"
            "<p>Sua conta no CapiDoc foi criada. Use a opção \"Esqueci minha senha\" "
            "na tela de login com este email para receber um código e definir sua senha de acesso.</p>"
        )
        await self.send_email(to, "Bem-vindo ao CapiDoc", html)


@lru_cache
def get_email_service() -> EmailService:
    return EmailService()
