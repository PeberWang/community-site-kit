# -*- coding: utf-8 -*-
"""User & invite service - register (invite-bound role), login, role management."""

import secrets
from typing import List, Optional

from config.schema import Invite, User, ROLES
from config.settings import Settings
from libs.json_io import path_lock
from libs.passwords import hash_password, verify_password
from services.store import JsonStore, new_id, now_iso

MAX_INVITE_USES = 1000
ROLE_SEARCH_TERMS = {
    "admin": ("admin", "管理员"),
    "user": ("user", "用户", "一般用户", "普通用户"),
    "observer": ("observer", "观察员"),
}


class UserService:
    def __init__(self, settings: Settings):
        self.users = JsonStore(settings.db_dir, "users", User, key=lambda u: u.username)
        self.invites = JsonStore(settings.db_dir, "invites", Invite, key=lambda i: i.code)
        self.registration_lock = settings.db_dir / "invite_registration"

    # ---- auth ----

    def register(self, username: str, password: str, display_name: str,
                 invite_code: str) -> User:
        username = username.strip()
        if not username or not password:
            raise ValueError("用户名与密码不能为空")
        with path_lock(self.registration_lock, exclusive=True):
            if self.users.get(username):
                raise ValueError("用户名已被占用")
            invite = self.invites.get(invite_code.strip())
            usage_count = self.invite_usage_count(invite) if invite else 0
            if not invite or usage_count >= invite.max_uses:
                raise ValueError("邀请码无效或已达到使用次数上限")
            user = User(username=username, id=new_id(), password_hash=hash_password(password),
                        display_name=display_name.strip() or username,
                        role=invite.role, created_at=now_iso())
            self.users.put(user)
            if not invite.used_by:
                invite.used_by = user.id
            if user.id not in invite.used_by_ids:
                invite.used_by_ids.append(user.id)
            invite.used_count = usage_count + 1
            invite.used_at = now_iso()
            self.invites.put(invite)
            return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.users.get(username.strip())
        if user and verify_password(password, user.password_hash):
            return user
        return None

    def get(self, username: str) -> Optional[User]:
        return self.users.get(username)

    def get_by_id(self, user_id: str) -> Optional[User]:
        if not user_id:
            return None
        for u in self.users.all():
            if u.id == user_id:
                return u
        return None

    def display_name(self, user_id: str) -> str:
        """Resolve a user id to its current display name; unknown ids (system
        markers like 'llm'/'import') render as-is."""
        u = self.get_by_id(user_id)
        return u.display_name if u else user_id

    def list_users(self) -> List[User]:
        return sorted(self.users.all(), key=lambda u: u.created_at, reverse=True)

    def search_users(self, query: str = "") -> List[User]:
        """Match nickname, registration name, or a Chinese/English role label."""
        needle = query.strip().casefold()
        if not needle:
            return self.list_users()
        matching_roles = {
            role for role, terms in ROLE_SEARCH_TERMS.items()
            if any(needle in term.casefold() for term in terms)
        }
        return [user for user in self.list_users()
                if needle in user.username.casefold()
                or needle in user.display_name.casefold()
                or user.role in matching_roles]

    def set_role(self, username: str, role: str) -> None:
        if role not in ROLES:
            raise ValueError(f"非法角色: {role}")
        user = self.users.get(username)
        if not user:
            raise ValueError("用户不存在")
        user.role = role
        self.users.put(user)

    def set_display_name(self, username: str, display_name: str) -> None:
        user = self.users.get(username)
        if user:
            user.display_name = display_name.strip() or user.display_name
            self.users.put(user)

    def delete_user(self, username: str) -> bool:
        return self.users.delete(username)

    def delete_invite(self, code: str) -> bool:
        invite = self.invites.get(code)
        if invite and self.invite_usage_count(invite):
            return False  # used invites stay as audit trail
        return self.invites.delete(code)

    # ---- invites ----

    def create_invite(self, role: str, created_by: str, note: str = "",
                      max_uses: int = 1) -> Invite:
        if role not in ROLES:
            raise ValueError(f"非法角色: {role}")
        if not 1 <= max_uses <= MAX_INVITE_USES:
            raise ValueError(f"邀请码可使用次数须在 1 至 {MAX_INVITE_USES} 之间")
        invite = Invite(code=secrets.token_urlsafe(8), role=role,
                        note=note.strip(), max_uses=max_uses, created_by=created_by,
                        created_at=now_iso())
        self.invites.put(invite)
        return invite

    def list_invites(self) -> List[Invite]:
        return sorted(self.invites.all(), key=lambda i: i.created_at, reverse=True)

    def search_invites(self, query: str = "") -> List[Invite]:
        """Match an invitation code or its administrative note."""
        needle = query.strip().casefold()
        if not needle:
            return self.list_invites()
        return [invite for invite in self.list_invites()
                if needle in invite.code.casefold() or needle in invite.note.casefold()]

    @staticmethod
    def invite_usage_count(invite: Invite) -> int:
        """Read old single-use records and new multi-use records consistently."""
        return max(invite.used_count, len(invite.used_by_ids), int(bool(invite.used_by)))
