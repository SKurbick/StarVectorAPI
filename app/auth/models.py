from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    field_serializer,
    model_validator,
)


NumericDate = Annotated[
    datetime,
    PlainSerializer(lambda v: v.timestamp(), return_type=float, when_used="always"),
    BeforeValidator(lambda v: datetime.fromtimestamp(v, tz=UTC) if isinstance(v, (int, float)) else v),
]


class BaseRegistredClaims(BaseModel):
    """
    Базовые параметры jwt-токенов.
    """

    iss: Annotated[str | None, Field(description="Издатель токена")] = None
    sub: Annotated[str | None, Field(description="Субъект")] = None
    aud: Annotated[str | list[str] | None, Field(description="Для каких сервисов предназначен")] = None
    exp: Annotated[NumericDate | None, Field(description="Время истечения")] = None
    nbf: Annotated[
        NumericDate | None,
        Field(
            default_factory=lambda: datetime.now(UTC),
            description="Не использовать до",
        ),
    ]
    iat: Annotated[
        NumericDate | None,
        Field(
            default_factory=lambda: datetime.now(UTC),
            description="Время выпуска",
        ),
    ]
    jti: Annotated[
        str,
        Field(default_factory=lambda: str(uuid4()), description="Уникальный идентификатор"),
    ]
    sid: Annotated[str | None, Field(description="ID сессии")] = None
    amr: Annotated[list[str] | None, Field(description="Методы аутентификации")] = None


class BaseTokenPayload(BaseRegistredClaims):
    """
    Базовая модель токена аутентификации.
    """

    auth_schema_version: Annotated[int | None, Field(description="Версия схемы токена")] = None
    auth_time: Annotated[NumericDate | None, Field(description="Время входа в систему")] = None

    def to_jwt_payload(self) -> dict:
        return self.model_dump(mode="json", exclude_none=True)


class UserRole(BaseModel):
    """
    Роль пользователя в access-токене.
    """

    id: Annotated[int, Field(description="ID роли")]
    slug: Annotated[str, Field(description="Слаг роли")]


class RolePermissionPayload(BaseModel):
    """
    Роль и разрешения пользователя.
    """

    authz_version: Annotated[int, Field(description="Версия прав пользователя")] = -1
    permissions: Annotated[
        set[str],
        Field(default_factory=set, description="Доступные разрешения пользователя"),
    ]
    scopes: Annotated[set[str], Field(default_factory=set, description="Домены доступных разрешений")]
    role: Annotated[UserRole | None, Field(description="Роль пользователя")] = None

    @field_serializer("permissions", "scopes")
    def _serialize_sorted_set(self, value: set[str]) -> list[str]:
        return sorted(value)

    def has_permission(self, slug: str) -> bool:
        """
        Проверить наличие разрешения.
        """
        domain, separator, _ = slug.partition(".")
        return slug in self.permissions or (bool(separator) and f"{domain}.admin" in self.permissions)

    def has_scope(self, scope: str) -> bool:
        """
        Проверить наличие разрешений домена.
        """
        return scope in self.scopes


class AccessTokenPayload(
    BaseTokenPayload,
    RolePermissionPayload,
):
    """
    Модель access-токена.
    """

    user_id: int | None = None
    token_type: Literal["access"] = "access"

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    @model_validator(mode="after")
    def validate_subject(self) -> Self:
        """
        Проверяет идентификатор пользователя и тип токена.
        """
        if self.token_type not in (None, "access"):
            raise ValueError("Недопустимый тип токена.")

        if self.sub is not None and not self.sub.isdigit():
            raise ValueError("Недопустимый субъект токена.")

        if self.sub is None and self.user_id is None:
            raise ValueError("В токене отсутствует идентификатор пользователя.")

        if self.sub is not None and self.user_id is not None:
            if int(self.sub) != self.user_id:
                raise ValueError("Идентификаторы пользователя в токене не совпадают.")

        return self

    @property
    def resolved_user_id(self) -> int:
        """
        Возвращает идентификатор пользователя из новой или прежней схемы.
        """
        if self.sub is not None:
            return int(self.sub)

        if self.user_id is not None:
            return self.user_id

        raise ValueError("В токене отсутствует идентификатор пользователя.")


@dataclass(slots=True, frozen=True)
class UserRequestContext:
    """
    Данные аутентифицированного пользователя для одного запроса.
    """

    user_id: int
    is_superuser: bool
    permissions: frozenset[str]


class AuthenticatedUserModel:
    """
    Модель аутентифированного пользователя.
    """

    def __init__(
        self,
        user_context: UserRequestContext,
    ):
        self._user_id = user_context.user_id
        self._is_superuser = user_context.is_superuser
        self._permissions = user_context.permissions

    @property
    def user_id(self) -> int:
        """
        Идентификатор пользователя.
        """
        return self._user_id

    @property
    def permissions(self) -> frozenset:
        """
        Итоговые разрешения пользователя для данного домена.
        """
        return self._permissions

    @property
    def is_superuser(self):
        """
        Признак суперпользователя.
        """
        return self._is_superuser
