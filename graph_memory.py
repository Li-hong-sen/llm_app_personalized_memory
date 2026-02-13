
import os
import streamlit as st
from mem0 import Memory
from openai import OpenAI

# --- 修复 mem0 与 langchain_neo4j / Qwen 的兼容性 bug ---
# Bug 1: langchain_neo4j 新版 Neo4jGraph.__init__ 在 password 和 database 之间
#   新增了 token 参数，mem0 用位置参数传递导致 database 被当作 token -> AuthError
# Bug 2: Qwen 模型 tool call 返回的实体可能缺少 source/relationship/destination 字段
#   导致 _remove_spaces_from_entities 抛出 KeyError: 'source'
import logging
from mem0.memory.graph_memory import MemoryGraph, Neo4jGraph
from mem0.memory.utils import sanitize_relationship_for_cypher
from mem0.utils.factory import EmbedderFactory, LlmFactory

_original_init = MemoryGraph.__init__

def _patched_init(self, config):
    """修复 Neo4jGraph 位置参数 bug，改用关键字参数"""
    self.config = config
    self.graph = Neo4jGraph(
        url=self.config.graph_store.config.url,
        username=self.config.graph_store.config.username,
        password=self.config.graph_store.config.password,
        database=self.config.graph_store.config.database,
        refresh_schema=False,
        driver_config={"notifications_min_severity": "OFF"},
    )
    self.embedding_model = EmbedderFactory.create(
        self.config.embedder.provider, self.config.embedder.config, self.config.vector_store.config
    )
    self.node_label = ":`__Entity__`" if self.config.graph_store.config.base_label else ""
    if self.config.graph_store.config.base_label:
        try:
            self.graph.query(f"CREATE INDEX entity_single IF NOT EXISTS FOR (n {self.node_label}) ON (n.user_id)")
        except Exception:
            pass
        try:
            self.graph.query(f"CREATE INDEX entity_composite IF NOT EXISTS FOR (n {self.node_label}) ON (n.name, n.user_id)")
        except Exception:
            pass
    self.llm_provider = "openai"
    if self.config.llm and self.config.llm.provider:
        self.llm_provider = self.config.llm.provider
    if self.config.graph_store and self.config.graph_store.llm and self.config.graph_store.llm.provider:
        self.llm_provider = self.config.graph_store.llm.provider
    llm_config = None
    if self.config.graph_store and self.config.graph_store.llm and hasattr(self.config.graph_store.llm, "config"):
        llm_config = self.config.graph_store.llm.config
    elif hasattr(self.config.llm, "config"):
        llm_config = self.config.llm.config
    self.llm = LlmFactory.create(self.llm_provider, llm_config)
    self.user_id = None
    self.threshold = self.config.graph_store.threshold if hasattr(self.config.graph_store, 'threshold') else 0.7

def _patched_remove_spaces(self, entity_list):
    """修复 Qwen tool call 返回实体可能缺少字段的问题，跳过不完整的实体"""
    _logger = logging.getLogger(__name__)
    valid = []
    for item in entity_list:
        if not all(k in item for k in ("source", "relationship", "destination")):
            _logger.warning(f"跳过不完整的实体: {item}")
            continue
        item["source"] = item["source"].lower().replace(" ", "_")
        item["relationship"] = sanitize_relationship_for_cypher(item["relationship"].lower().replace(" ", "_"))
        item["destination"] = item["destination"].lower().replace(" ", "_")
        valid.append(item)
    return valid

MemoryGraph.__init__ = _patched_init
MemoryGraph._remove_spaces_from_entities = _patched_remove_spaces
# --- 修复结束 ---

st.title("LLM App with Memory 🧠")
st.caption("LLM App with personalized memory layer that remembers ever user's choice and interests")

# 阿里云 DashScope API Key
dashscope_api_key = st.text_input("Enter Aliyun DashScope API Key", value="sk-37b98fd30e1d44669bb1046aac45dc69", type="password")

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
        "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": "neo4j+s://7ebeea71.databases.neo4j.io",
            "username": "neo4j",
            "password": "jkHfTyOWwicagj1Dc18Vw_-pmJdZ2IdMKUXYFKYYuts",
            "database": "neo4j",
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
                relevant_memories = memory.search(query=prompt, user_id=user_id,    limit=3,rerank=True)
            st.success("记忆搜索完成")
            
            # Prepare context with relevant memories
            context = "Relevant past information:\n"
            if relevant_memories:
                # 向量存储记忆
                for mem in relevant_memories.get("results", []):
                    memory_text = mem.get('memory', '') or mem.get('text', '')
                    if memory_text:
                        context += f"- {memory_text}\n"
                # 图谱存储记忆 (关系三元组)
                for rel in relevant_memories.get("relations", []):
                    source = rel.get("source", "")
                    relationship = rel.get("relationship", "")
                    target = rel.get("target", rel.get("destination", ""))
                    if source and relationship and target:
                        context += f"- {source} {relationship} {target}\n"
                
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

            # Add conversation (user + AI) to memory
            with st.spinner('正在保存到记忆...'):
                messages_to_save = [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": answer},
                ]
                add_result = memory.add(messages_to_save, user_id=user_id)
            st.success("已保存到记忆")
            # 调试: 显示 add 返回结果
            with st.expander("调试: memory.add 返回值"):
                st.json(add_result)
            
        except Exception as e:
            st.error(f"出错了: {e}")
            import traceback
            st.code(traceback.format_exc())


    # Sidebar option to show memory
    st.sidebar.title("Memory Info")
    if st.button("View My Memory"):
            memories = memory.get_all(user_id=user_id)

            # 调试: 显示 get_all 原始返回
            with st.expander("调试: memory.get_all 返回值"):
                st.json(memories)

            has_data = False

            # 显示向量存储的记忆 (results)
            if memories.get("results"):
                st.write(f"**{user_id} 的文本记忆:**")
                for mem in memories["results"]:
                    memory_text = mem.get('memory', '') or mem.get('text', '')
                    if memory_text:
                        st.write(f"- {memory_text}")
                        has_data = True

            # 显示图谱存储的记忆 (relations)
            if memories.get("relations"):
                st.write(f"**{user_id} 的图谱记忆 (知识图谱):**")
                for rel in memories["relations"]:
                    source = rel.get("source", "?")
                    relationship = rel.get("relationship", "?")
                    target = rel.get("target", rel.get("destination", "?"))
                    st.write(f"- {source} --[{relationship}]--> {target}")
                    has_data = True

            if not has_data:
                st.info("No memory found for this user ID.")