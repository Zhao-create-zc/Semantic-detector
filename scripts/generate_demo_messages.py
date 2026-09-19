"""R297-R301: 生成 Demo messages.jsonl

按 DEMO_DESIGN.md 设计生成 40 条消息，覆盖 5 个 layout、9 个标准粗粒度标签。
R297-R301 修正：
- 同 layout 消息长度变化，避免 length 字段被 ConstantDetector 误命中
- username/password 固定宽度，使 StringDetector 可命中
- username/password 使用非递增 ASCII，避免被 SequenceDetector 误命中
- payload_data 使用非递增字节，避免被 SequenceDetector 误命中
"""
import struct
import json
import random
from datetime import datetime, timezone, timedelta
from collections import Counter

random.seed(42)  # 可复现

messages = []
mid = 0

# ===== login_request (request, 6 fields) =====
# type=0x01, length=BE(msg_len), seq=BE(1000+i), username(5字节固定), password(6字节固定), extra(变长)
# R297 修正：usernames 打乱顺序，避免按字母表递增被 SequenceDetector 误命中
# 首字节序列：f(0x66), h(0x68), a(0x61), g(0x67), b(0x62), e(0x65), c(0x63), d(0x64) - 非单调递增
usernames = ['frank', 'heidi', 'alice', 'grace', 'bobby', 'edelta', 'carol', 'david']
passwords = ['secret', 'hidden', 'mypass', 'qwerty', 'abc123', 'dragon', 'monkey', 'tiger1']
extra_data_list = [
    bytes([0xAB, 0xCD]),
    bytes([0x12, 0x34, 0x56]),
    bytes([0xFE, 0xDC]),
    bytes([0x11, 0x22, 0x33, 0x44]),
    bytes([0xAB, 0xCD]),
    bytes([0x12, 0x34, 0x56]),
    bytes([0xFE, 0xDC]),
    bytes([0x11, 0x22, 0x33, 0x44]),
]
for i in range(8):
    mid += 1
    username = usernames[i].encode('ascii')[:5].ljust(5, b'\x00')  # 固定 5 字节
    password = passwords[i].encode('ascii')[:6].ljust(6, b'\x00')  # 固定 6 字节
    extra = extra_data_list[i]
    msg_len = 1 + 4 + 4 + 5 + 6 + len(extra)
    payload = (
        struct.pack('>B', 0x01)
        + struct.pack('>I', msg_len)
        + struct.pack('>I', 1000 + i)
        + username
        + password
        + extra
    )
    assert len(payload) == msg_len
    messages.append({
        'message_id': mid,
        'layout_id': 'login_request',
        'direction': 'request',
        'payload_hex': payload.hex(),
        'fields': [
            {'field_index': 0, 'start': 0, 'end': 1},
            {'field_index': 1, 'start': 1, 'end': 5},
            {'field_index': 2, 'start': 5, 'end': 9},
            {'field_index': 3, 'start': 9, 'end': 14},
            {'field_index': 4, 'start': 14, 'end': 20},
            {'field_index': 5, 'start': 20, 'end': 20 + len(extra)},
        ]
    })

# ===== data_request (request, 4 fields) =====
payload_data_list = [
    bytes([0xAB, 0xCD, 0xEF]),
    bytes([0x12, 0x34, 0x56, 0x78, 0x9A]),
    bytes([0xFE, 0xDC, 0xBA, 0x98]),
    bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66]),
    bytes([0xAB, 0xCD, 0xEF]),
    bytes([0x12, 0x34, 0x56, 0x78, 0x9A]),
    bytes([0xFE, 0xDC, 0xBA, 0x98]),
    bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66]),
]
for i in range(8):
    mid += 1
    payload_data = payload_data_list[i]
    msg_len = 1 + 4 + 4 + len(payload_data)
    payload = (
        struct.pack('>B', 0x02)
        + struct.pack('>I', msg_len)
        + struct.pack('>I', 2000 + i)
        + payload_data
    )
    assert len(payload) == msg_len
    messages.append({
        'message_id': mid,
        'layout_id': 'data_request',
        'direction': 'request',
        'payload_hex': payload.hex(),
        'fields': [
            {'field_index': 0, 'start': 0, 'end': 1},
            {'field_index': 1, 'start': 1, 'end': 5},
            {'field_index': 2, 'start': 5, 'end': 9},
            {'field_index': 3, 'start': 9, 'end': 9 + len(payload_data)},
        ]
    })

