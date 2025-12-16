"""
PostgreSQL 数据库连接器
负责连接 LobeChat PostgreSQL 数据库
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class DBConfig:
    """数据库配置"""
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "ssl": self.ssl
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DBConfig':
        return cls(
            host=data.get("host", "localhost"),
            port=int(data.get("port", 5432)),
            database=data.get("database", "lobechat"),
            user=data.get("user", "postgres"),
            password=data.get("password", ""),
            ssl=data.get("ssl", False)
        )


class PostgreSQLConnector:
    """PostgreSQL 数据库连接器"""
    
    def __init__(self, config: DBConfig, log_callback: Optional[callable] = None):
        """
        初始化连接器
        
        Args:
            config: 数据库配置
            log_callback: 日志回调函数
        """
        self.config = config
        self.log_callback = log_callback
        self.connection = None
        self._psycopg2 = None
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)
    
    def _import_psycopg2(self):
        """延迟导入 psycopg2"""
        if self._psycopg2 is None:
            try:
                import psycopg2
                import psycopg2.extras
                self._psycopg2 = psycopg2
                self.log("psycopg2 模块加载成功", "DEBUG")
            except ImportError:
                raise ImportError(
                    "需要安装 psycopg2 模块。\n"
                    "请运行: pip install psycopg2-binary"
                )
        return self._psycopg2
    
    def connect(self) -> bool:
        """
        建立数据库连接
        
        Returns:
            是否连接成功
        """
        try:
            psycopg2 = self._import_psycopg2()
            
            self.log(f"正在连接数据库 {self.config.host}:{self.config.port}...", "INFO")
            
            conn_params = {
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "user": self.config.user,
                "password": self.config.password,
                "connect_timeout": 10
            }
            
            if self.config.ssl:
                conn_params["sslmode"] = "require"
            
            self.connection = psycopg2.connect(**conn_params)
            self.log("✅ 数据库连接成功!", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"❌ 数据库连接失败: {str(e)}", "ERROR")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.log("数据库连接已关闭", "INFO")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connection is not None and not self.connection.closed
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        执行查询并返回结果
        
        Args:
            query: SQL查询语句
            params: 查询参数
        
        Returns:
            查询结果列表
        """
        if not self.is_connected():
            raise ConnectionError("数据库未连接")
        
        psycopg2 = self._import_psycopg2()
        
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            self.log(f"查询执行失败: {str(e)}", "ERROR")
            raise
    
    def get_table_count(self, table_name: str) -> int:
        """获取表的行数"""
        result = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        return result[0]["count"] if result else 0
    
    # ==================== 数据获取方法 ====================
    
    def get_all_agents(self, user_id: str = None) -> List[Dict]:
        """获取所有助手"""
        query = "SELECT * FROM agents"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        query += " ORDER BY created_at"
        return self.execute_query(query, params)
    
    def get_all_sessions(self, user_id: str = None) -> List[Dict]:
        """获取所有会话"""
        query = "SELECT * FROM sessions"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        query += " ORDER BY created_at"
        return self.execute_query(query, params)
    
    def get_all_topics(self, user_id: str = None) -> List[Dict]:
        """获取所有主题"""
        query = "SELECT * FROM topics"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        query += " ORDER BY created_at"
        return self.execute_query(query, params)
    
    def get_all_messages(self, user_id: str = None) -> List[Dict]:
        """获取所有消息"""
        query = "SELECT * FROM messages"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        query += " ORDER BY created_at"
        return self.execute_query(query, params)
    
    def get_agents_to_sessions(self, user_id: str = None) -> List[Dict]:
        """获取助手与会话的关联"""
        query = "SELECT * FROM agents_to_sessions"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        return self.execute_query(query, params)
    
    def get_all_ai_models(self, user_id: str = None) -> List[Dict]:
        """获取所有AI模型"""
        query = "SELECT * FROM ai_models"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        query += " ORDER BY sort, id"
        return self.execute_query(query, params)
    
    def get_all_ai_providers(self, user_id: str = None) -> List[Dict]:
        """获取所有AI提供商"""
        query = "SELECT * FROM ai_providers"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        query += " ORDER BY sort, id"
        return self.execute_query(query, params)
    
    def get_user_settings(self, user_id: str = None) -> List[Dict]:
        """获取用户设置"""
        query = "SELECT * FROM user_settings"
        params = None
        if user_id:
            query += " WHERE id = %s"
            params = (user_id,)
        return self.execute_query(query, params)
    
    def get_session_groups(self, user_id: str = None) -> List[Dict]:
        """获取会话分组"""
        query = "SELECT * FROM session_groups"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        query += " ORDER BY sort"
        return self.execute_query(query, params)
    
    def get_message_plugins(self, user_id: str = None) -> List[Dict]:
        """获取消息插件"""
        query = "SELECT * FROM message_plugins"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        return self.execute_query(query, params)
    
    def get_message_translates(self, user_id: str = None) -> List[Dict]:
        """获取消息翻译"""
        query = "SELECT * FROM message_translates"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        return self.execute_query(query, params)
    
    def get_threads(self, user_id: str = None) -> List[Dict]:
        """获取对话线程"""
        query = "SELECT * FROM threads"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        return self.execute_query(query, params)
    
    def get_user_installed_plugins(self, user_id: str = None) -> List[Dict]:
        """获取用户安装的插件"""
        query = "SELECT * FROM user_installed_plugins"
        params = None
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)
        return self.execute_query(query, params)
    
    def get_all_users(self) -> List[Dict]:
        """获取所有用户"""
        query = "SELECT id, username, email, created_at FROM users ORDER BY created_at"
        return self.execute_query(query)


def test_connection(config: DBConfig) -> tuple:
    """
    测试数据库连接
    
    Returns:
        (success: bool, message: str)
    """
    connector = PostgreSQLConnector(config)
    try:
        if connector.connect():
            # 测试查询
            count = connector.get_table_count("messages")
            connector.disconnect()
            return True, f"连接成功! 消息数: {count}"
        else:
            return False, "连接失败"
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"连接错误: {str(e)}"
