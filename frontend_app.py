import gradio as gr
import torch
import re
import requests
import subprocess
import threading # 🚀 引入多线程
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

# --- 1. 配置 OpenClaw ---
OPENCLAW_URL = "http://127.0.0.1:3000/v1/chat/completions"
OPENCLAW_TOKEN = "YOUR_TOKEN"

# --- 2. 模型初始化 ---
MODEL_PATH = "YOUR_MODEL_PATH"
print("🔥 正在载入避障大脑...")
model = Qwen2VLForConditionalGeneration.from_pretrained(
    MODEL_PATH, torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map="auto"
)
processor = AutoProcessor.from_pretrained(MODEL_PATH)

# --- 3. 异步发送函数 (家属通知) ---
def async_notify_family(score, guidance):
    """
    这是一个后台任务，直接调用系统命令行发送，确保稳定触发
    """
    def task():
        # 把换行符换成逗号，避免在命令行里截断命令
        status_report = f"🚨【导盲犬警报】危险系数：{score}/10，当前指令：{guidance}"
        
        # 🚀 完美复刻你刚才在终端里跑通的那条命令
        # 注意要切换到 openclaw 的目录，并且带上端口环境变量
        cmd = f"cd /home/xsuper/openclaw && OPENCLAW_GATEWAY_PORT=3000 pnpm run start message send --channel synology-chat --target 1 --message '{status_report}'"
        
        try:
            # 运行命令，并且主程序不用等它跑完
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"\n📲 家属端消息推送成功 -> 危险系数: {score}")
            else:
                print(f"\n📡 推送可能失败，OpenClaw 报错: {result.stderr.strip()}")
        except Exception as e:
            print(f"\n📡 命令行执行失败: {e}")

    # 启动子线程执行任务
    thread = threading.Thread(target=task)
    thread.daemon = True 
    thread.start()

# --- 4. 推理核心逻辑 ---
def guide_me(image_path):
    if image_path is None:
        return "请先拍照", 0
    
    try:
        prompt = """
# Role
你是一位专业的智能导盲机器人专家。你的任务是保障盲人主人的行走安全。

# Risk Scoring Standard (0-10)
- 0-2: 前方空旷，无障碍物。
- 3-5: 检测到障碍物，距离较远。
- 6-8: 障碍物距离很近，必须减速。
- 9-10: 极其危险！立即停止。

# Task Description
输出格式：危险等级: [数字] | 提醒: [方位] + [障碍物] + [具体动作建议]
提醒语要短促有力。
"""
        
        messages = [{"role": "user", "content": [{"type": "image", "image": image_path}, {"type": "text", "text": prompt}]}]
        text_tpl = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, _ = process_vision_info(messages)
        inputs = processor(text=[text_tpl], images=image_inputs, padding=True, return_tensors="pt").to("cuda")
        
        # 推理
        generated_ids = model.generate(**inputs, max_new_tokens=64)
        generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        raw_output = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]
        
        # 提取分数和文本
        score = 5
        match = re.search(r"危险等级:\s*(\d+)", raw_output)
        if match:
            score = int(match.group(1))
        
        clean_text = raw_output.split("|")[-1].replace("提醒:", "").strip()
        
        # 🚀 【核心改进】异步通知家属，主程序不等待
        async_notify_family(score, clean_text)
        
        return clean_text, score
    except Exception as e:
        return f"识别波动: {e}", 0

# --- 5. UI 构造 ---
with gr.Blocks(title="AI 导盲犬 - 稳定增强版") as demo:
    gr.Markdown("# 🦮 AI 导盲犬：实景避障终端")
    gr.Markdown("状态：Qwen2-VL 大脑已就绪 | OpenClaw 家属同步通道：已激活（异步运行）")
    
    with gr.Row():
        with gr.Column(scale=2):
            input_img = gr.Image(sources=["webcam", "upload"], type="filepath", label="视野采集")
            run_btn = gr.Button("🚀 开始分析", variant="primary")
        
        with gr.Column(scale=1):
            risk_label = gr.Number(label="⚠️ 碰撞风险系数 (0-10)", precision=0)
            output_text = gr.Textbox(label="播报指令", interactive=False, lines=3)

    tts_js = "(text) => { if (!text || text.includes('波动')) return text; const msg = new SpeechSynthesisUtterance(text); msg.lang = 'zh-CN'; msg.rate = 1.3; window.speechSynthesis.speak(msg); return text; }"

    run_btn.click(
        fn=guide_me, 
        inputs=input_img, 
        outputs=[output_text, risk_label]
    ).then(
        fn=None, inputs=output_text, outputs=None, js=tts_js
    )

if __name__ == "__main__":
    demo.launch(share=True)