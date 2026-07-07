from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthenticatedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut

# verify_id_token をテストが 1 箇所で monkeypatch できるよう、関数ではなく
# モジュールを import する（Google の JWKS を自動テストで叩かないため）。
from app.services import google_identity

# ユーザーが存在しない場合でも本物と同じ argon2 検証コストを支払うためのダミーハッシュ。
# 応答時間差からメールアドレスの登録有無を推測されるのを緩和する（タイミング対策）。
# hash_password と同一インスタンスで生成するため、検証コストは実ユーザーと一致する。
_DUMMY_PASSWORD_HASH = hash_password("constant-time-placeholder-password")


async def register(db: AsyncSession, payload: RegisterRequest) -> User:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise ConflictError(code="email_already_registered")

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as e:
        # 事前 SELECT を通り抜けた並行登録（TOCTOU）。unique 制約が DB で弾くため、
        # 500 ではなく契約どおりの 409 に翻訳する。失敗トランザクションは
        # get_session 依存のロールバックが片付ける。
        raise ConflictError(code="email_already_registered") from e
    return user


async def authenticate(db: AsyncSession, payload: LoginRequest) -> User:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or user.password_hash is None:
        # ユーザー不在（または Google 専用ユーザーでパスワードを持たない）でも
        # 検証を 1 回走らせ、存在時との応答時間差を消す。
        verify_password(payload.password, _DUMMY_PASSWORD_HASH)
        raise UnauthenticatedError(code="invalid_credentials")
    if not verify_password(payload.password, user.password_hash):
        raise UnauthenticatedError(code="invalid_credentials")
    return user


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