# ===== data_response (response, 4 fields) =====
base_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
payload_data_list_resp = [
    bytes([0xA0, 0xB0]),
    bytes([0x1A, 0x2B, 0x3C, 0x4D]),
    bytes([0xFF, 0xEE, 0xDD]),
    bytes([0x55, 0x66, 0x77, 0x88, 0x99]),
    bytes([0xA0, 0xB0]),
    bytes([0x1A, 0x2B, 0x3C, 0x4D]),
    bytes([0xFF, 0xEE, 0xDD]),
    bytes([0x55, 0x66, 0x77, 0x88, 0x99]),
]
for i in range(8):
    mid += 1
    capture_time = base_time + timedelta(hours=i)
    unix_seconds = int(capture_time.timestamp())
    payload_data = payload_data_list_resp[i]
    msg_len = 1 + 4 + 4 + len(payload_data)
    payload = (
        struct.pack('>B', 0x03)
        + struct.pack('>I', msg_len)
        + struct.pack('>I', unix_seconds)
        + payload_data
    )
    assert len(payload) == msg_len
    messages.append({
        'message_id': mid,
        'layout_id': 'data_response',
        'direction': 'response',
        'capture_time': capture_time.isoformat(),
        'payload_hex': payload.hex(),
        'fields': [
            {'field_index': 0, 'start': 0, 'end': 1},
            {'field_index': 1, 'start': 1, 'end': 5},
            {'field_index': 2, 'start': 5, 'end': 9},
            {'field_index': 3, 'start': 9, 'end': 9 + len(payload_data)},
        ]
    })

# ===== heartbeat (request, 3 fields) =====
for i in range(8):
    mid += 1
    msg_len = 1 + 4 + 4
    payload = (
        struct.pack('>B', 0x04)
        + struct.pack('>I', 0)
        + struct.pack('>I', 3000 + i)
    )
    assert len(payload) == msg_len
    messages.append({
        'message_id': mid,
        'layout_id': 'heartbeat',
        'direction': 'request',
        'payload_hex': payload.hex(),
        'fields': [
            {'field_index': 0, 'start': 0, 'end': 1},
            {'field_index': 1, 'start': 1, 'end': 5},
            {'field_index': 2, 'start': 5, 'end': 9},
        ]
    })

# ===== auth_token (request, 4 fields) =====
token_ids = [1, 2, 1, 3, 2, 4, 3, 5]
unknown_lengths = [4, 6, 5, 7, 4, 6, 5, 7]
for i in range(8):
    mid += 1
    unknown_bytes = bytes([random.randint(0, 255) for _ in range(unknown_lengths[i])])
    msg_len = 1 + 4 + 4 + len(unknown_bytes)
    payload = (
        struct.pack('>B', 0x05)
        + struct.pack('>I', msg_len)
        + struct.pack('>I', token_ids[i])
        + unknown_bytes
    )
    assert len(payload) == msg_len
    messages.append({
        'message_id': mid,
        'layout_id': 'auth_token',
        'direction': 'request',
        'payload_hex': payload.hex(),
        'fields': [
            {'field_index': 0, 'start': 0, 'end': 1},
            {'field_index': 1, 'start': 1, 'end': 5},
            {'field_index': 2, 'start': 5, 'end': 9},
            {'field_index': 3, 'start': 9, 'end': 9 + len(unknown_bytes)},
        ]
    })

# 写入文件
with open('examples/messages.jsonl', 'w', encoding='utf-8') as f:
    for msg in messages:
        f.write(json.dumps(msg, ensure_ascii=False) + '\n')

print('Generated {} messages'.format(len(messages)))
layout_counts = Counter(m['layout_id'] for m in messages)
for layout, count in sorted(layout_counts.items()):
    print('  {}: {} messages'.format(layout, count))

print('\nMessage lengths per layout:')
for layout in sorted(set(m['layout_id'] for m in messages)):
    lengths = [len(bytes.fromhex(m['payload_hex'])) for m in messages if m['layout_id'] == layout]
    unique_lengths = set(lengths)
    print('  {}: {} unique lengths {}'.format(layout, len(unique_lengths), sorted(unique_lengths)))
