# 同一个完整 VidMuse thread

需要已登录的 VidMuse CLI、可用图像/视频编辑能力。Python3和FFmpeg用于媒体核对和确定性合成。若安装了 `vidmuse` Skill，先读取其当前说明；否则先 `vidmuse --help` 与子命令 `--help` 确认接口。本文件的例子是当前已验证命令，不是永久模型契约。连接流程必须遵守SKILL中的确认环节：收齐素材后先解释VidMuse提供生成/剪辑能力、会上传本次人物与穿搭素材并使用账号额度，询问是否连接。没有明确同意之前，不提供催促执行的安装指令、不登录、不上传、不创建thread。已有本次连接授权无需重复询问。

用户确认连接后，才检查是否已安装。缺失时展示纯文本安装命令，让用户自行复制执行；只有明确授权Agent代为执行该命令时才能代装：

```bash
curl -fsSL https://vidmuse.sandcdn.com/cli/install.sh | bash
```

这只是安装接口，不是密钥或已完成连接。已安装就跳过；需要登录时由用户执行 `vidmuse login`，或在其明确同意后由Agent启动登录，用户完成网页授权。素材和生成操作必须等到连接授权及登录均就绪。首次尚未连接时，三视图在连接后生成，不能提前声称已生成。

## 1. 创建工程并持久化

先 `vidmuse profile get --output json`；在已获得连接确认的前提下，鉴权失败时提示用户运行 `vidmuse login` 并完成授权；Agent代为启动登录需要明确同意。再检查登录状态，不能假装生成。

每个新用户/新项目分配自己的项目目录，保存 `project.json`，其中包含 `thread_id`、阶段、输入文件与哈希、身份/穿搭/场景/开头资产、输出版本。未创建成功前 thread_id 保持空；不复制作者历史ID或个人资料。

```sh
vidmuse thread create --canvas --aspect-ratio 9:16 --resolution 1080p --output json
```

解析成功返回的真实 `id`，立即写入 project.json，再发送第一条消息。分开创建与上传，避免创建大请求超时后反复开工程。若创建响应不明确，先 `vidmuse thread list --limit 20 --output json` 核实是否已创建，不盲目重试。

**仅创建空画布不是完整制作。** 从身份三视图开始，把生成、素材、修改、合成、校验请求实际发送到此 thread，完成后登记结果。可以在本地只读分析或下载验收，不能把整套制作搬到单独模型调用或另一个thread。

## 2. 按阶段上传与指令

```sh
vidmuse message send --thread REAL_ID --text '本阶段具体制作指令' --file /absolute/input.png --output json
```

`--file`可重复。local path会上传；远程路径不能冒充本地路径。用Python `subprocess.run([参数...])` 传长指令、特殊字符和文件名，避免shell插值。上传后的远端文件名可能改变，按真实上传映射和图片内容核对，不能假定附件顺序等于返回列表顺序。

阶段A：只传新用户原照片和三视图版式要求，实际生成身份三视图，展示后回到用户询问穿搭。不得提前生成12场景和视频。

阶段B：继续同一REAL_ID，传穿搭图（别人照片仅提取衣服）、原人物照片和已有身份参考，实际生成穿搭三视图并展示。再按SKILL规定询问是否制作。

阶段C：收到制作确认后，同一REAL_ID上传：12张场景原图、新用户原照/身份/穿搭参考、`opening-scene.png`、`opening-full-v5.mp4`、`reference-final-v5.mp4`、`luke-march.m4a`、timeline.json、必要的合成脚本。发送完整制作要求：

> 请在本thread完成整个项目。人物以本次用户原照为唯一身份，按本次穿搭参考。逐一以12张原图局部替换人物，保留原背景像素与构图，维持姿态神情；开头也锁定原背景，先生成并核验新人物已戴好墨镜的单画面首帧，再用该帧生成视频：第0帧镜片就覆盖双眼，手接触已有镜框扶正，冷淡直视镜头，再接踩鼓点的大步模特步；墨镜不能凭空出现、消失或变形。抬镜露眼仅为可选连续动作，不能裸眼开场。三视图不能作为单画面视频首帧。先验收人物、穿搭、背景，再生成开头并用固定timeline合成。音乐只用上传原m4a，0秒起，不改速。输出1080×1920、60fps、630帧，开头154帧，12张图及回切按timeline.json，硬切、同图模糊边缘。不要只给方案或单模型产物；持续做到可播放最终MP4、画布登记、可复现工程和下载交付。

模型在thread里按当前能力选：优先局部图像编辑与背景保留的视频人物编辑/前景合成。普通参考图生视频不能保证背景不改写，必须对照检查并修复。模型参数查询 `vidmuse model list --image/--video --output json`，不要硬编码一次会话的任务ID、付费状态或过期模型参数。

## 3. 追踪和修正

```sh
vidmuse thread status REAL_ID --output json
vidmuse message list --thread REAL_ID --last 5 --output json
vidmuse asset list --thread REAL_ID --output json
```

生成任务只返回taskId或thread状态running，不是完成。以真实消息和结果为依据，每30—60秒有界查询，适时简短告知用户。查询超时继续查原任务，不重复付费提交。waiting也不一定是成功：读取最新助手消息判断是否需要用户输入、是否仅完成分析或渲染。只有实际产物满足要求才交付。

需要修正时继续 `message send --thread REAL_ID`，说明只修改哪个镜头，其他已验收素材、音乐和切点保留。等待现有运行结束或明确状态，避免同时发多个互相覆盖的完整制作指令。失败须分类（鉴权/参数/素材访问/服务错误/内容拒绝），不能把一切错误都解释成需要重新登录。

## 4. 同工程合成

将 `compose.py` 和 `timeline.json` 上传到thread，要求VidMuse在其工作目录生成 `resolved-media.json`：

```json
{
  "thread_id": "本次真实ID",
  "opening": "/该thread/已验收新人物视频.mp4",
  "opening_start": 0,
  "audio": "/该thread/上传原音乐.m4a",
  "scenes": {"01": "/该thread/新人物场景01.png", "02": "/该thread/新人物场景02.png"}
}
```

scenes必须包含01至12全部键。`opening_start`选取原速且动作完整的有效窗口，不够长就重新生成动作，不盲目加速。

在**该thread**运行：

```sh
python compose.py --timeline timeline.json --media resolved-media.json --out exports/final.mp4
```

脚本保留分段、全局帧表与映射记录，供局部修改与复现。不可把上传的原女主参考图填入production映射冒充新用户生成结果。

## 5. 实际交付

要求将最终成片登记为画布video节点（done），时间线和各素材也保存为工程资产；不要只有文字表格而丢掉可复现脚本/映射。旧版本保留。

`asset list`和`latestResultVideoUrl`可能没有手工合成文件；这不证明文件不存在，也不能用来宣称已有下载链接。读取画布实际视频资产；通过VidMuse前端的播放/下载功能交付。项目真实路由格式可由前端确认：`https://vidmuse.ai/zh-CN/thread/REAL_ID`。若只能提供工程入口，明确指出具体视频节点，不编造本地文件或公共CDN链接。

完成后保存本次project.json（不打包进公开Skill），并将结果提供用户。后续调整继续同一thread。
