import asyncio
import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.redis_client import get_redis_client
from app.core.security import InvalidTokenError, TokenType, decode_token
from app.core.stomp import StompFrame, decode_frame, encode_frame
from app.modules.mobile.realtime import forms_channel
from app.modules.users.api.v1.dependencies import UserServiceDep
from app.modules.users.application.services import UserService
from app.modules.users.domain.entities import UserEntity

router = APIRouter()

_STOMP_VERSION = "1.2"


async def _authenticate(token: str, user_service: UserService) -> UserEntity | None:
    token = token.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        payload = decode_token(token)
    except InvalidTokenError:
        return None
    if payload.token_type != TokenType.ACCESS:
        return None
    try:
        user = await user_service.get_user(UUID(payload.subject))
    except Exception:
        return None
    if not user.can_authenticate():
        return None
    return user


async def _forward_project_forms(
    websocket: WebSocket, redis_client: Redis, project_id: UUID, subscription_id: str
) -> None:
    channel = forms_channel(project_id)
    pubsub = redis_client.pubsub()
    try:
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            frame = StompFrame(
                command="MESSAGE",
                headers={
                    "subscription": subscription_id,
                    "message-id": str(uuid.uuid4()),
                    "destination": f"/topic/projects/{project_id}/forms",
                    "content-type": "application/json",
                },
                body=message["data"],
            )
            await websocket.send_text(encode_frame(frame))
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


@router.websocket("/mobile/ws")
async def stomp_endpoint(
    websocket: WebSocket,
    user_service: UserServiceDep,
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> None:
    """Authenticated STOMP-over-WebSocket channel for the Android app.

    Auth happens inside the STOMP CONNECT frame (an `authorization` header
    carrying the same `Bearer <access token>` used everywhere else), not at
    the WebSocket handshake — this keeps the channel STOMP-native rather than
    relying on transport-level headers a generic STOMP client might not set.
    Subscriptions are restricted to the caller's own project — an operator
    can only ever subscribe to `/topic/projects/{their own project id}/forms`.
    """
    await websocket.accept()

    user: UserEntity | None = None
    subscription_task: asyncio.Task | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                frame = decode_frame(raw)
            except ValueError:
                continue  # ignore heart-beat/empty frames

            if frame.command in ("CONNECT", "STOMP"):
                user = await _authenticate(frame.headers.get("authorization", ""), user_service)
                if user is None:
                    await websocket.send_text(
                        encode_frame(StompFrame("ERROR", {"message": "Invalid or expired token"}))
                    )
                    await websocket.close()
                    return
                await websocket.send_text(encode_frame(StompFrame("CONNECTED", {"version": _STOMP_VERSION})))

            elif frame.command == "SUBSCRIBE":
                if user is None:
                    await websocket.send_text(encode_frame(StompFrame("ERROR", {"message": "Not connected"})))
                    continue
                destination = frame.headers.get("destination", "")
                subscription_id = frame.headers.get("id", "sub-0")
                if user.project_id is None or destination != f"/topic/projects/{user.project_id}/forms":
                    await websocket.send_text(
                        encode_frame(StompFrame("ERROR", {"message": f"Forbidden destination: {destination}"}))
                    )
                    continue
                if subscription_task is not None:
                    subscription_task.cancel()
                subscription_task = asyncio.create_task(
                    _forward_project_forms(websocket, redis_client, user.project_id, subscription_id)
                )

            elif frame.command == "UNSUBSCRIBE":
                if subscription_task is not None:
                    subscription_task.cancel()
                    subscription_task = None

            elif frame.command == "DISCONNECT":
                break

    except WebSocketDisconnect:
        pass
    finally:
        if subscription_task is not None:
            subscription_task.cancel()
