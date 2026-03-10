"""
测试 verify_license_online() 函数返回值的正确性
修复 Bug: auth.py 返回值不匹配导致解包错误

运行方式（在项目根目录）：
    python -m pytest tests/test_bugfix_auth_return.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, MagicMock
from core.auth import verify_license_online


class TestVerifyLicenseOnlineReturnValue:
    """验证 verify_license_online 始终返回三元组"""

    @patch('core.auth.requests.post')
    @patch('core.auth._load_local_token')
    def test_online_success_returns_three_values(self, mock_token, mock_post):
        """成功时应返回 (True, str, dict|None)"""
        mock_token.return_value = ("fake_token", None, "KEY123")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "token": "jwt_token",
            "products": [{"product_id": "zenclean", "status": "active", "expires_at": "2025-12-31"}]
        }
        mock_post.return_value = mock_response

        result = verify_license_online("test_key")

        assert isinstance(result, tuple), "返回值应为元组"
        assert len(result) == 3, f"返回值应为三元组，实际长度: {len(result)}"
        assert isinstance(result[0], bool), "第一个元素应为 bool"
        assert isinstance(result[1], str), "第二个元素应为 str"
        assert result[2] is None or isinstance(result[2], dict), "第三个元素应为 None 或 dict"

    @patch('core.auth.requests.post')
    @patch('core.auth._load_local_token')
    def test_network_error_returns_three_values(self, mock_token, mock_post):
        """网络错误时应返回 (False, str, None) 三元组"""
        import requests
        mock_token.return_value = ("fake_token", None, "KEY123")
        mock_post.side_effect = requests.RequestException("Connection error")

        result = verify_license_online("test_key")

        assert isinstance(result, tuple), "返回值应为元组"
        assert len(result) == 3, f"返回值应为三元组，实际长度: {len(result)}"
        # 验证不会抛出解包错误
        success, msg, note = result
        assert success is False
        assert "网络连接失败" in msg or "Connection error" in msg

    @patch('core.auth.requests.post')
    @patch('core.auth._load_local_token')
    def test_invalid_license_returns_three_values(self, mock_token, mock_post):
        """无效 license 时应返回 (False, str, None) 三元组"""
        mock_token.return_value = ("fake_token", None, "KEY123")
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"msg": "Invalid license"}
        mock_post.return_value = mock_response

        result = verify_license_online("test_key")

        assert isinstance(result, tuple), "返回值应为元组"
        assert len(result) == 3, f"返回值应为三元组，实际长度: {len(result)}"
        # 验证不会抛出解包错误
        success, msg, note = result
        assert success is False
        assert "[REVOKED]" in msg or "Invalid" in msg

    @patch('core.auth.requests.post')
    @patch('core.auth._load_local_token')
    def test_server_error_returns_three_values(self, mock_token, mock_post):
        """服务端错误时应返回 (False, str, None) 三元组"""
        mock_token.return_value = ("fake_token", None, "KEY123")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = verify_license_online("test_key")

        assert isinstance(result, tuple), "返回值应为元组"
        assert len(result) == 3, f"返回值应为三元组，实际长度: {len(result)}"
        # 验证不会抛出解包错误
        success, msg, note = result
        assert success is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
