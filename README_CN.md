## 🧠 带记忆功能的LLM应用
这是一个基于Streamlit的AI聊天机器人应用，使用OpenAI的GPT-4o模型并具备持久化记忆功能。它允许用户与AI进行对话，同时在多次交互中保持上下文。

### 功能特性

- 使用OpenAI的GPT-4o模型生成响应
- 使用Mem0和Qdrant向量存储实现持久化记忆
- 允许用户查看他们的对话历史
- 提供友好的Streamlit用户界面


### 如何开始？

1. 克隆GitHub仓库
```bash
git clone https://github.com/Shubhamsaboo/awesome-llm-apps.git
cd awesome-llm-apps/llm_apps_with_memory_tutorials/llm_app_personalized_memory
```

2. 安装所需的依赖项：

```bash
pip install -r requirements.txt
```

3. 确保Qdrant正在运行：
应用程序期望Qdrant在localhost:6333上运行。如果您的设置不同，请在代码中调整配置。

```bash
docker pull qdrant/qdrant

docker run -p 6333:6333 -p 6334:6334 \ -v $(pwd)/qdrant_storage:/qdrant/storage:z \ qdrant/qdrant
docker run -p 6333:6333 -p 6334:6334 -v ${PWD}/qdrant_storage:/qdrant/storage qdrant/qdrant
docker run -d -p 6333:6333 -p 6334:6334 -v ${PWD}/qdrant_storage:/qdrant/storage qdrant/qdrant
```

4. 运行Streamlit应用
```bash
streamlit run llm_app_memory.py
```
