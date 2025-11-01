import base64

from openai import OpenAI
from langchain_openai import ChatOpenAI

from mcp_use import MCPAgent, MCPClient

from . import utils
from . import settings


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
    llm = ChatOpenAI(model=settings.M, temperature=0)
    config = {
                  "mcpServers": {
                    "notionMCP": {
                      "command": "npx",
                      "args": [
                        "-y",
                        "mcp-remote",
                        "https://mcp.notion.com/mcp",
                        "--debug"
                      ]
                    }
                  }
                }
    client = MCPClient.from_dict(config)
    agent = MCPAgent(llm=llm, client=client, max_steps=30)
    return client, agent
