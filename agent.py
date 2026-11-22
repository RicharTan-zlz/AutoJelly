"""
Jellyfin Agent sidecar.

- FastAPI 暴露 /chat 和 /health。
- 用 DeepSeek（OpenAI 兼容接口）作为 LLM。
- 通过 function calling 把 Jellyfin 的 REST 能力暴露给模型。

启动：uvicorn agent:app --host 0.0.0.0 --port 8787
"""
import json

import httpx
import openai
from fastapi import FastAPI
from openai import AsyncOpenAI
from pydantic import BaseModel

app = FastAPI(title="Jellyfin Agent Sidecar")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_media",
            "description": "按关键词搜索 Jellyfin 媒体库中的电影/剧集",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "搜索关键词"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_sessions",
            "description": "列出当前所有播放会话（哪些设备正在播放什么）",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_item",
            "description": "在指定会话上播放某个媒体项（需要 itemId）",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "description": "媒体项 Id"},
                    "session_id": {"type": "string", "description": "会话 Id，缺省则用第一个活动会话"},
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_pause",
            "description": "切换播放/暂停",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "会话 Id，缺省则用第一个活动会话"},
                },
            },
        },
    },
]


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    jellyfin_url: str
    jellyfin_api_key: str = ""


def _headers(api_key: str) -> dict:
    if not api_key:
        return {}
    return {
        "Authorization": 'MediaBrowser Token="%s"' % api_key,
        "X-Emby-Token": api_key,
    }


class JellyfinError(Exception):
    """Jellyfin 请求失败（携带 HTTP 状态码与可读原因）。"""


def _read_jf_error(resp) -> str:
    """从 Jellyfin 的错误响应里尽量提取一句可读的原因。"""
    try:
        data = resp.json()
    except Exception:
        text = (resp.text or "").strip()
        return text[:500] or "无详情"
    if isinstance(data, dict):
        for k in ("Message", "message", "detail", "error", "Error", "title", "Title"):
            v = data.get(k)
            if v:
                return str(v)
        return json.dumps(data, ensure_ascii=False)[:500]
    return str(data)[:500]


async def _jf_get(jf: str, key: str, path: str, params: dict | None = None):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{jf.rstrip('/')}/{path.lstrip('/')}", params=params, headers=_headers(key))
        if r.is_error:
            raise JellyfinError(f"HTTP {r.status_code}：{_read_jf_error(r)}")
        return r.json()


async def _jf_post(jf: str, key: str, path: str, json: dict | None = None, params: dict | None = None):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{jf.rstrip('/')}/{path.lstrip('/')}", json=json, params=params, headers=_headers(key))
        if r.is_error:
            raise JellyfinError(f"HTTP {r.status_code}：{_read_jf_error(r)}")
        return r


async def _first_session(jf: str, key: str) -> str | None:
    try:
        sessions = await _jf_get(jf, key, "Sessions")
    except Exception:
        return None
    for s in sessions:
        if s.get("NowPlayingItem"):
            return s.get("Id")
    return sessions[0].get("Id") if sessions else None


async def call_tool(name: str, args: dict, req: ChatRequest):
    jf, key = req.jellyfin_url, req.jellyfin_api_key

    try:
        return await _call_tool(name, args, jf, key)
    except JellyfinError as e:
        return {"error": "Jellyfin 请求失败（%s）。请确认 Jellyfin 正在运行、地址正确，且没有被代理/VPN 拦截。" % e}
    except httpx.HTTPError as e:
        return {"error": "无法连接 Jellyfin（%s）。请确认 Jellyfin 服务已启动。" % e}
    except Exception as e:
        return {"error": "工具执行出错：%s" % e}


async def _call_tool(name: str, args: dict, jf: str, key: str):
    if name == "search_media":
        data = await _jf_get(
            jf, key, "Items",
            {"SearchTerm": args.get("query", ""), "Recursive": "true",
             "IncludeItemTypes": "Movie,Series", "Limit": 10},
        )
        return [
            {"Id": i.get("Id"), "Name": i.get("Name"),
             "Type": i.get("Type"), "Year": i.get("ProductionYear")}
            for i in data.get("Items", [])
        ]

    if name == "list_sessions":
        sessions = await _jf_get(jf, key, "Sessions")
        return [
            {"Id": s.get("Id"), "Client": s.get("Client"),
             "NowPlaying": (s.get("NowPlayingItem") or {}).get("Name")}
            for s in sessions
        ]

    if name == "play_item":
        sid = args.get("session_id") or await _first_session(jf, key)
        if not sid:
            return {"error": "没有活动会话"}
        await _jf_post(jf, key, f"Sessions/{sid}/Playing",
                        params={"playCommand": "PlayNow", "itemIds": args["item_id"]})
        return {"ok": True, "session_id": sid}

    if name == "play_pause":
        sid = args.get("session_id") or await _first_session(jf, key)
        if not sid:
            return {"error": "没有活动会话"}
        await _jf_post(jf, key, f"Sessions/{sid}/Playing/PlayPause")
        return {"ok": True, "session_id": sid}

    return {"error": f"未知工具 {name}"}


@app.get("/health")
async def health():
    return {"ok": True}


async def _run_agent(req: ChatRequest):
    client = AsyncOpenAI(api_key=req.deepseek_api_key, base_url=req.deepseek_base_url)
    messages = [*req.history, {"role": "user", "content": req.message}]

    for _ in range(6):
        resp = await client.chat.completions.create(
            model=req.deepseek_model,
            messages=messages,
            tools=TOOLS,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return {"reply": msg.content or ""}

        assistant_msg = {"role": "assistant", "content": msg.content}
        assistant_msg["tool_calls"] = [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]
        messages.append(assistant_msg)

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = await call_tool(tc.function.name, args, req)
            messages.append(
                {"role": "tool", "tool_call_id": tc.id,
                 "content": json.dumps(result, ensure_ascii=False)}
            )

    return {"reply": "已达到最大工具调用轮数。"}


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.deepseek_api_key:
        return {"reply": "请先在配置页填写 DeepSeek API Key。"}

    try:
        return await _run_agent(req)
    except openai.AuthenticationError:
        return {"reply": "DeepSeek API Key 无效或已过期，请到配置页检查。"}
    except openai.RateLimitError:
        return {"reply": "DeepSeek 请求太频繁或账户余额不足，请稍后再试。"}
    except openai.APIConnectionError:
        return {"reply": "无法连接到 DeepSeek，请检查网络或 Base URL 是否正确。"}
    except openai.APIStatusError as e:
        return {"reply": "DeepSeek 返回错误（状态码 %d），请检查账户状态。" % e.status_code}
    except Exception as e:
        return {"reply": "出错了：%s" % e}


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("JFAGENT_PORT", "8787"))
    uvicorn.run(app, host="0.0.0.0", port=port)
