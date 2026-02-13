import os
import streamlit as st
from mem0 import Memory
from openai import OpenAI

st.title("LLM App with Memory 🧠")
st.caption("LLM App with personalized memory layer that remembers ever user's choice and interests")

# 阿里云 DashScope API Key
dashscope_api_key = st.text_input("Enter Aliyun DashScope API Key", value="", type="password")

@st.cache_resource
def init_client(api_key):
    """缓存 OpenAI 客户端"""
    return OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

@st.cache_resource
def init_memory(api_key):
    """缓存 Memory 对象"""
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "llm_app_memory_ali",
                "host": "localhost",
                "port": 6333,
                "embedding_model_dims": 1024, # 明确告诉向量数据库维度
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "qwen-plus",
                "api_key": api_key,
                "openai_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-v3",
                "api_key": api_key,
                "openai_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "embedding_dims": 1024
            }
        }
    }
    return Memory.from_config(config)

if dashscope_api_key:
    try:
        with st.spinner("正在初始化..."):
            client = init_client(dashscope_api_key)
            memory = init_memory(dashscope_api_key)
        st.success("初始化完成!")
    except Exception as e:
        st.error(f"初始化失败: {e}")
        st.stop()

    user_id = st.text_input("Enter your Username")

    prompt = st.text_input("Ask Qwen")

    if st.button('Chat with LLM'):
        if not user_id:
            st.warning("请先输入用户名")
            st.stop()
        if not prompt:
            st.warning("请输入问题")
            st.stop()
            
        try:
            with st.spinner('正在搜索记忆...'):
                relevant_memories = memory.search(query=prompt, user_id=user_id)
            st.success("记忆搜索完成")
            
            # Prepare context with relevant memories
            context = "Relevant past information:\n"
            if relevant_memories:
                for mem in relevant_memories.get("results",[]):
                    # 新版 mem0 使用 'memory' 字段
                    print(f'mem:{mem}')
                    memory_text = mem.get('memory', '') or mem.get('text', '')
                    if memory_text:
                        context += f"- {memory_text}\n"
                
            # Prepare the full prompt
            full_prompt = f"{context}\nHuman: {prompt}\nAI:"

            with st.spinner('正在调用 Qwen 模型...'):
                # Get response from Qwen
                response = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant with access to past conversations."},
                        {"role": "user", "content": full_prompt}
                    ]
                )
            
            answer = response.choices[0].message.content
            st.write("Answer: ", answer)

            # Add AI response to memory
            with st.spinner('正在保存到记忆...'):
                memory.add(answer, user_id=user_id)
            st.success("已保存到记忆")
            
        except Exception as e:
            st.error(f"出错了: {e}")


    # Sidebar option to show memory
    st.sidebar.title("Memory Info")
    if st.button("View My Memory"):
            memories = memory.get_all(user_id=user_id)
            if memories and "results" in memories:
                st.write(f"Memory history for **{user_id}**:")
                for mem in memories["results"]:
                    if "memory" in mem:
                        st.write(f"- {mem['memory']}")
            else:
                st.sidebar.info("No learning history found for this user ID.")
