"""Chatbot and AI Advisory Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.schemas.chatbot import (
    ChatMessageCreate,
    ChatMessageOut,
    ConversationCreate,
    ConversationOut,
)
from app.schemas.common import APIResponse
from app.services.chatbot_service import ChatbotService

router = APIRouter(prefix="/chat", tags=["AI Chatbot & Advisory"])


@router.post("/conversations", response_model=APIResponse[ConversationOut])
async def create_conversation(
    payload: ConversationCreate,
    current_user: dict = Depends(get_current_user),
):
    convo = ChatbotService.create_conversation(current_user["id"], payload)
    return APIResponse(
        success=True,
        message="New storage advisory chat started.",
        data=convo,
    )


@router.get("/conversations", response_model=APIResponse[list[ConversationOut]])
async def list_conversations(current_user: dict = Depends(get_current_user)):
    convos = ChatbotService.list_conversations(current_user["id"])
    return APIResponse(
        success=True,
        message=f"Retrieved {len(convos)} conversations.",
        data=convos,
        meta={"total": len(convos)},
    )


@router.get("/conversations/{conversation_id}", response_model=APIResponse[ConversationOut])
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    convo = ChatbotService.get_conversation(conversation_id, current_user["id"])
    if not convo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return APIResponse(
        success=True,
        message="Conversation retrieved.",
        data=convo,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=APIResponse[list[ChatMessageOut]])
async def list_conversation_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    convo = ChatbotService.get_conversation(conversation_id, current_user["id"])
    if not convo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    msgs = ChatbotService.list_messages(conversation_id)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(msgs)} messages.",
        data=msgs,
        meta={"total": len(msgs)},
    )


@router.post("/conversations/{conversation_id}/messages", response_model=APIResponse[ChatMessageOut])
async def post_message(
    conversation_id: str,
    payload: ChatMessageCreate,
    current_user: dict = Depends(get_current_user),
):
    try:
        reply = await ChatbotService.post_message(
            user_id=current_user["id"],
            convo_id=conversation_id,
            payload=payload,
        )
        return APIResponse(
            success=True,
            message="Response generated using Groq LLM and traditional RAG knowledge.",
            data=reply,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
