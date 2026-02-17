import base64
import json
import logging
from typing import Optional

from openai import OpenAI
from notion_client import AsyncClient
from notion_client.errors import APIResponseError

from src.Notes2Notion import utils

logger = logging.getLogger(__name__)

NOTION_TOOLS = [
    {
        "name": "API-post-page",
        "description": (
            "Create a new Notion page. "
            "Use 'parent': {'page_id': '<id>'} to set the parent page. "
            "Use 'properties': {'title': {'title': [{'text': {'content': '<title>'}}]}} to set the title."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent": {
                    "type": "object",
                    "description": "Parent object, e.g. {'page_id': 'xxx'}",
                    "properties": {
                        "page_id": {"type": "string"}
                    },
                    "required": ["page_id"]
                },
                "properties": {
                    "type": "object",
                    "description": "Page properties. Must include 'title'."
                },
                "children": {
                    "type": "array",
                    "description": "Optional initial blocks",
                    "items": {"type": "object"}
                }
            },
            "required": ["parent", "properties"]
        }
    },
    {
        "name": "API-patch-block-children",
        "description": (
            "Append blocks to an existing Notion page or block. "
            "Pass 'block_id' (the page ID) and 'children' (list of block objects). "
            "Supported block types: paragraph, heading_1, heading_2, heading_3, "
            "bulleted_list_item, numbered_list_item, quote, callout, code, toggle, to_do."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "block_id": {
                    "type": "string",
                    "description": "ID of the page or block to append children to"
                },
                "children": {
                    "type": "array",
                    "description": "List of block objects to append",
                    "items": {"type": "object"}
                }
            },
            "required": ["block_id", "children"]
        }
    }
]


class _Content:
    def __init__(self, text: str):
        self.text = text


class _CallToolResult:
    def __init__(self, text: str):
        self.content = [_Content(text)]


class _ListToolsResult:
    def __init__(self):
        self.tools = [_ToolDef(t) for t in NOTION_TOOLS]


class _ToolDef:
    def __init__(self, tool_dict: dict):
        self.name = tool_dict["name"]
        self.description = tool_dict["description"]
        self.inputSchema = tool_dict["inputSchema"]


class NotionSession:
    """Calls the Notion API directly, mimicking the MCP ClientSession interface."""

    def __init__(self, notion_token: str):
        self.client = AsyncClient(auth=notion_token)

    async def list_tools(self) -> _ListToolsResult:
        return _ListToolsResult()

    async def call_tool(self, name: str, args: dict) -> _CallToolResult:
        try:
            if name == "API-post-page":
                result = await self.client.pages.create(**args)
            elif name == "API-patch-block-children":
                result = await self.client.blocks.children.append(
                    block_id=args["block_id"],
                    children=args["children"]
                )
            else:
                return _CallToolResult(json.dumps({"error": f"Unknown tool: {name}"}))
            return _CallToolResult(json.dumps(result))
        except APIResponseError as e:
            return _CallToolResult(json.dumps({"error": str(e), "code": e.code}))
        except Exception as e:
            return _CallToolResult(json.dumps({"error": str(e)}))


class NotionDirectConnector:
    """Replaces McpNotionConnector — no MCP server needed."""

    def __init__(self):
        self.session: Optional[NotionSession] = None

    async def connect_to_server(self, user_notion_token: str):
        if not user_notion_token:
            raise EnvironmentError("No Notion token provided.")
        self.session = NotionSession(user_notion_token)

    async def cleanup(self):
        pass


# Kept for backward compatibility with any direct import
McpNotionConnector = NotionDirectConnector


class ImageTextExtractor:
    def __init__(self, repo_path: str):
        self.client = OpenAI()
        self.repo_path = repo_path
        self.text = ""

    def extract_text(self) -> str:
        images_path = utils.get_file_paths(self.repo_path)
        for image_path in images_path:
            if ".gitkeep" not in image_path:
                with open(image_path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode("utf-8")

                prompt_text = (
                    "Extract all text from the provided image."
                    " The text is handwritten and may contain "
                    "abbreviations or imperfect handwriting."
                    "Accurately transcribe what is written."
                    "Expand common abbreviations if you are confident "
                    "about their meaning."
                    "Return only the extracted text, no commentary."
                )

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}"
                                    },
                                },
                            ],
                        }
                    ],
                )
                self.text = self.text + response.choices[0].message.content
        return self.text
