# 智能情绪健康与压力临床测评系统演示文稿 (Medical v6.0)

本项目是一个基于**计算机视觉与面部微表情识别技术**的临床级心理健康监测与压力评估商业化原型。它将前沿的深度学习技术与临床心理学标准相结合，专注于可视化情绪分析，为个人情绪管理、企业员工关怀及医疗辅助诊断提供数据支撑。

## 🌟 核心亮点

### 1. 视频流实时情绪分析
- **摄像头实时捕捉**：支持实时面部情绪识别，实时反馈情绪状态
- **7种核心情绪识别**：开心、悲伤、愤怒、惊讶、恐惧、厌恶、平静
- **情绪强度量化**：精确到百分比的情绪强度分析

### 2. 生理指标集成
- **心率 (Heart Rate)** 模拟监测
- **心率变异性 (HRV)** 分析
- **呼吸频率** 评估
- **血压** 模拟数据

### 3. 临床级心理量表评估
- **SAS 焦虑自评量表** (20题)
- **SDS 抑郁自评量表** (20题)
- **PSS 压力知觉量表** (10题)

### 4. 专业数据分析报告
- **情绪趋势分析图表**：可视化情绪波动曲线
- **临床PDF报告导出**：包含数字化签名与唯一审计ID
- **健康建议生成**：基于分析结果的个性化建议

### 5. 心理健康服务
- **深呼吸练习**：带动画引导的呼吸训练
- **正念冥想模式**：沉浸式放松体验
- **放松音乐播放**：内置舒缓音乐库

### 6. 情绪日记功能
- **每日心情记录**：1-5级心情评分
- **心情日历可视化**：直观展示情绪变化趋势

### 7. 专家咨询模块
- **在线预约**：多种咨询类型可选
- **匿名咨询**：AI心理咨询师即时响应

### 8. 用户体验优化
- **现代化UI设计**：卡片式布局、渐变背景
- **完整会员体系**：免费版/高级版/专属版
- **JWT安全认证**：符合HIPAA/GDPR数据隐私规范

## 🚀 快速开始

### 环境准备
确保已安装 Python 3.10+，并运行以下命令安装依赖：
```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 启动系统

本项目采用**前后端分离**架构，需启动两个服务：

#### 方式一：开发模式（推荐）
打开**第一个终端窗口**，启动后端服务：
```powershell
cd e:\new_deeplearn3.0
python -m uvicorn backend.main:app --reload --port 8000
```

打开**第二个终端窗口**，启动前端服务：
```powershell
cd e:\new_deeplearn3.0\frontend
python -m http.server 8080
```

访问地址：[http://localhost:8080](http://localhost:8080)

#### 方式二：单服务模式
如需简化，可将前端文件集成到后端，只需启动一个服务：
```powershell
cd e:\new_deeplearn3.0
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

访问地址：[http://localhost:8000](http://localhost:8000)

> **注意**：开发模式下前后端独立运行，便于调试；单服务模式适合快速预览。

### DeepSeek AI 配置（可选）

匿名咨询功能默认使用固定安抚话术。接入 DeepSeek API 后，可升级为真正的 AI 智能问答。

**1. 获取 API Key**

前往 [platform.deepseek.com](https://platform.deepseek.com) 注册并创建 API Key。

**2. 配置**

编辑项目根目录的 `.env` 文件，填入 Key：

```ini
DEEPSEEK_ENABLED=true
DEEPSEEK_API_KEY=sk-你的密钥
```

**3. 关闭 AI**

不需要改代码。将 `.env` 中的 `DEEPSEEK_ENABLED` 设为 `false` 即可退回固定话术：

```ini
DEEPSEEK_ENABLED=false
```

**4. 推理引擎模式**

通过 `APP_INFERENCE_MODE` 切换推理模式：

```ini
# demo = 假随机结果 / pytorch = 真实模型 / onnx = 高性能推理
APP_INFERENCE_MODE=pytorch
```

改完重启后端即生效。不配置 Key 或 API 调用失败时，系统会自动降级。

### 模型训练

训练脚本位于 `scripts/train.py`，支持 GPU 加速：

```powershell
cd e:\new_deeplearn3.0
.venv\Scripts\python.exe scripts\train.py
```

数据集要求：`datasets/data.csv`（支持像素字符串或文件名两种格式）。

### 使用流程
1. **注册/登录**：创建个人账号以保存历史评估数据
2. **实时检测**：开启摄像头进行视频流情绪分析
3. **心理评估**：完成SAS/SDS/PSS量表测试
4. **查看报告**：获取专业临床分析报告
5. **健康服务**：使用深呼吸、冥想等心理健康工具
6. **记录心情**：每日心情打卡与日记记录

## 🛠 技术架构
- **后端**：FastAPI (Python) + SQLite + PyTorch
- **前端**：原生 HTML5/CSS3 + JavaScript (ES6)
- **AI 引擎**：PyTorch原生推理 + ONNX高性能推理（支持Demo降级）
- **安全合规**：AES-256加密模拟 + 全行为审计日志

## 📋 API 端点概览

| 模块 | 端点 | 功能 |
|------|------|------|
| 认证 | `/api/auth/register` | 用户注册 |
| 认证 | `/api/auth/login` | 用户登录 |
| 情绪分析 | `/api/emotion/analyze` | 图片情绪识别 |
| 视频流 | `/api/video/start-session` | 开始视频会话 |
| 视频流 | `/api/video/process-frame` | 处理视频帧 |
| 生理指标 | `/api/health/biometrics` | 获取健康指标 |
| 心理评估 | `/api/assessment/scales/{type}` | 获取量表 |
| 心理评估 | `/api/assessment/{scale_type}` | 提交评估 |
| 报告 | `/api/reports/generate` | 生成PDF报告 |
| 心情日记 | `/api/mood/save` | 保存心情记录 |
| 心情日记 | `/api/mood/history` | 获取心情历史 |
| 咨询 | `/api/consultation/book` | 预约咨询 |
| 咨询 | `/api/consultation/anonymous` | 匿名咨询 |

---
*免责声明：本系统为商业化原型演示，分析结果仅供参考，不作为正式医疗诊断依据。*
