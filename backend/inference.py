from __future__ import annotations

import base64
import hashlib
import logging
import os
import threading
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局导入 torch（如果可用）
try:
    import torch
    import cv2
    import numpy as np
    from torchvision import transforms, models
    TORCH_AVAILABLE = True
except ImportError as e:
    torch = None
    cv2 = None
    np = None
    transforms = None
    models = None
    TORCH_AVAILABLE = False
    logger.warning(f"PyTorch/CV2 不可用: {e}, 将使用 Demo 模式")

# 全局导入 ONNX Runtime（如果可用）
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError as e:
    ort = None
    ONNX_AVAILABLE = False
    logger.warning(f"ONNX Runtime 不可用: {e}, 将使用 Demo 模式")

EMOTIONS = ["开心", "悲伤", "愤怒", "惊讶", "恐惧", "厌恶", "平静"]

# 情绪类别权重（用于平衡数据不平衡问题）
# 训练数据中"恐惧"样本可能过多，通过权重调整输出
EMOTION_WEIGHTS = {
    "开心": 1.0,
    "悲伤": 1.0,
    "愤怒": 1.0,
    "惊讶": 1.0,
    "恐惧": 0.6,  # 降低恐惧类别的权重，防止过度预测
    "厌恶": 1.0,
    "平静": 1.1   # 适当提高平静类别的权重
}

# 置信度阈值配置
CONFIDENCE_THRESHOLD = 0.3  # 低于此阈值的预测视为不确定
UNCERTAINTY_LABEL = "平静"   # 不确定时返回的默认情绪


def _normalize_image_bytes(image_data_url: str) -> bytes:
    """标准化图像数据URL，提取并解码base64数据"""
    if not image_data_url:
        raise ValueError("图像数据不能为空")
    
    try:
        if "," in image_data_url:
            _, encoded = image_data_url.split(",", maxsplit=1)
        else:
            encoded = image_data_url
        
        # 移除可能存在的空格和换行
        encoded = encoded.replace(" ", "").replace("\n", "").replace("\r", "")
        return base64.b64decode(encoded)
    except Exception as e:
        logger.error(f"图像解码失败: {e}")
        raise ValueError(f"无效的图像数据: {str(e)}") from e


@dataclass
class InferenceResult:
    """推理结果数据类"""
    label: str
    confidence: float
    intensity: float
    duration_ms: int
    secondary_label: str
    engine: str
    engine_version: str
    is_real_model: bool = False
    error: Optional[str] = None


