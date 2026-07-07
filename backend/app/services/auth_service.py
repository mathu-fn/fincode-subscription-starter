from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import AuthResponse, UserOut

# verify_id_token をテストが 1 箇所で monkeypatch できるよう、関数ではなく
# モジュールを import する（Google の JWKS を自動テストで叩かないため）。
from app.services import google_identity


async def login_with_google(db: AsyncSession, credential: str) -> tuple[User, bool]:
    """検証済み Google ID をキーにユーザーを find-or-create する。

    戻り値の bool は「このログインでユーザーを新規作成したか」。呼び出し側が
    監査ログ（auth.register）の要否を判断するために使う。
    """
    identity = await google_identity.verify_id_token(credential)

    user = await db.scalar(select(User).where(User.google_sub == identity.sub))
    if user is not None:
        return user, False

    # 同じメールのパスワード時代のユーザー行が残っている場合は紐付けせず 409 を
    # 返す（Google アカウントの所有 = 旧アカウントの所有とは限らないため）。
    existing = await db.scalar(select(User).where(User.email == identity.email))
    if existing is not None:
        raise ConflictError(code="email_already_registered")

    user = User(google_sub=identity.sub, email=identity.email, name=identity.name)
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as e:
        # 事前 SELECT を通り抜けた並行 INSERT（TOCTOU）。google_sub 側の衝突は
        # 同一ユーザーの並行ログインなので、既に入った行を読み直して成功させる。
        if "google_sub" in str(e.orig):
            await db.rollback()
            user = await db.scalar(select(User).where(User.google_sub == identity.sub))
            if user is not None:
                return user, False
        # email 側の衝突（または読み直し失敗）は契約どおりの 409 に翻訳する。
        raise ConflictError(code="email_already_registered") from e
    return user, True


def issue_token(user: User) -> AuthResponse:
    token, expires_at = create_access_token(user.id)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at,
        user=UserOut.model_validate(user),
    )
