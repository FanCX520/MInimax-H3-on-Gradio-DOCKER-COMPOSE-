"""
MiniMax H3 视频生成 - Gradio 图参考文生图界面
基于 Gradio 5.x

功能:
- 上传参考图片
- 输入文本提示词
- 设置视频生成参数
- 生成视频并预览/下载
"""

import os
import sys
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple

import gradio as gr
import numpy as np
from PIL import Image

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MiniMax-H3")

# 路径配置
OUTPUT_DIR = Path("/app/outputs")
UPLOAD_DIR = Path("/app/uploads")
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/MiniMax-H3")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============== 模型加载部分 ==============
class H3VideoGenerator:
    """MiniMax H3 视频生成器封装"""

    def __init__(self):
        self.model = None
        self.device = "cuda" if self._check_cuda() else "cpu"
        self.loaded = False
        logger.info(f"H3VideoGenerator 初始化 - device: {self.device}")

    def _check_cuda(self) -> bool:
        """检查 CUDA 是否可用，处理 total_mem 兼容性"""
        try:
            import torch
            if torch.cuda.is_available():
                # 处理 PyTorch total_mem 属性兼容问题
                props = torch.cuda.get_device_properties(0)
                # 兼容新旧版本
                total_mem = getattr(props, 'total_memory', None) or getattr(props, 'total_mem', 0)
                logger.info(f"GPU: {props.name}, 总显存: {total_mem / 1024**3:.2f} GB")
                return True
            return False
        except Exception as e:
            logger.error(f"CUDA 检查失败: {e}")
            return False

    def load_model(self, model_path: str = MODEL_PATH):
        """加载模型（占位 - 实际使用时替换为真实加载逻辑）"""
        try:
            logger.info(f"开始加载模型: {model_path}")
            # ============================================
            # TODO: 在这里替换为真实的模型加载代码
            # 示例:
            # from diffusers import MinimaxH3Pipeline
            # self.model = MinimaxH3Pipeline.from_pretrained(
            #     model_path,
            #     torch_dtype=torch.bfloat16,
            # ).to(self.device)
            # ============================================
            self.loaded = True
            logger.info("模型加载完成 (演示模式)")
            return True
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            return False

    def generate(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 96,
        fps: int = 24,
        height: int = 720,
        width: int = 1280,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 30,
        seed: int = -1,
        progress=gr.Progress(track_tqdm=True),
    ) -> str:
        """生成视频"""
        if not self.loaded:
            self.load_model()

        if image is None:
            raise ValueError("请先上传参考图片")

        # 保存上传图片
        image_id = uuid.uuid4().hex[:8]
        image_path = UPLOAD_DIR / f"ref_{image_id}.png"
        image.save(image_path)

        # 输出视频路径
        output_path = OUTPUT_DIR / f"h3_{image_id}_{int(time.time())}.mp4"

        try:
            logger.info(f"开始生成视频 - prompt: {prompt[:50]}...")

            # ============================================
            # TODO: 在这里调用真实的模型推理
            # 示例:
            # if seed == -1:
            #     seed = torch.randint(0, 2**32, (1,)).item()
            # generator = torch.Generator(device=self.device).manual_seed(seed)
            #
            # result = self.model(
            #     image=image,
            #     prompt=prompt,
            #     negative_prompt=negative_prompt,
            #     num_frames=num_frames,
            #     height=height,
            #     width=width,
            #     fps=fps,
            #     guidance_scale=guidance_scale,
            #     num_inference_steps=num_inference_steps,
            #     generator=generator,
            # )
            # frames = result.frames[0]
            #
            # # 导出视频
            # from diffusers.utils import export_to_video
            # export_to_video(frames, str(output_path), fps=fps)
            # ============================================

            # 演示模式: 生成一个简单的视频占位
            progress(0.1, desc="准备生成...")
            self._generate_placeholder_video(image, output_path, num_frames, fps)
            progress(1.0, desc="完成!")

            logger.info(f"视频生成完成: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"视频生成失败: {e}")
            raise

    def _generate_placeholder_video(
        self,
        image: Image.Image,
        output_path: Path,
        num_frames: int,
        fps: int,
    ):
        """生成占位视频（演示用）"""
        try:
            import imageio
            frames = []
            w, h = image.size
            # 缩放到目标尺寸
            img_resized = image.resize((min(w, 1280), min(h, 720)))
            arr = np.array(img_resized)

            for i in range(num_frames):
                # 简单的淡入淡出效果
                alpha = np.sin(i / num_frames * np.pi)
                frame = (arr * (0.7 + 0.3 * alpha)).astype(np.uint8)
                frames.append(frame)

            imageio.mimsave(str(output_path), frames, fps=fps, codec='libx264', quality=8)
        except ImportError:
            # 如果 imageio 不可用，只写一个空 mp4 文件
            output_path.write_bytes(b"")


# 全局生成器实例
generator = H3VideoGenerator()


# ============== Gradio 界面 ==============

def generate_video(
    image,
    prompt,
    negative_prompt,
    num_frames,
    fps,
    height,
    width,
    guidance_scale,
    num_inference_steps,
    seed,
):
    """视频生成处理函数"""
    try:
        if image is None:
            raise gr.Error("请先上传参考图片！")
        if not prompt or not prompt.strip():
            raise gr.Error("请输入提示词！")

        output_path = generator.generate(
            image=image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_frames=num_frames,
            fps=fps,
            height=height,
            width=width,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            seed=int(seed) if seed >= 0 else -1,
        )
        return output_path, f"✅ 生成成功: {Path(output_path).name}"
    except Exception as e:
        logger.exception("生成失败")
        return None, f"❌ 生成失败: {str(e)}"


def build_ui() -> gr.Blocks:
    """构建 Gradio 界面"""
    with gr.Blocks(
        title="MiniMax H3 图参考视频生成",
        theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="purple"),
        css="""
        .main-header { text-align: center; margin-bottom: 20px; }
        .gen-btn { height: 60px !important; font-size: 18px !important; }
        """
    ) as demo:
        # 标题
        gr.Markdown(
            """
            # 🎬 MiniMax H3 图参考视频生成
            **基于参考图片 + 文本提示词生成高质量视频**

            上传一张参考图片，输入你想生成的视频描述，H3 模型会基于图参考生成对应的视频。
            """,
            elem_classes="main-header",
        )

        with gr.Row():
            # 左侧: 输入区
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 📥 输入")

                    image_input = gr.Image(
                        label="参考图片",
                        type="pil",
                        sources=["upload", "clipboard"],
                        height=350,
                    )

                    prompt_input = gr.Textbox(
                        label="提示词 (Prompt)",
                        placeholder="例如: A woman walking on the beach at sunset, cinematic, slow motion...",
                        lines=4,
                    )

                    negative_prompt = gr.Textbox(
                        label="负面提示词 (Negative Prompt)",
                        placeholder="不希望出现的元素，例如: blurry, low quality, distortion...",
                        lines=2,
                        value="blurry, low quality, distorted, watermark, text",
                    )

                with gr.Accordion("⚙️ 高级参数", open=False):
                    with gr.Row():
                        num_frames = gr.Slider(
                            label="视频帧数",
                            minimum=16,
                            maximum=192,
                            step=8,
                            value=96,
                        )
                        fps = gr.Slider(
                            label="帧率 (FPS)",
                            minimum=8,
                            maximum=60,
                            step=1,
                            value=24,
                        )

                    with gr.Row():
                        height = gr.Slider(
                            label="高度",
                            minimum=256,
                            maximum=1080,
                            step=64,
                            value=720,
                        )
                        width = gr.Slider(
                            label="宽度",
                            minimum=256,
                            maximum=1920,
                            step=64,
                            value=1280,
                        )

                    with gr.Row():
                        guidance_scale = gr.Slider(
                            label="引导强度 (CFG)",
                            minimum=1.0,
                            maximum=20.0,
                            step=0.5,
                            value=7.5,
                        )
                        num_inference_steps = gr.Slider(
                            label="推理步数",
                            minimum=10,
                            maximum=100,
                            step=1,
                            value=30,
                        )

                    seed = gr.Number(
                        label="随机种子 (-1 为随机)",
                        value=-1,
                        precision=0,
                    )

                generate_btn = gr.Button(
                    "🚀 生成视频",
                    variant="primary",
                    elem_classes="gen-btn",
                )

            # 右侧: 输出区
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 📤 输出")

                    video_output = gr.Video(
                        label="生成的视频",
                        height=450,
                        autoplay=True,
                        show_download_button=True,
                    )

                    status_text = gr.Textbox(
                        label="状态",
                        interactive=False,
                        value="等待生成...",
                    )

                    gr.Markdown(
                        """
                        **使用提示:**
                        - 上传清晰的参考图片可获得更好的生成效果
                        - 提示词越具体，生成结果越可控
                        - 推理步数越多质量越好但耗时更长
                        - 遇到 CUDA 显存不足时，请调小视频尺寸或帧数
                        """
                    )

        # 事件绑定
        generate_btn.click(
            fn=generate_video,
            inputs=[
                image_input,
                prompt_input,
                negative_prompt,
                num_frames,
                fps,
                height,
                width,
                guidance_scale,
                num_inference_steps,
                seed,
            ],
            outputs=[video_output, status_text],
        )

        # 示例
        gr.Examples(
            examples=[
                [
                    None,
                    "A majestic eagle soaring through misty mountains at sunrise, cinematic, 4K",
                    "blurry, low quality",
                    96, 24, 720, 1280, 7.5, 30, -1,
                ],
                [
                    None,
                    "A woman dancing gracefully in a field of flowers, slow motion, golden hour lighting",
                    "blurry, distorted",
                    120, 24, 720, 1280, 8.0, 40, 42,
                ],
            ],
            inputs=[
                image_input,
                prompt_input,
                negative_prompt,
                num_frames,
                fps,
                height,
                width,
                guidance_scale,
                num_inference_steps,
                seed,
            ],
            label="示例 (请先上传参考图片)",
        )

    return demo


# ============== 启动 ==============

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MiniMax H3 Gradio 视频生成服务启动中...")
    logger.info(f"CUDA_HOME: {os.getenv('CUDA_HOME')}")
    logger.info(f"MODEL_PATH: {MODEL_PATH}")
    logger.info(f"OUTPUT_DIR: {OUTPUT_DIR}")
    logger.info("=" * 60)

    demo = build_ui()

    demo.queue(
        max_size=10,
        status_update_rate=5,
    ).launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        share=False,
        show_error=True,
    )
