from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Conversation, Feedback, Message, User
from app.schemas.feedback import FeedbackCreate, FeedbackRead

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_feedback(payload: FeedbackCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    message = (
        db.query(Message)
        .join(Conversation)
        .filter(Message.id == payload.message_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    feedback = db.query(Feedback).filter(Feedback.message_id == message.id).first()
    if feedback:
        feedback.helpful = payload.helpful
        feedback.comment = payload.comment
    else:
        feedback = Feedback(user_id=current_user.id, message_id=message.id, helpful=payload.helpful, comment=payload.comment)
        db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
