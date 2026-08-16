from fastapi import APIRouter, Depends

from app.core.permission import require_admin
from app.models.user import User


router = APIRouter()


@router.get("/test")
def admin_test(current_admin: User = Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok", "message": "Admin access granted"}
