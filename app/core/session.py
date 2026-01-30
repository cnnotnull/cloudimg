"""
Session管理模块
基于内存的session实现，支持登录认证和会话管理
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import secrets
from app.config.settings import settings


class SessionManager:
    """Session管理器 - 基于内存的session存储"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self._cleanup_interval_hours = 1  # 每小时清理一次过期session
    
    def create_session(
        self,
        username: str,
        remember_me: bool = False
    ) -> str:
        """
        创建新session
        
        Args:
            username: 用户名
            remember_me: 是否记住登录
            
        Returns:
            session_id: session ID
        """
        session_id = secrets.token_urlsafe(32)
        
        # 计算过期时间
        if remember_me:
            expires_at = datetime.utcnow() + timedelta(
                days=settings.SESSION_REMEMBER_DAYS
            )
        else:
            expires_at = datetime.utcnow() + timedelta(
                minutes=settings.SESSION_EXPIRE_MINUTES
            )
        
        # 创建session数据
        self._sessions[session_id] = {
            "username": username,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "remember_me": remember_me,
            "last_accessed": datetime.utcnow()
        }
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        获取session信息，如果session有效则更新访问时间
        
        Args:
            session_id: session ID
            
        Returns:
            session数据，如果不存在或已过期则返回None
        """
        session = self._sessions.get(session_id)
        
        if not session:
            return None
        
        # 检查是否过期
        if datetime.utcnow() > session["expires_at"]:
            del self._sessions[session_id]
            return None
        
        # 更新最后访问时间
        session["last_accessed"] = datetime.utcnow()
        
        # 如果是"记住我"的session，自动延长过期时间
        if session["remember_me"]:
            session["expires_at"] = datetime.utcnow() + timedelta(
                days=settings.SESSION_REMEMBER_DAYS
            )
        
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除session
        
        Args:
            session_id: session ID
            
        Returns:
            是否删除成功
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def refresh_session(self, session_id: str) -> bool:
        """
        刷新session过期时间（针对非记住我的session）
        
        Args:
            session_id: session ID
            
        Returns:
            是否刷新成功
        """
        session = self._sessions.get(session_id)
        
        if not session:
            return False
        
        # 检查是否过期
        if datetime.utcnow() > session["expires_at"]:
            del self._sessions[session_id]
            return False
        
        # 刷新过期时间
        if session["remember_me"]:
            session["expires_at"] = datetime.utcnow() + timedelta(
                days=settings.SESSION_REMEMBER_DAYS
            )
        else:
            session["expires_at"] = datetime.utcnow() + timedelta(
                minutes=settings.SESSION_EXPIRE_MINUTES
            )
        
        session["last_accessed"] = datetime.utcnow()
        return True
    
    def cleanup_expired_sessions(self) -> int:
        """
        清理所有过期的session
        
        Returns:
            清理的session数量
        """
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if current_time > session["expires_at"]
        ]
        
        for session_id in expired_sessions:
            del self._sessions[session_id]
        
        return len(expired_sessions)
    
    def get_session_count(self) -> int:
        """获取当前活跃的session数量"""
        return len(self._sessions)
    
    def get_all_sessions(self) -> Dict[str, Dict]:
        """获取所有session（用于调试）"""
        return self._sessions.copy()


# 创建全局session管理器实例
session_manager = SessionManager()
