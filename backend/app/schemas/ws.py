"""WebSocket 帧类型定义，与前端 web/types/index.ts 对齐。

契约来源：plan/后端设计方案.md §5.4 / web/types/index.ts
"""


# ===== 文字流式 /ws/chat =====

# C → S
USER_MESSAGE = "user_message"
STOP = "stop"
HEARTBEAT = "heartbeat"

# S → C
TOKEN = "token"
CITATION = "citation"
FOLLOWUP = "followup"
CLARIFY = "clarify"
DONE = "done"
ERROR = "error"
RATE = "rate"


# ===== 语音流式 /ws/voice =====

# 二进制首字节
VOICE_FRAME_PCM = 0x01
VOICE_ASR_TEXT = 0x02
VOICE_LLM_TOKEN = 0x03
VOICE_TTS_AUDIO = 0x04
VOICE_CONTROL = 0x10

# 控制帧 type
START_CALL = "start_call"
INTERRUPT = "interrupt"
MUTE = "mute"
END_CALL = "end_call"
ASR_FINAL = "asr_final"
AI_START = "ai_start"
AI_END = "ai_end"
STATUS = "status"
FALLBACK_TEXT = "fallback_text"


# 错误码
ERR_RATE_LIMITED = "RATE_LIMITED"
ERR_VOICE_QUOTA_EXCEEDED = "VOICE_QUOTA_EXCEEDED"
ERR_INTERNAL = "INTERNAL"
ERR_INVALID = "INVALID"
