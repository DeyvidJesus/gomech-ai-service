from langchain_core.messages import HumanMessage

def to_human_message(content: str) -> HumanMessage:
    return HumanMessage(content=content)