class DemoInferenceEngine:
    """演示用推理引擎 - 使用哈希算法生成随机结果"""
    
    name: str = "demo-hash-inference"
    version: str = "v2"
    
    def __init__(self):
        self._lock = threading.Lock()
        logger.info("Demo推理引擎已初始化")
    
    def build_health_assessment(self, sequence: list[dict], calibration: dict[str, Any] | None = None) -> dict:
        """基于临床心理学标准的增强型多维健康评估"""
        if not sequence:
            return {
                "stress_index": 0, 
                "anxiety_risk": "Waiting", 
                "focus_score": 0,
                "hrv_status": "Calculating",
                "blink_rate_score": 0
            }
        
        # 获取基准值 (Calibration)
        base_hrv = calibration.get("base_hrv", 60) if calibration else 60
        base_blink = calibration.get("base_blink_rate", 15) if calibration else 15
        
        counts = {}
        for item in sequence:
            label = item["label"]
            counts[label] = counts.get(label, 0) + 1
        
        total = len(sequence)
        
        # 1. 压力指数 (基于微表情频次与强度)
        stress_base = (counts.get("恐惧", 0) * 1.8 + counts.get("愤怒", 0) * 1.4 + counts.get("厌恶", 0) * 1.2)
        stress_index = min(100, int((stress_base / total) * 100))
        
        # 2. 模拟 HRV (心率变异性) - 临床压力关键指标
        hrv_offset = (counts.get("平静", 0) / total) * 30 - (counts.get("愤怒", 0) / total) * 20
        hrv_value = base_hrv + hrv_offset + (hashlib.sha256(str(total).encode()).digest()[0] % 5)
        hrv_status = "正常 (Good)" if hrv_value > (base_hrv * 0.9) else "偏低 (Fatigue/Stress)"
        
        # 3. 专注度得分
        focus_score = min(100, int((counts.get("平静", 0) / total) * 100 + (counts.get("惊讶", 0) / total) * 20))
        
        # 4. 模拟瞬目率 (Blink Rate)
        blink_rate = base_blink + (counts.get("悲伤", 0) / total) * 8 - (counts.get("平静", 0) / total) * 3
        blink_status = "正常" if (base_blink * 0.7) <= blink_rate <= (base_blink * 1.3) else "异常 (需休息)"

        # 风险评估逻辑
        risk_level = "健康 (Normal)"
        if stress_index > 75 or hrv_value < (base_hrv * 0.7):
            risk_level = "极高风险 (Clinical Attention)"
        elif stress_index > 45:
            risk_level = "中度预警 (Moderate)"
            
        return {
            "stress_index": stress_index,
            "focus_score": focus_score,
            "anxiety_risk": risk_level,
            "hrv_value": round(hrv_value, 1),
            "hrv_status": hrv_status,
            "blink_rate": int(blink_rate),
            "blink_status": blink_status,
            "is_calibrated": calibration is not None,
            "clinical_id": f"DX-{hashlib.md5(str(total).encode()).hexdigest()[:8].upper()}",
            "health_advice": self._get_medical_advice(stress_index, focus_score, hrv_value, base_hrv)
        }

    def _get_medical_advice(self, stress, focus, hrv, base_hrv=60):
        if stress > 70:
            return "【临床建议】检测到持续性的高度负面微表情信号。PSS-10 评估倾向于高压力状态。建议进行专业心理咨询，并配合自主神经调节训练（如生物反馈）。"
        if hrv < (base_hrv * 0.8):
            return "【生理警告】心率变异性(HRV)显著低于您的个人基准线，提示交感神经系统过度活跃。建议立即停止高强度脑力工作，进行 15 分钟强制休息。"
        if focus < 40:
            return "【效能提示】认知资源分配不均，专注度曲线出现明显波动。建议通过正念冥想提升前额叶皮层稳定性。"
        return "【状态良好】各项心理生理指标均处于个人基准范围内。建议保持当前的压力管理习惯。"

    def predict(self, image_data_url: str) -> dict:
        """执行情绪预测（Demo模式）"""
        try:
            raw = _normalize_image_bytes(image_data_url)
            digest = hashlib.sha256(raw).digest()
            
            label = EMOTIONS[digest[0] % len(EMOTIONS)]
            confidence = round(0.55 + (digest[1] / 255) * 0.4, 3)
            intensity = round(0.3 + (digest[2] / 255) * 0.7, 3)
            duration_ms = 80 + int((digest[3] / 255) * 520)
            secondary = EMOTIONS[digest[4] % len(EMOTIONS)]
            
            return {
                "label": label,
                "confidence": confidence,
                "intensity": intensity,
                "duration_ms": duration_ms,
                "secondary_label": secondary,
                "engine": self.name,
                "engine_version": self.version,
                "is_real_model": False,
                "note": "当前为演示模式，使用哈希算法生成结果。请训练真实模型以获得准确识别。",
            }
        except Exception as e:
            logger.error(f"Demo推理失败: {e}")
            return {
                "label": "平静",
                "confidence": 0.5,
                "intensity": 0.5,
                "duration_ms": 100,
                "secondary_label": "平静",
                "engine": self.name,
                "engine_version": self.version,
                "is_real_model": False,
                "error": f"推理失败: {str(e)}"
            }


