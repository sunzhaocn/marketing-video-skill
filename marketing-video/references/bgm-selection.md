# BGM音乐库与题材搭配

用户提供桌面「短视频BGM音乐库」，实际音频导入本机 skill 的 `assets/BGM/`，沿用8类目录。`assets/bgm-index.json` 记录曲目、实际版本/演唱者、路径、来源报告、时长、音频格式和完整解码结果。文件名、下载报告属于来源描述，不等同于已试听或已验证版权。库内原说明标注仅限个人使用，这一来源限制不会因上传改变。用户已要求将实际音乐加入公开仓库，原音频由Git LFS存储。安装后须核实真实音频已拉取，不能把索引或LFS指针当成已有音频。

## 按用户指定的方向选曲

| 题材目录 | 声音方向 | 用户参考曲目/检索词 |
|---|---|---|
| 01_悬疑揭秘八卦 | 低沉弦乐、心跳、时钟、警报、riser，突出悬念与转折 | Inspector Gadget Theme、The X-Files Theme、Halloween Theme；悬疑、紧张、揭秘、反转、暗黑 |
| 02_励志成功创业 | 史诗、宏大鼓点，配合推进和高潮 | Victory、Star Sky、The Mass、Empire of Angels、Strength of a Thousand Men、Hall of Fame、Believer、Rise、Legends Never Die |
| 03_情感家庭伤感 | 钢琴、大提琴、二胡、慢弦乐 | Kiss the Rain、River Flows in You、My Soul / 忧伤还是快乐、The Truth That You Leave、Merry Christmas Mr. Lawrence、Luv Letter、Flower Dance、A Little Story |
| 04_影视解说卡点 | 按剧情在悬疑、史诗、温情之间切换；片头卡点 | Cornfield Chase、Time、Dragon Rider、Fearless、Tokyo Drift、He's a Pirate、The Avengers Theme；片头 Phut Hon、Astronomia |
| 05_搞笑沙雕盘点 | 滑稽、古典改编、网络歌曲、短反应声 | 猪八戒背媳妇、甩葱歌、Tunak Tunak Tun、We Are Number One、Seinfeld Theme、Curb Your Enthusiasm；罐头笑声 |
| 06_国风历史文化 | 古筝、琵琶、笛子、大气国风 | 赤伶、牵丝戏、琵琶行、象王行、广寒宫、故宫的记忆 / Palace Memories、兰陵王入阵曲 |
| 07_知识科普商业带货 | 轻快电子、Lo-fi、科技感、卡点流行 | 本地风格补充；用户列出的外部来源是选曲渠道，不是默认下载或订阅指令 |
| 08_热榜万能 | 按内容情绪选择用户候选流行曲 | See Tình、爱如火、悬溺、精卫、向云端、乌梅子酱、Cupid、Letting Go、把回忆拼好给你、一路生花、孤勇者 |

第7类用户参考渠道：剪映音乐库、抖音热榜、B站热门、快手音乐、YouTube Audio Library、Epidemic Sound、Artlist、Bensound、Kevin MacLeod、爱给网、耳聆网。未经实际查询不称任何曲目当前热门，不自动登录、购买或补下载。

这些曲名是风格与选择参考，使用时以实际文件为准。Inspector Gadget / X-Files 等可能是翻奏或不同版本；Phut Hon 在当前库中是 2 Phut Hon (AbQayyum Bootleg)，Believer 是含 Lil Wayne 的版本，Curb Your Enthusiasm 对应 Frolic。保留实际版本名称。故宫的记忆与 Palace Memories 在来源报告中合并。未找到的指定曲或音效记录在 `assets/bgm-import-report.json`，不能声称库里齐全。

## 制作时自动使用

用户没指定无音乐时，按题材与当前镜头情绪，从存在且可解码的曲目里选适合的一首或少量曲目；先实际试听候选的入点、高潮、出点，尤其留意人声和重鼓是否干扰口播。音频缺失时先检查用户素材目录或用户本次提供的新文件；确实缺失则说明，不虚构音乐使用结果。

剪出适合本片长度的片段并记录入出点，开头进入速度与画面钩子配合，高潮对齐转折。需要循环时按乐句切点衔接并淡化接缝；结尾淡出，避免突然截断。已有原视频音乐时决定保留、替换或降低，避免两首无意叠加。

先将不同音量的音乐统一到可控制的起点，再将BGM置于口播下方。可从口播期间音乐低约15–22dB开始试听调整；无口播的短段可适当抬高。通过手工音量包络或 sidechain ducking 让口播出现时音乐下降，音效也不能盖住关键词。数字是调音起点，不是无须试听的固定验收值。

音乐与配音分轨处理。已认可的尖嗓快语速效果只作用于配音，BGM不跟随变调、变速；在处理后的最终口播长度上重新确定BGM与音效时间。交付前检查响度、峰值、淡入淡出、循环接缝及声画卡点。记录使用曲目ID、相对路径、实际版本、裁切点、增益/压低方法，并在制作说明中列出。

事件类关键原声段按 event-default-workflow.md 默认关闭添加的BGM，并暂停TTS；这优先于上述自动压低的常规建议。原素材自身已有的声音与添加的BGM分开记录，不把保留原素材音轨声称为已清除其内部音乐。音乐恢复避开原声尾句和必要停顿。

## 用户自行补充

将新音频放入 `assets/BGM/` 对应分类，保留原文件。运行 `scripts/index_bgm.py` 更新独立音乐索引，需要Python及FFmpeg/ffprobe。该脚本完整解码检查音频，不改写或删除源文件；不要用图片索引脚本处理音乐。原 `_raw`、`_tools`、下载配置和账号文件不属于音乐资产，不能随skill上传。公开安装缺音频时，先执行Git LFS拉取或导入音频再更新索引；别直接在空目录运行索引覆盖仍需参考的公共曲目清单。
