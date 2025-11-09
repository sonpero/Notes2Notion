import base64
import json
import os

from openai import OpenAI
from langchain_openai import ChatOpenAI

from mcp_use import MCPAgent, MCPClient
from dotenv import load_dotenv

from . import utils
from . import settings

load_dotenv()


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

                prompt_text = ("Extract all text from the provided image."
                               " The text is handwritten and may contain "
                               "abbreviations or imperfect handwriting."
                               "Accurately transcribe what is written."
                               "Expand common abbreviations if you are confident "
                               "about their meaning."
                               "Return only the extracted text, no commentary.")

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt_text
                                },
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


async def create_notion_connector():
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        raise EnvironmentError("NOTION_TOKEN environment variable not set.")

    llm = ChatOpenAI(model=settings.L, temperature=0)

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28"
    }

    config = {
        "mcpServers": {
            "docker_server": {
                "command": "docker",
                "args": [
                    "run", "--rm", "-i",
                    "-e", f"OPENAPI_MCP_HEADERS={json.dumps(headers)}",
                    "mcp/notion"
                ]
            }
        }
    }

    client = MCPClient.from_dict(config)
    agent = MCPAgent(llm=llm, client=client, max_steps=30)
    return client, agent
