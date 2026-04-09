# QuantumLife
# Use dynex for fortune telling, requiring the details of the fortune book to be accurate to the minute
pip install dynex dimod  # Dynex SDK（已支持 dimod）
# 设置环境变量（或放在 .env 文件里）
export DYNEX_SDK_KEY=你的SDK密钥
# 第一次运行会自动连接 Dynex 量子路由引擎，之后每次采样都会显示作业 ID 和结果表格

