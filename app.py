"""
Qwen3-VL-32B 视觉问答 - Gradio 界面
基于 Gradio 5.x

功能:
- 上传图片
- 输入文本问题
- Qwen3-VL 模型用文字回答（视觉问答 VQA）
- 支持多轮对话
"""

import os
import sys
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, List, Tuple

import gradio as gr
import numpy as np
from PIL import Image

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Qwen3-VL")

# 路径配置
OUTPUT_DIR = Path("/app/outputs")
UPLOAD_DIR = Path("/app/uploads")
# HuggingFace 缓存目录(挂载到命名卷,持久化模型文件)
HF_CACHE_DIR = os.getenv("HF_HOME", "/app/models/huggingface")
# 模型 ID - 用户的 HuggingFace 模型
MODEL_ID = os.getenv("MODEL_ID", "FanCXZi/Qwen3-VL-32B-Instruct-ultra-uncensored-heretic-bucket")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Path(HF_CACHE_DIR).mkdir(parents=True, exist_ok=True)

# 设置 HuggingFace 环境变量,确保缓存到持久化目录
os.environ["HF_HOME"] = HF_CACHE_DIR
os.environ["HUGGINGFACE_HUB_CACHE"] = HF_CACHE_DIR
os.environ["TRANSFORMERS_CACHE"] = HF_CACHE_DIR
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"  # 禁用 hf_transfer,避免额外依赖

# 模型全局变量
MODEL = None
PROCESSOR = None
LOADED = False


def check_cuda() -> dict:
    """检查 CUDA"""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"ok": False, "msg": "CUDA 不可用,将使用 CPU (会非常慢)"}
        props = torch.cuda.get_device_properties(0)
        # 兼容新旧版本
        total_mem = getattr(props, 'total_memory', None) or getattr(props, 'total_mem', 0)
        return {
            "ok": True,
            "name": props.name,
            "total_gb": round(total_mem / 1024**3, 2),
            "msg": f"GPU: {props.name} | 显存: {total_mem/1024**3:.1f} GB"
        }
    except Exception as e:
        return {"ok": False, "msg": f"CUDA 探测失败: {e}"}


def load_model():
    """加载 Qwen3-VL 模型"""
    global MODEL, PROCESSOR, LOADED
    if LOADED:
        return MODEL, PROCESSOR

    logger.info(f"开始加载模型: {MODEL_ID}")
    logger.info(f"模型缓存目录: {HF_CACHE_DIR}")
    start_time = time.time()

    try:
        import torch
        from transformers import (
            Qwen3VLForConditionalGeneration,
            AutoProcessor,
        )

        # 检查本地缓存
        cache_path = Path(HF_CACHE_DIR) / "models--FanCXZi--Qwen3-VL-32B-Instruct-ultra-uncensored-heretic-bucket"
        if cache_path.exists():
            logger.info(f"✅ 发现本地缓存: {cache_path}")
        else:
            logger.info(f"⏳ 首次启动,需要从 HuggingFace 下载 ~67GB 模型...")
            logger.info(f"   下载可能需要 5-15 分钟(取决于网速)")

        # 加载模型 (BF16 精度节省显存)
        logger.info("加载 model...")
        MODEL = Qwen3VLForConditionalGeneration.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            device_map="auto",  # 自动分配到 GPU
            attn_implementation="sdpa",  # SDPA attention, 速度快
            cache_dir=HF_CACHE_DIR,
        )

        logger.info("加载 processor...")
        PROCESSOR = AutoProcessor.from_pretrained(
            MODEL_ID,
            cache_dir=HF_CACHE_DIR,
        )

        LOADED = True
        elapsed = time.time() - start_time
        logger.info(f"✅ 模型加载完成! 耗时: {elapsed:.1f} 秒")
        return MODEL, PROCESSOR

    except Exception as e:
        logger.exception(f"模型加载失败: {e}")
        raise


def chat_with_image(
    image: Optional[Image.Image],
    message: str,
    history: List[dict],
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> List[dict]:
    """视觉问答核心函数"""
    if image is None:
        raise gr.Error("请先上传图片!")
    if not message or not message.strip():
        raise gr.Error("请输入问题!")

    try:
        import torch
        from transformers import AutoProcessor

        model, processor = load_model()

        # 保存上传图片(可选,用于记录)
        image_id = uuid.uuid4().hex[:8]
        image_path = UPLOAD_DIR / f"upload_{image_id}.png"
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        image.save(image_path)

        # 构建消息格式(Qwen3-VL 多模态 chat)
        messages = []

        # 添加历史对话
        for h in history:
            messages.append(h)

        # 当前用户消息
        messages.append({
            "role": "user",
            "content": [
                {"type": "image", "image": image_path},
                {"type": "text", "text": message},
            ],
        })

        logger.info(f"推理: message='{message[:50]}...' max_tokens={max_new_tokens}")

        # 准备输入
        text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = processor(
            text=[text],
            images=[image],
            padding=True,
            return_tensors="pt",
        ).to(model.device)

        # 生成
        with torch.no_grad():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=temperature > 0,
            )

        # 提取新生成的 token
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        response = processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]

        logger.info(f"回答: '{response[:100]}...'")

        # 返回更新后的 history
        history.append({
            "role": "user",
            "content": [
                {"type": "image", "image": str(image_path)},
                {"type": "text", "text": message},
            ],
        })
        history.append({
            "role": "assistant",
            "content": response,
        })

        return history

    except Exception as e:
        logger.exception("推理失败")
        raise gr.Error(f"推理失败: {str(e)}")


