# family_monitor.py (Gradio 稳妥版)
import gradio as gr
import threading
from flask import Flask, request, jsonify
import json
import time

# --- 1. 共享数据区 ---
global_alert_history = "🏠 监控台已上线，等待接收 AI 导盲犬的预警...\n"

# --- 2. Flask 后台接收器 ---
app = Flask(__name__)

@app.route('/alert', methods=['POST'])
def receive_alert():
    global global_alert_history
    data = request.json if request.is_json else request.form.to_dict()
    
    # 解析数据包
    content = "无内容"
    if 'payload' in data:
        try:
            payload_data = json.loads(data['payload'])
            content = payload_data.get('text', '无内容')
        except Exception as e:
            content = f"解析失败: {e}"
    else:
        content = data.get('text', data.get('message', '无内容'))
        
    # 拼接时间戳
    time_str = time.strftime("%H:%M:%S", time.localtime())
    new_log = f"[{time_str}] 🔴 新警报: {content}\n"
    
    # 追加到记录
    global_alert_history = new_log + global_alert_history
    
    print(f"后台已接收并更新: {content}")
    return jsonify({"status": "received"}), 200

def run_flask():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # 屏蔽 Flask 多余的访问日志
    app.run(host='0.0.0.0', port=5000)

# 启动后台 Flask 线程
threading.Thread(target=run_flask, daemon=True).start()


# --- 3. Gradio 前台界面 ---
def fetch_latest():
    return global_alert_history

with gr.Blocks(title="AI 导盲犬 - 家属监控台") as demo:
    gr.Markdown("# 🏠 AI 导盲犬 - 家属实时监控端")
    gr.Markdown("💡 **提示：** 请点击下方按钮获取最新的预警状态。")
    
    with gr.Row():
        output_text = gr.Textbox(
            label="实时报警记录", 
            value=fetch_latest, 
            interactive=False, 
            lines=15
        )
    
    with gr.Row():
        # 把按钮设为高亮主题，演示时更醒目
        refresh_btn = gr.Button("🔄 获取最新预警状态", variant="primary")
        
    # 去掉了引发报错的 every=1，改为页面初次加载时读取一次
    demo.load(fn=fetch_latest, inputs=None, outputs=output_text)
    
    # 绑定刷新按钮的点击事件
    refresh_btn.click(fn=fetch_latest, inputs=None, outputs=output_text)

if __name__ == "__main__":
    print("🚀 正在启动带有公网链接的家属端监控台...")
    # 生成公网 URL
    demo.launch(share=True)
    