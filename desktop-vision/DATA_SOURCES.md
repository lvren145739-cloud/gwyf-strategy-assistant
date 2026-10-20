# 素材与验证来源

这不是随包分发的数据集。原始录像和抽帧仅保留在开发工作区研究目录，未放入下载包。源码、模型权重与样例的成功/失败记录在包中。

## 0.1训练素材（历史）

- Spazbo4 / World of Longplays，**PC Longplay Gamble With Your Friends**：https://archive.org/details/pc-longplay-gamble-with-your-friends
- 作者发布说明：https://longplays.org/infusions/forum/viewthread.php?thread_id=17176
- 可公开下载的原始录像：`https://archive.org/download/pc-longplay-gamble-with-your-friends/PC_Longplay_Gamble_With_Your_Friends.mp4`
- 视频画面显示游戏 v1.0.11。训练其牌面外观不等于使用这个旧版本的玩法规则。

开发时抽取了 225–273秒、1420–1485秒、2015–2090秒三个片段，每秒1帧，缩至1280宽；另在240、1435、2024、2066秒抽取1920×1080原始帧。片段中大部分不是可用牌面；对清晰牌进行了人工标注，训练牌块列表在 `models/model-card.json`。最后一轮实际使用19个真实牌块与合成字形训练，每类750个增强样本、15轮。点数真实素材仍未完整覆盖13种点数，多数样本来自极少的实体手牌。

可用 FFmpeg 按上述时间点抽帧；长视频支持 HTTP Range，不需要下载整段13GB原片。例：

```text
ffmpeg -ss 240 -i https://archive.org/download/pc-longplay-gamble-with-your-friends/PC_Longplay_Gamble_With_Your_Friends.mp4 -frames:v 1 -q:v 1 full-240.jpg
```

`tools/prepare_training_crops.py` 根据已经抽出的研究帧重建训练牌块。完成后运行 `tools/train.py`。视频重新编码、时间轴和解码器差异会影响像素，不承诺逐字节复现权重。模型本身附 SHA-256，使用时可验证现有权重。

## 另一视频的开发检查

- 鬼鬼Phan，**100种作弊的方法 一群人发出了赌徒的声音 末路三种结局一次看**：https://www.bilibili.com/video/BV1XGVH6DEou/
- 从510秒开始每5秒抽一帧，共26帧。检查使用其中第22帧和第25帧（约617.5和632.5秒；FFmpeg滤镜采样会存在半间隔偏移），未作为训练素材。
- 第22帧：三个清楚可见的7♣、9♠、J♦；这不是完整五张扑克手牌，不能把三张都识对说成一整手成功。
- 第25帧：极端斜角，Q♥、10♠、10♣发生误识，保留为失败样例。

开发还筛选了另一份两小时直播 `BV17HeN6AEN5`，因有效牌面少未用于训练或评价。YouTube 的 fgw 全流程录像虽被检索到，但此云环境未能下载，未作为已使用素材。

## 合成样本字体

训练脚本使用 DejaVu 系列以及以下 Google Fonts 文件；字形经过旋转、缩放、模糊和压缩增强。花色同时使用自行绘制的角形图案与字体符号。字体和视频帧均未随包附带。

- https://github.com/google/fonts/tree/main/ofl/kalam
- https://github.com/google/fonts/tree/main/ofl/lilitaone
- https://github.com/google/fonts/tree/main/apache/luckiestguy

## 0.1评价口径（历史）

`tests/vision-evaluation.json` 是六个人工选定的开发场景，包含训练相关样例和失败样例；不是随机抽样，也不是未曾看过的盲测。没有据此估算整体准确率。改进过程中参考过这些场景，因此即使来自另一视频，也只能叫开发检查，不能当独立测试集。

## 0.2数据扩充与保留样例

0.2继续使用上述19个裁块，补充第一视频1435秒的Q♥/9♦与2066秒的8♦/6♣/8♠/7♥，第二视频第17帧的K♦/2♥及第22帧的7♣/9♠/J♦，合计30个标注裁块。第22帧在0.1是开发检查，**在0.2已进入训练**，不再把它称为独立验证样例。每类真实字形去重后均衡抽样，结合更多字体、压缩与形态增强；22轮，每类1200个增强样本。记录在新模型卡的trainingRecords。

第二视频第25、26帧没有参与训练。第25帧曾用于发现朝向问题，是开发回归，不是盲测；第26帧留出另一手清晰3♣作单牌检查，也不代表完整五张牌验证。

另取第三视频 https://www.bilibili.com/video/BV1eD5x6NEEs/ 前80秒左右的抽帧，内容主要是介绍和非牌面，未用于训练。只把第1帧白鸭子场景作为独立负例，没有把它算成新的跨视频正牌识别证明。下载在约120秒超时后保留20个已完成帧，未声称拿到完整录像。原始帧和视频不随包分发。

0.2的tools/prepare_training_crops.py读取training/v01-training-records.json重建基础裁块；tools/train_v2.py从已抽好的原始帧生成新增裁块。合成花色生成器在tools/training_primitives.py。训练另需开发依赖与本地字体，普通运行不需要。