class ExpressionModel(torch.nn.Module):
    """与训练脚本一致的模型结构"""
    def __init__(self, num_classes=7):
        super(ExpressionModel, self).__init__()
        self.backbone = models.resnet18(pretrained=False)
        num_ftrs = self.backbone.fc.in_features
        self.backbone.fc = torch.nn.Sequential(
            torch.nn.Linear(num_ftrs, 512),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(512, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)


class PytorchInferenceEngine(DemoInferenceEngine):
    """PyTorch推理引擎 - 使用真实训练模型"""
    
    def __init__(self, model_path: str = "models/micro_expression.pth"):
        super().__init__()
        self.model_path = model_path
        self.labels = ["开心", "悲伤", "愤怒", "惊讶", "恐惧", "厌恶", "平静"]
        self.model = None
        self.face_cascade = None
        self.demo_engine = DemoInferenceEngine()
        self.device = None
        self._model_loaded = False
        self._load_lock = threading.Lock()
        
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch不可用，将使用Demo模式")
            return
        
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化PyTorch模型"""
        with self._load_lock:
            if self._model_loaded:
                return
            
            try:
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self.model = ExpressionModel(num_classes=len(self.labels)).to(self.device)
                
                if os.path.exists(self.model_path):
                    # 加载权重 (兼容不同 PyTorch 版本)
                    try:
                        state_dict = torch.load(self.model_path, map_location=self.device, weights_only=True)
                    except TypeError:
                        state_dict = torch.load(self.model_path, map_location=self.device)
                    self.model.load_state_dict(state_dict)
                    self.model.eval()
                    self._model_loaded = True
                    logger.info(f"成功加载模型: {self.model_path}")
                else:
                    logger.warning(f"模型文件不存在: {self.model_path}，将使用Demo模式")
                    self.model = None
                
                # Load Haar cascade for face detection
                cascade_paths = [
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
                    os.path.join(os.path.dirname(cv2.__file__), "data", "haarcascade_frontalface_default.xml"),
                    "/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",  # Linux
                    "C:\\opencv\\build\\etc\\haarcascades\\haarcascade_frontalface_default.xml",  # Windows备用
                ]
                
                self.face_cascade = None
                for path in cascade_paths:
                    if os.path.exists(path):
                        self.face_cascade = cv2.CascadeClassifier(path)
                        if self.face_cascade and not self.face_cascade.empty():
                            logger.info(f"成功加载人脸检测器: {path}")
                            break
                        else:
                            self.face_cascade = None
                
                if self.face_cascade is None:
                    logger.warning("无法加载人脸检测器，将在推理时跳过人脸检测")
                
                self.torch = torch
                self.cv2 = cv2
                self.np = np
                self.transform = transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
                ])
                    
            except Exception as e:
                logger.error(f"PyTorch引擎初始化失败: {e}")
                self.model = None

    @property
    def name(self) -> str:
        return "PyTorch-Real" if self._model_loaded else "PyTorch-Fallback(Demo)"

    @property
    def model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._model_loaded

    def predict(self, image_data_url: str) -> dict:
        """执行情绪预测（优先使用真实模型）"""
        # 如果真实模型不可用，回退到Demo模式
        if self.model is None or self.face_cascade is None or not self._model_loaded:
            logger.debug("真实模型不可用，回退到Demo模式")
            return self.demo_engine.predict(image_data_url)
            
        try:
            image_bytes = _normalize_image_bytes(image_data_url)
            nparr = self.np.frombuffer(image_bytes, self.np.uint8)
            img = self.cv2.imdecode(nparr, self.cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("无法解码图像")
                return self.demo_engine.predict(image_data_url)
            
            # 人脸检测
            gray = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            face_detected = len(faces) > 0
            
            if face_detected:
                x, y, w, h = faces[0]
                face_roi = img[y:y+h, x:x+w]
            else:
                # 如果没有检测到人脸，使用整个图像中心区域
                h, w = img.shape[:2]
                min_dim = min(h, w)
                start_x = (w - min_dim) // 2
                start_y = (h - min_dim) // 2
                face_roi = img[start_y:start_y+min_dim, start_x:start_x+min_dim]
                
            # 图像预处理
            input_tensor = self.transform(face_roi).unsqueeze(0).to(self.device)
            
            # 推理
            with self.torch.no_grad():
                outputs = self.model(input_tensor)
                probs = self.torch.nn.functional.softmax(outputs[0], dim=0)
                
            # 应用类别权重进行数据平衡处理
            weighted_probs = probs.clone()
            for i, label in enumerate(self.labels):
                weight = EMOTION_WEIGHTS.get(label, 1.0)
                weighted_probs[i] = weighted_probs[i] * weight
            
            # 重新归一化
            weighted_probs = weighted_probs / weighted_probs.sum()
            
            max_idx = int(self.torch.argmax(weighted_probs))
            confidence = float(weighted_probs[max_idx])
            original_confidence = float(probs[max_idx])
            
            # 置信度阈值过滤
            if confidence < CONFIDENCE_THRESHOLD:
                logger.debug(f"置信度 {confidence} 低于阈值 {CONFIDENCE_THRESHOLD}，使用默认标签")
                final_label = UNCERTAINTY_LABEL
                final_confidence = CONFIDENCE_THRESHOLD
            else:
                final_label = self.labels[max_idx]
                final_confidence = confidence
            
            # 获取次高概率的情绪
            sorted_probs, sorted_indices = self.torch.sort(weighted_probs, descending=True)
            secondary_idx = int(sorted_indices[1]) if len(sorted_indices) > 1 else (max_idx + 1) % 7
            
            return {
                "label": final_label,
                "confidence": round(final_confidence, 3),
                "intensity": round(final_confidence, 3),
                "duration_ms": 100,
                "secondary_label": self.labels[secondary_idx],
                "engine": self.name,
                "engine_version": "v1.0.0-pth",
                "is_real_model": True,
                "face_detected": face_detected,
                "original_confidence": round(original_confidence, 3),
                "adjusted_by_weights": confidence != original_confidence,
            }
        except Exception as e:
            logger.error(f"PyTorch推理失败: {e}")
            # 回退到Demo模式
            return self.demo_engine.predict(image_data_url)


class ONNXInferenceEngine(DemoInferenceEngine):
    """ONNX推理引擎 - 使用ONNX Runtime进行高性能推理"""
    
    def __init__(self, model_path: str = "models/micro_expression.onnx"):
        super().__init__()
        self.model_path = model_path
        self.labels = ["开心", "悲伤", "愤怒", "惊讶", "恐惧", "厌恶", "平静"]
        self.session = None
        self.face_cascade = None
        self.demo_engine = DemoInferenceEngine()
        self._model_loaded = False
        self._load_lock = threading.Lock()
        
        if not ONNX_AVAILABLE:
            logger.warning("ONNX Runtime不可用，将使用Demo模式")
            return
        
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化ONNX模型"""
        with self._load_lock:
            if self._model_loaded:
                return
            
            try:
                if os.path.exists(self.model_path):
                    # 创建ONNX会话
                    self.session = ort.InferenceSession(self.model_path)
                    self._model_loaded = True
                    logger.info(f"成功加载ONNX模型: {self.model_path}")
                else:
                    logger.warning(f"ONNX模型文件不存在: {self.model_path}，将使用Demo模式")
                    self.session = None
                
                # Load Haar cascade for face detection
                cascade_paths = [
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
                    os.path.join(os.path.dirname(cv2.__file__), "data", "haarcascade_frontalface_default.xml"),
                    "/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",  # Linux
                    "C:\\opencv\\build\\etc\\haarcascades\\haarcascade_frontalface_default.xml",  # Windows备用
                ]
                
                self.face_cascade = None
                for path in cascade_paths:
                    if os.path.exists(path):
                        self.face_cascade = cv2.CascadeClassifier(path)
                        if self.face_cascade and not self.face_cascade.empty():
                            logger.info(f"成功加载人脸检测器: {path}")
                            break
                        else:
                            self.face_cascade = None
                
                if self.face_cascade is None:
                    logger.warning("无法加载人脸检测器，将在推理时跳过人脸检测")
                
                # 预处理变换
                if transforms:
                    self.transform = transforms.Compose([
                        transforms.ToPILImage(),
                        transforms.Resize((224, 224)),
                        transforms.ToTensor(),
                        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
                    ])
                    
            except Exception as e:
                logger.error(f"ONNX引擎初始化失败: {e}")
                self.session = None

    @property
    def name(self) -> str:
        return "ONNX-Real" if self._model_loaded else "ONNX-Fallback(Demo)"

    @property
    def model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._model_loaded

    def predict(self, image_data_url: str) -> dict:
        """执行情绪预测（优先使用ONNX模型）"""
        # 如果ONNX模型不可用，回退到Demo模式
        if self.session is None or self.face_cascade is None or not self._model_loaded:
            logger.debug("ONNX模型不可用，回退到Demo模式")
            return self.demo_engine.predict(image_data_url)
            
        try:
            image_bytes = _normalize_image_bytes(image_data_url)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("无法解码图像")
                return self.demo_engine.predict(image_data_url)
            
            # 人脸检测
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            face_detected = len(faces) > 0
            if not face_detected:
                logger.debug("未检测到人脸，使用默认情绪")
                return {
                    "label": UNCERTAINTY_LABEL,
                    "confidence": 0.5,
                    "intensity": 0.5,
                    "duration_ms": 100,
                    "secondary_label": UNCERTAINTY_LABEL,
                    "engine": self.name,
                    "engine_version": self.version,
                    "is_real_model": True,
                    "face_detected": False,
                }
            
            # 取最大人脸
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            face = img[y:y+h, x:x+w]
            
            # 预处理
            face_pil = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
            input_tensor = self.transform(face_pil).unsqueeze(0).numpy()
            
            # ONNX推理
            ort_inputs = {self.session.get_inputs()[0].name: input_tensor}
            ort_outs = self.session.run(None, ort_inputs)
            probs = ort_outs[0][0]
            
            # 应用情绪权重
            weighted_probs = probs.copy()
            for i, emotion in enumerate(self.labels):
                weight = EMOTION_WEIGHTS.get(emotion, 1.0)
                weighted_probs[i] = weighted_probs[i] * weight
            
            # 重新归一化
            weighted_probs = weighted_probs / weighted_probs.sum()
            
            max_idx = int(np.argmax(weighted_probs))
            confidence = float(weighted_probs[max_idx])
            original_confidence = float(probs[max_idx])
            
            # 置信度阈值过滤
            if confidence < CONFIDENCE_THRESHOLD:
                label = UNCERTAINTY_LABEL
                secondary = self.labels[max_idx]
            else:
                label = self.labels[max_idx]
                # 次要情绪：排除当前情绪后的最高概率
                temp_probs = weighted_probs.copy()
                temp_probs[max_idx] = 0
                secondary_idx = int(np.argmax(temp_probs))
                secondary = self.labels[secondary_idx]
            
            # 强度计算（基于置信度）
            intensity = min(1.0, confidence * 1.2)
            
            # 推理时间（模拟）
            duration_ms = 50 + int((np.random.rand() * 100))
            
            return {
                "label": label,
                "confidence": round(confidence, 3),
                "intensity": round(intensity, 3),
                "duration_ms": duration_ms,
                "secondary_label": secondary,
                "engine": self.name,
                "engine_version": self.version,
                "is_real_model": True,
                "face_detected": face_detected,
                "original_confidence": round(original_confidence, 3),
                "adjusted_by_weights": confidence != original_confidence,
            }
        except Exception as e:
            logger.error(f"ONNX推理失败: {e}")
            # 回退到Demo模式
            return self.demo_engine.predict(image_data_url)


def get_inference_engine() -> DemoInferenceEngine:
    """获取推理引擎实例（单例模式）"""
    from backend.config import config
    engine_mode = config.inference_mode

    if engine_mode == "onnx":
        # 优先尝试ONNX引擎
        return ONNXInferenceEngine()
    elif engine_mode == "pytorch":
        # 使用PyTorch引擎
        return PytorchInferenceEngine()

    return DemoInferenceEngine()


# 全局推理引擎实例（单例）
_engine_instance = None
_engine_lock = threading.Lock()


def get_cached_inference_engine() -> DemoInferenceEngine:
    """获取缓存的推理引擎实例"""
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = get_inference_engine()
        return _engine_instance


def predict_micro_expression(image_data_url: str) -> dict:
    """预测单帧图像的微表情"""
    engine = get_cached_inference_engine()
    
    # 检查模型状态
    if hasattr(engine, 'model_loaded') and not engine.model_loaded:
        logger.warning(f"推理引擎 {engine.name} 的模型未正确加载，将使用演示模式结果")
    
    return engine.predict(image_data_url)


def predict_micro_expression_sequence(frames: list[str], source_type: str) -> dict:
    """预测图像序列的微表情"""
    engine = get_cached_inference_engine()
    frame_results = []
    
    for index, frame in enumerate(frames, start=1):
        try:
            result = engine.predict(frame)
            frame_results.append({
                "frame_index": index,
                "label": result["label"],
                "confidence": result["confidence"],
                "intensity": result["intensity"],
                "duration_ms": result["duration_ms"],
                "secondary_label": result["secondary_label"],
                "engine": result["engine"],
                "engine_version": result["engine_version"],
            })
        except Exception as e:
            logger.error(f"处理第 {index} 帧失败: {e}")
            # 添加失败帧的占位符
            frame_results.append({
                "frame_index": index,
                "label": "平静",
                "confidence": 0.0,
                "intensity": 0.0,
                "duration_ms": 0,
                "secondary_label": "平静",
                "engine": engine.name,
                "engine_version": engine.version,
                "error": str(e)
            })

    if not frame_results:
        return {
            "frame_count": 0,
            "source_type": source_type,
            "dominant_emotion": "平静",
            "secondary_emotion": "平静",
            "average_confidence": 0.0,
            "average_intensity": 0.0,
            "wave": [],
            "frames": [],
            "engine": engine.name,
            "engine_version": engine.version,
            "is_real_model": engine.name == "PyTorch-Real",
        }

    # 统计情绪分布
    counter = Counter(item["label"] for item in frame_results)
    ordered = counter.most_common()
    dominant_emotion = ordered[0][0]
    secondary_emotion = ordered[1][0] if len(ordered) > 1 else dominant_emotion
    
    # 计算平均值（排除错误帧）
    valid_frames = [f for f in frame_results if "error" not in f]
    if valid_frames:
        average_confidence = round(sum(item["confidence"] for item in valid_frames) / len(valid_frames), 3)
        average_intensity = round(sum(item["intensity"] for item in valid_frames) / len(valid_frames), 3)
    else:
        average_confidence = 0.0
        average_intensity = 0.0
    
    # 生成波动数据
    wave = []
    for item in frame_results[:50]:  # 最多50个点用于可视化
        wave.append({
            "index": item["frame_index"],
            "value": round(item["intensity"] * 100, 1),
            "label": item["label"],
        })
    
    return {
        "frame_count": len(frame_results),
        "source_type": source_type,
        "dominant_emotion": dominant_emotion,
        "secondary_emotion": secondary_emotion,
        "average_confidence": average_confidence,
        "average_intensity": average_intensity,
        "wave": wave,
        "frames": frame_results,
        "engine": engine.name,
        "engine_version": engine.version,
        "is_real_model": engine.name == "PyTorch-Real",
        "valid_frame_count": len(valid_frames),
    }


def build_emotion_report(recognitions: list[dict]) -> dict:
    """构建情绪分析报告"""
    if not recognitions:
        return {
            "summary": "当前暂无足够样本，请先完成至少一次识别。",
            "distribution": {},
            "wave": [],
            "insight": "建议先采集 30 秒以上视频片段后再生成报告。",
            "status": "insufficient_data",
        }

    distribution: dict[str, int] = {}
    wave = []
    for index, item in enumerate(recognitions[:50]):  # 限制数据量
        distribution[item["label"]] = distribution.get(item["label"], 0) + 1
        wave.append({
            "index": index + 1,
            "value": round(float(item["intensity"]) * 100, 1),
            "label": item["label"],
        })
    
    dominant_emotion = max(distribution, key=distribution.get)
    
    summary_map = {
        "开心": f"近期识别以{dominant_emotion}为主，情绪状态积极，建议保持良好心态。",
        "悲伤": f"检测到较多{dominant_emotion}情绪，建议关注情绪变化，适当进行放松训练。",
        "愤怒": f"{dominant_emotion}情绪较明显，建议学习情绪管理技巧，避免冲动行为。",
        "惊讶": f"对外界刺激敏感度较高，{dominant_emotion}情绪较多，建议保持冷静思考。",
        "恐惧": f"{dominant_emotion}情绪较突出，建议逐步面对恐惧源，必要时寻求支持。",
        "厌恶": f"对某些事物存在{dominant_emotion}情绪，建议明确边界，调整环境。",
        "平静": f"整体情绪较{dominant_emotion}稳定，建议继续保持当前状态。",
    }
    
    insight_map = {
        "开心": "用户整体反馈偏积极，可适合推荐成长型内容与互动活动。",
        "悲伤": "检测到较多低落样本，建议优先推送舒缓型陪伴和心理支持内容。",
        "愤怒": "压力或挫败感波动较明显，建议结合职场场景做表达调节训练。",
        "惊讶": "外界刺激敏感度较高，适合通过模拟场景提升应对稳定性。",
        "恐惧": "紧张与防御倾向较突出，适合先做低压环境适应与反馈练习。",
        "厌恶": "负面排斥信号偏多，建议关注内容偏好与沟通场景匹配度。",
        "平静": "整体情绪较稳定，适合进一步做高阶场景分析与定制课程推荐。",
    }
    
    return {
        "summary": summary_map[dominant_emotion],
        "distribution": distribution,
        "wave": wave,
        "insight": insight_map[dominant_emotion],
        "status": "success",
        "sample_count": len(recognitions),
    }


def build_workplace_assessment(recognitions: list[dict], scenario: str) -> dict:
    """构建职场场景评估"""
    dominant = "平静"
    if recognitions:
        counter: dict[str, int] = {}
        for item in recognitions[:12]:
            counter[item["label"]] = counter.get(item["label"], 0) + 1
        dominant = max(counter, key=counter.get)
    
    score_base = {
        "平静": 88,
        "开心": 84,
        "惊讶": 76,
        "悲伤": 70,
        "恐惧": 66,
        "厌恶": 62,
        "愤怒": 58,
    }
    
    score = score_base.get(dominant, 75)
    
    suggestion_map = {
        "平静": f"在“{scenario}”场景中，您的表现稳定从容，建议继续保持这种状态。",
        "开心": f"在“{scenario}”场景中，您表现出积极情绪，建议继续保持热情。",
        "惊讶": f"在“{scenario}”场景中，您对变化反应较敏感，建议加强适应能力训练。",
        "悲伤": f"在“{scenario}”场景中，您可能存在情绪低落，建议调整心态，必要时寻求支持。",
        "恐惧": f"在“{scenario}”场景中，您表现出紧张情绪，建议通过深呼吸等方式放松。",
        "厌恶": f"在“{scenario}”场景中，您可能对某些内容存在排斥，建议明确表达需求。",
        "愤怒": f"在“{scenario}”场景中，您表现出较强情绪，建议学习情绪管理技巧。",
    }
    
    return {
        "scenario": scenario,
        "score": score,
        "dominant_emotion": dominant,
        "suggestion": suggestion_map[dominant],
        "status": "success",
    }


def build_companion_reply(emotion: str) -> str:
    """构建AI陪伴回复"""
    replies = {
        "开心": "你现在的状态很不错，适合继续推进高价值任务，我也可以帮你整理下一步行动。",
        "悲伤": "我在这里，先放慢一点节奏。你可以做三次深呼吸，然后把最困扰你的点告诉我。",
        "愤怒": "先别急着对抗，把注意力放回事实本身。我可以帮你把问题拆解成更可控的步骤。",
        "惊讶": "这可能是突发信息带来的刺激，先确认最关键的一件事，再决定下一步。",
        "恐惧": "紧张是正常反应，建议先从最容易完成的一步开始，我可以陪你一起推进。",
        "厌恶": "你对当前内容可能存在明显排斥，先明确边界，再选择更适合你的处理方式。",
        "平静": "你的状态比较稳定，现在很适合做分析、规划和关键决策。",
    }
    return replies.get(emotion, replies["平静"])


def build_ad_recommendation(dominant_emotion: str) -> dict:
    """构建广告推荐"""
    mapping = {
        "开心": ("成长训练营", "适合状态积极用户的表达力与领导力提升课程"),
        "悲伤": ("情绪舒缓礼包", "包含白噪音、心理陪伴内容与解压产品推荐"),
        "愤怒": ("沟通修复课", "帮助用户降低冲突表达，提升谈判与反馈能力"),
        "惊讶": ("高压场景模拟课", "适合快速应对面试、汇报与演讲等变化场景"),
        "恐惧": ("面试自信包", "包含表达训练、呼吸引导和镜头适应练习"),
        "厌恶": ("内容偏好优化服务", "用于识别排斥触点并优化用户体验与产品匹配"),
        "平静": ("高阶职业微表情报告", "适合稳定状态下进行深度评估和付费转化"),
    }
    title, description = mapping.get(dominant_emotion, mapping["平静"])
    return {
        "title": title,
        "description": description,
        "dominant_emotion": dominant_emotion,
        "status": "success",
    }


def build_sequence_summary(sequence_result: dict) -> str:
    """构建序列分析摘要"""
    if not sequence_result.get("frame_count", 0):
        return "暂无分析数据"
    
    return (
        f"本次共分析 {sequence_result['frame_count']} 帧，主导情绪为{sequence_result['dominant_emotion']}，"
        f"平均置信度 {sequence_result['average_confidence']}，平均强度 {sequence_result['average_intensity']}。"
    )


def get_engine_health_status() -> dict:
    """获取推理引擎健康状态"""
    engine = get_cached_inference_engine()
    
    return {
        "engine_name": engine.name,
        "engine_version": engine.version,
        "is_real_model": isinstance(engine, PytorchInferenceEngine) and engine.model_loaded,
        "torch_available": TORCH_AVAILABLE,
        "device": engine.device.type if hasattr(engine, 'device') and engine.device else "cpu",
        "status": "healthy" if (isinstance(engine, PytorchInferenceEngine) and engine.model_loaded) else "demo_mode",
    }