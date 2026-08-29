import pandas as pd
import json
import os
import time
from pathlib import Path
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm  # 引入专业的进度条库

# ================= 1. 初始化配置 =================
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = EXPERIMENT_ROOT / "data" / "raw" / "vehicle-review-data.csv"
OUTPUT_FILE = EXPERIMENT_ROOT / "data" / "interim" / "appearance-features.jsonl"
MAX_WORKERS = 10  # 【新增】并发线程数，可以根据 API 的并发限制调整，10 通常是个安全的提速点

# 初始化客户端
if not API_KEY:
    raise SystemExit("请先设置环境变量 DEEPSEEK_API_KEY。")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# ================= 2. 定义系统提示词 =================
# （保持你原来的提示词不变）
system_prompt = """您是一名智能汽车用户体验分析领域的专家。
您的任务是：从每一条用户评论文本中，提取关于汽车外观特征的原始表述，以及与之相关的用户感知内容。

具体约束要求如下：
请根据以下定义提取关键词：
外观特征（Appearance Feature） 是指汽车的外部造型、车身线条、颜色、灯具及材质等视觉设计元素，该特征能够直接激发或影响用户的审美和视觉体验。
用户感知（User Perception） 指用户体验中最直接、最核心的感受维度。
提取的词语必须是文本中的原始表述，不得增减、修改字数或进行归一化处理（例如：原始文本为“非常的流畅”，不得修改为“非常流畅”）。

请严格遵循以下 JSON 输出格式规范：
[
  {
   "appearance_feature": "外观1",
   "user_perceptions": ["感知1", "感知2"]
  }
]

以下是一些具有代表性的示例：

input：车身侧面的线条非常的流畅，前脸的格栅设计很有未来感，大灯造型犀利，整体看起来非常运动，在路上回头率很高。
output：[
    {
     "appearance_feature": "车身侧线",
     "user_perceptions": ["非常的流畅"]
   },
    {
     "appearance_feature": "前脸格栅",
     "user_perceptions": ["有未来感"]
   },
    {
     "appearance_feature": "大灯造型",
     "user_perceptions": ["犀利"]
    },
    {
     "appearance_feature": "整体外观",
     "user_perceptions": ["非常运动", "回头率很高"]
    }
  ]

input：那个星空灰的车漆绝了，在阳光下闪闪发光，质感拉满。
output：[
    {
     "appearance_feature": "星空灰漆",
     "user_perceptions": ["绝了", "闪闪发光", "质感拉满"]
    }
  ]

input: es6让我一见钟情的是他的外观，在同级别的suv中，他显的更高更宽更魁梧，轮廓分明，很有质感! Nomi也是蔚来的一个亮点，在第一次试驾的时候不仅我老婆，连我儿子都对nomi产生了好感。
output： [
    {
     "appearance_feature": "整体外观",
     "user_perceptions": ["一见钟情", "很有质感"]
    },
   {
     "appearance_feature": "车身体态",
     "user_perceptions": ["更高更宽更魁梧"]
    },
   {
     "appearance_feature": "轮廓",
     "user_perceptions": ["分明"]
    }
  ]"""

# ================= 3. 读取与清洗数据 =================
print("正在读取数据...")
df = pd.read_csv(INPUT_FILE, encoding='gbk')

comments = df['外观评分评价'].dropna()
comments = comments[~comments.str.contains('暂无|没有|无|不知道', na=False)]
comments_to_process = comments.head(2000).tolist()
print(f"准备处理 {len(comments_to_process)} 条有效评论...")

# ================= 4. 定义请求函数 =================
def extract_features(text, max_retries=3):
    # 我们去掉了外层的强行 sleep，利用重试机制中的 sleep 来应对可能的并发限流 (HTTP 429)
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"input: {text}\noutput:"}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            # 如果触发并发限制或网络波动，等待后重试
            time.sleep(2 * (attempt + 1)) # 采用退避策略，第一次等2秒，第二次等4秒

    return None

# ================= 5. 定义单条处理包装函数 =================
def process_single_item(item):
    i, text = item
    result_text = extract_features(text)
    if result_text:
        clean_result = result_text.strip().removeprefix('```json').removesuffix('```').strip()
        return {
            "id": i + 1,
            "original_text": text,
            "extracted_features": clean_result
        }
    return None

# ================= 6. 多线程并发处理并保存 =================
print(f"启动多线程处理，并发数：{MAX_WORKERS}")

# 准备带有索引的数据，方便追踪 ID
indexed_comments = list(enumerate(comments_to_process))

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_FILE.open('w', encoding='utf-8') as f:
    # 使用 ThreadPoolExecutor 管理并发
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务到线程池
        future_to_item = {executor.submit(process_single_item, item): item for item in indexed_comments}

        # 使用 tqdm 包装 as_completed，实现带进度条的异步结果获取
        for future in tqdm(as_completed(future_to_item), total=len(indexed_comments), desc="处理进度"):
            record = future.result()

            # 只要有有效结果，就立即写入文件（主线程负责写入，避免文件锁冲突）
            if record:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                f.flush()

print(f"\n处理完成！所有结果已安全保存至 {OUTPUT_FILE}")
