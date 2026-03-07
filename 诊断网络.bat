@echo off
chcp 65001 >nul
echo ========================================
echo ZenClean 网络连接诊断工具
echo ========================================
echo.
echo 正在检测与授权服务器的连接...
echo.

python run_network_diag.py

echo.
echo ========================================
echo 诊断完成！
echo ========================================
echo.
echo 如果检测到连接问题：
echo 1. 检查Windows防火墙是否拦截了Python或ZenClean
echo 2. 检查杀毒软件的网络防护功能
echo 3. 尝试以管理员身份运行此脚本
echo 4. 检查网络代理设置
echo.
pause
