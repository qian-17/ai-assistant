import streamlit as st
import os
import json
from datetime import datetime
from openai import OpenAI

#页面基础配置
st.set_page_config(
    page_title="AI智能助手平台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

#基于css页面样式
st.markdown("""
<style>
.stApp {
    background: #f8f9fa;
}
.stChatMessage {
    border-radius: 10px;
    padding: 10px 14px;
    margin: 5px 0;
}
</style>
""", unsafe_allow_html=True)

# 多模型配置
MODEL_LIST = {
    "DeepSeek 深度求索": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key": os.environ.get("DEEPSEEK_API_KEY", "")
    },
    "通义千问 Qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-turbo",
        "api_key": os.environ.get("QWEN_API_KEY", "")
    }
}

# 只显示配置了API Key的模型
VALID_MODELS = {k: v for k, v in MODEL_LIST.items() if v["api_key"]}

# 生成时间格式的会话ID
def get_time_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# 保存当前对话到JSON文件
def save_session():
    if not st.session_state.session_id:
        return

    session_data = {
        "session_id": st.session_state.session_id,
        "messages": st.session_state.messages
    }

    if not os.path.exists("sessions"):
        os.mkdir("sessions")

    with open(f"sessions/{st.session_state.session_id}.json", "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=4)

# 读取所有历史会话列表
def load_sessions():
    sessions = []
    if os.path.exists("sessions"):
        for f in os.listdir("sessions"):
            if f.endswith(".json"):
                sessions.append(f[:-5])
    return sorted(sessions, reverse=True)

# 加载某个会话的聊天记录
def load_session(session_id):
    try:
        with open(f"sessions/{session_id}.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        st.session_state.session_id = data["session_id"]
        st.session_state.messages = data["messages"]
    except Exception as e:
        st.error(f"加载失败：{str(e)}")

# 删除会话
def delete_session(session_id):
    try:
        path = f"sessions/{session_id}.json"
        if os.path.exists(path):
            os.remove(path)
        if session_id == st.session_state.session_id:
            st.session_state.session_id = get_time_str()
            st.session_state.messages = []
    except:
        st.error("删除失败")

#状态初始化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = get_time_str()
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "DeepSeek 深度求索"

# 主界面
st.title("🤖 AI智能助手平台")
st.caption(f"当前会话：{st.session_state.session_id}")

# 侧边栏
with st.sidebar:
    st.subheader("⚙️ 模型设置")
    model_name = st.selectbox("选择AI模型", list(VALID_MODELS.keys()), index=0)
    model_config = VALID_MODELS[model_name]

    # 新建对话
    if st.button("🆕 新建对话", use_container_width=True):
        save_session()
        st.session_state.session_id = get_time_str()
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("📁 历史会话")

    # 显示所有会话
    session_list = load_sessions()
    for sid in session_list:
        c1, c2 = st.columns([4, 1])
        with c1:
            btn_type = "primary" if sid == st.session_state.session_id else "secondary"
            if st.button(sid, key=f"l_{sid}", type=btn_type, use_container_width=True):
                load_session(sid)
                st.rerun()
        with c2:
            if st.button("🗑", key=f"d_{sid}", use_container_width=True):
                delete_session(sid)
                st.rerun()

# 系统提示词
system_prompt = """
你是一个专业、简洁、有用的AI助手。
回答准确、有条理、不废话，只提供有用信息。
"""

#展示历史聊天
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 发送后立刻保存，防止切换丢失
if prompt := st.chat_input("输入你的问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_session()
    st.rerun()

#AI交互
# 如果最后一条是用户消息，就自动生成回复（切回来也能继续）
if st.session_state.messages:
    last = st.session_state.messages[-1]
    if last["role"] == "user":
        with st.chat_message("assistant"):
            full_resp = ""
            placeholder = st.empty()

            try:
                client = OpenAI(
                    api_key=model_config["api_key"],
                    base_url=model_config["base_url"]
                )
                response = client.chat.completions.create(
                    model=model_config["model"],
                    messages=[{"role": "system", "content": system_prompt}, *st.session_state.messages],
                    stream=True
                )
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_resp += chunk.choices[0].delta.content
                        placeholder.markdown(full_resp)
            except Exception as e:
                full_resp = f"⚠️ 调用失败：{str(e)}"
                placeholder.error(full_resp)

        # 保存AI回复
        st.session_state.messages.append({"role": "assistant", "content": full_resp})
        save_session()
        st.rerun()