import unittest
import os
import sys
from unittest.mock import MagicMock
from dotenv import load_dotenv

def setup_mocks():
    """为缺少库的环境设置 Mock，防止自检崩溃"""
    load_dotenv() # 加载测试环境所需的 .env 变量
    # 模拟 akshare (scraper 核心依赖)
    if 'akshare' not in sys.modules:
        mock_ak = MagicMock()
        sys.modules['akshare'] = mock_ak
        print("💡 环境提示: akshare 未安装，已启用 Mock 模式。")
    
    # 模拟 schedule (main 循环依赖)
    if 'schedule' not in sys.modules:
        sys.modules['schedule'] = MagicMock()
        print("💡 环境提示: schedule 未安装，已启用 Mock 模式。")

def run_all_tests():
    print("🔍 开始执行 Frank Gemini 系统自检...\n")
    setup_mocks()
    
    loader = unittest.TestLoader()
    # 查找 tests 目录下所有以 test_ 开头的 py 文件
    suite = loader.discover('tests', pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ 所有系统模块自检通过！发布准入已达成。")
        return 0
    else:
        print("\n❌ 发现模块异常，请检查上述错误日志。发布准入被拒绝。")
        return 1

if __name__ == "__main__":
    # 确保当前目录在 sys.path 中，以便加载 src
    current_dir = os.getcwd()
    src_dir = os.path.join(current_dir, "src")
    if src_dir not in sys.path:
        sys.path.append(src_dir)
        
    sys.exit(run_all_tests())
