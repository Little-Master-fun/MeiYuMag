from datetime import datetime, timedelta
from random import random
from uuid import uuid4

import httpx
from fastapi import HTTPException, Request, Response

from app.core.config import settings
from app.schemas.sdu_auth import SduerInfo
from app.services.uniform_login_des import strEnc


class SduAuthService:
    def __init__(self) -> None:
        self.login_sessions: dict[str, tuple[httpx.Cookies, datetime]] = {}

    def clear_expired_sessions(self) -> None:
        now = datetime.now()
        expired = [
            session_id
            for session_id, (_, expires_at) in self.login_sessions.items()
            if now > expires_at
        ]
        for session_id in expired:
            self.login_sessions.pop(session_id, None)

    async def get_image_code(self, response: Response) -> Response:
        self.clear_expired_sessions()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                upstream = await client.get(f"{settings.sdu_auth_base_url}/cas/code?{random()}")
        except httpx.HTTPError as exc:
            raise HTTPException(503, "SDU CAS unavailable") from exc

        session_id = uuid4().hex
        self.login_sessions[session_id] = (
            upstream.cookies,
            datetime.now() + timedelta(seconds=120),
        )
        response = Response(upstream.content, media_type="image/gif")
        response.set_cookie("login_session", session_id, max_age=120, httponly=True)
        return response

    async def send_sms_code(self, request: Request, mobile: str, code: str) -> None:
        self.clear_expired_sessions()
        session_id = request.cookies.get("login_session")
        if session_id not in self.login_sessions:
            raise HTTPException(400, "Invalid session or session expired")

        cookies, expires_at = self.login_sessions[session_id]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                result = await client.post(
                    f"{settings.sdu_auth_base_url}/cas/loginByMorE",
                    data={
                        "method": "sendMobileCode",
                        "sendConfirm": code,
                        "mobile": mobile,
                        "random": random(),
                    },
                    cookies=cookies,
                )
        except httpx.HTTPError as exc:
            raise HTTPException(503, "SDU CAS unavailable") from exc

        cookies.update(result.cookies)
        self.login_sessions[session_id] = (cookies, expires_at)
        payload = result.json()
        if error := payload.get("error"):
            raise HTTPException(400, error)
        if payload.get("redirectUrl") != "login":
            raise HTTPException(400, "Invalid image code")

    async def sms_login(self, request: Request, mobile: str, code: str) -> SduerInfo:
        self.clear_expired_sessions()
        session_id = request.cookies.get("login_session")
        if session_id not in self.login_sessions:
            raise HTTPException(400, "Invalid session or session expired")

        cookies, _ = self.login_sessions.pop(session_id)
        try:
            async with httpx.AsyncClient(cookies=cookies, timeout=15) as client:
                result = await client.post(
                    f"{settings.sdu_auth_base_url}/cas/loginByMorE",
                    data={
                        "method": "login",
                        "mobile": mobile,
                        "mobileCode": code,
                        "random": random(),
                        "service": settings.sdu_service_url,
                    },
                )
                redirect_url = result.json().get("redirectUrl")
                if not redirect_url:
                    raise HTTPException(400, "Invalid sms code")

                await client.get(redirect_url, follow_redirects=True)
                user_type = await client.post(
                    "https://service.sdu.edu.cn/tp_up/sys/uacm/profile/getUserType",
                    json={},
                    headers={"Content-Type": "application/json;charset=UTF-8"},
                )
                sduid = user_type.json()[0]["ID_NUMBER"]
                user_info = await client.post(
                    "https://service.sdu.edu.cn/tp_up/sys/uacm/profile/getUserById",
                    json={"BE_OPT_ID": strEnc(sduid, "tp", "des", "param")},
                    headers={"Content-Type": "application/json;charset=UTF-8"},
                )
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Could not get user info from SDU service") from exc

        info = SduerInfo.model_validate(user_info.json())
        return info


sdu_auth_service = SduAuthService()
