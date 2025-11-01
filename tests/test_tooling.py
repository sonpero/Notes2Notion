import pytest
from unittest.mock import patch, MagicMock
import asyncio
from Notes2Notion.tooling import create_notion_connector


@pytest.mark.asyncio
async def test_create_notion_connector():
    mock_llm = MagicMock()
    mock_client = MagicMock()
    mock_agent = MagicMock()

    with patch("Notes2Notion.tooling.ChatOpenAI", return_value=mock_llm) as mock_chat, \
         patch("Notes2Notion.tooling.MCPClient.from_config_file", return_value=mock_client) as mock_client_from_file, \
         patch("Notes2Notion.tooling.MCPAgent", return_value=mock_agent) as mock_agent_cls:

        client, agent = await create_notion_connector()

        mock_chat.assert_called_once_with(model="gpt-4.1", temperature=0)
        mock_client_from_file.assert_called_once_with("./mcp_config.json")
        mock_agent_cls.assert_called_once_with(llm=mock_llm, client=mock_client, max_steps=30)

        assert client is mock_client
        assert agent is mock_agent