def build_ui():
    """构建 Gradio 界面"""
    info = check_cuda()

    with gr.Blocks(
        title="Qwen3-VL 视觉问答",
        theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="purple"),
    ) as demo:
        gr.Markdown(f"""
        # 🖼️ Qwen3-VL-32B 视觉问答

        **模型**: `Qwen3-VL-32B-Instruct-ultra-uncensored-heretic`

        **状态**: {info['msg']}

        上传图片,向 Qwen3-VL 提问,模型会用文字回答你的问题。
        """)

        # 模型加载状态
        with gr.Row():
            load_btn = gr.Button("📥 加载模型 (首次启动较慢)", variant="primary", size="lg")
            status = gr.Textbox(label="模型状态", interactive=False, value="未加载")

        load_btn.click(
            fn=lambda: ("加载中... 请稍候 (首次启动需下载 ~67GB 模型)" if not LOADED else "已加载"),
            outputs=status,
        ).then(
            fn=lambda: (
                "✅ 加载完成!" if _try_load() else "❌ 加载失败 - 请查看 Phala 日志"
            ),
            outputs=status,
        )

        # 视觉问答界面
        with gr.Row():
            # 左侧: 输入
            with gr.Column(scale=1):
                image_input = gr.Image(
                    label="上传图片",
                    type="pil",
                    sources=["upload", "clipboard"],
                    height=400,
                )

                with gr.Accordion("⚙️ 生成参数", open=False):
                    max_new_tokens = gr.Slider(
                        label="最大输出长度",
                        minimum=64, maximum=2048, step=64, value=512,
                    )
                    temperature = gr.Slider(
                        label="Temperature (随机性)",
                        minimum=0.0, maximum=2.0, step=0.1, value=0.7,
                    )
                    top_p = gr.Slider(
                        label="Top P",
                        minimum=0.1, maximum=1.0, step=0.05, value=0.9,
                    )

                gr.Markdown("""
                **使用示例:**
                - "描述这张图片"
                - "图片里有什么文字?"
                - "这个人穿什么衣服?"
                - "用中文写一个关于这张图的短故事"
                """)

            # 右侧: 对话
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="对话历史",
                    height=500,
                    type="messages",
                )

                msg_input = gr.Textbox(
                    label="你的问题",
                    placeholder="输入问题后按 Enter 发送...",
                    lines=2,
                )

                with gr.Row():
                    submit_btn = gr.Button("发送", variant="primary")
                    clear_btn = gr.Button("清空对话")

                gr.Markdown("""
                **提示:**
                - 首次加载模型约需 5-15 分钟(下载 67GB)
                - 之后从缓存加载只需 10-30 秒
                - 模型缓存在命名卷,容器重启不会重新下载
                - H200 GPU 显存 140GB,完全够 32B 模型
                """)

        # 事件绑定
        def user_submit(message, history):
            """用户提交问题"""
            if not message or not message.strip():
                raise gr.Error("请输入问题")
            return "", history

        def bot_respond(image, message, history, max_tokens, temp, top_p):
            """机器人回答"""
            response_history = chat_with_image(
                image=image,
                message=message,
                history=history or [],
                max_new_tokens=int(max_tokens),
                temperature=float(temp),
                top_p=float(top_p),
            )
            # 清空图片(避免下次对话意外使用)
            return None, response_history

        msg_input.submit(
            user_submit,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot],
        ).then(
            bot_respond,
            inputs=[image_input, msg_input, chatbot, max_new_tokens, temperature, top_p],
            outputs=[image_input, chatbot],
        )

        submit_btn.click(
            user_submit,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot],
        ).then(
            bot_respond,
            inputs=[image_input, msg_input, chatbot, max_new_tokens, temperature, top_p],
            outputs=[image_input, chatbot],
        )

        clear_btn.click(lambda: ([], None), outputs=[chatbot, image_input])

    return demo


def _try_load() -> bool:
    """后台尝试加载模型"""
    try:
        load_model()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Qwen3-VL Gradio 视觉问答服务启动中...")
    logger.info(f"模型 ID: {MODEL_ID}")
    logger.info(f"模型缓存: {HF_CACHE_DIR}")
    logger.info(f"输出目录: {OUTPUT_DIR}")
    logger.info("=" * 60)

    demo = build_ui()
    demo.queue(max_size=10).launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        show_error=True,
    )
