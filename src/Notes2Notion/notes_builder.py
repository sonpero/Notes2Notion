import json
import os

from typing import TypedDict
from pathlib import Path

from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langchain_core.messages import (HumanMessage, AIMessage, FunctionMessage,
                                     SystemMessage)
from dotenv import load_dotenv

from .tooling import McpNotionConnector, ImageTextExtractor
from .settings import S, M

load_dotenv()


class DraftEnhancer:
    def __init__(self):
        self.llm_for_notes_plan = ChatOpenAI(model=S,
                                             temperature=0)

        self.llm_for_notes_content = ChatOpenAI(model=M,
                                                temperature=0)

        self.llm_for_check = ChatOpenAI(model=S,
                                        temperature=0)

        self.state = None

    class State(TypedDict):
        user_input: str
        agent_response: str

    async def structure_content(self, state: State, ) -> State:
        """Convert raw draft into a structured outline."""
        self.state = state
        draft = state["user_input"]
        messages = [
            SystemMessage(content="Organize this draft into sections with headings. "
                                  "Preserve numbered titles like '1. Introduction'."
                                  "Preserve any schemas."
                                  "Use only the language of the draft. Do "
                                  "not add extra content."),
            HumanMessage(content=draft)
        ]
        response = await self.llm_for_notes_plan.ainvoke(messages)
        print("response 1 : ", response.content)
        state["agent_response"] = response.content
        return state

    async def enhance_clarity(self, state: State) -> State:
        """Explain jargon, add examples, and improve readability."""
        state = self.state
        structured_draft = state["agent_response"]
        messages = [
            SystemMessage(content="Improve this draft : ensure it is clear and easy to understand."
                                  "Keep sections as provided."
                                  "Preserve any schemas."
                                  "Ensure the facts are correct."),
            HumanMessage(content=structured_draft)
        ]
        response = await self.llm_for_notes_content.ainvoke(messages)
        print("response 2 : ", response.content)
        state["agent_response"] = response.content
        return state

    async def check_facts(self, state: State):
        content = state["agent_response"]
        messages = [
            SystemMessage(content="Check the facts in this draft : ensure "
                                  "there is no false information. If there "
                                  "is : answer only the word 'ko' in lowercase."
                                  " if theres is not :"
                                  "answer only the word 'ok' in lowercase."),
            HumanMessage(content=content)
        ]
        response = await self.llm_for_check.ainvoke(messages)
        print("response 3 : ", response.content)
        if response.content == "ok":
            return "ok"
        else:
            print("response 3 : ", response.content)
            return "ko"

    async def out(self, state: State):
        return state

    async def create_notes_workflow(self):
        workflow = StateGraph(self.State)

        # Add nodes
        workflow.add_node("structure", self.structure_content)
        workflow.add_node("enhance", self.enhance_clarity)
        workflow.add_node("out", self.out)

        workflow.add_edge("structure", "enhance")
        workflow.add_conditional_edges(
            "enhance", self.check_facts,
            {
                "ko": "enhance",
                "ok": "out"
            },
        )

        # Set entry/exit points
        workflow.set_entry_point("structure")
        # workflow.set_finish_point("out")

        return workflow.compile()


class NotesCreator:
    def __init__(self,
                 notion_connector: McpNotionConnector,
                 draft_enhancer: DraftEnhancer,
                 image_text_extractor: ImageTextExtractor):

        self.llm_for_notion_mcp = ChatOpenAI(model=M,
                                             temperature=0)

        self.notion_connector = notion_connector
        self.draft_enhancer = draft_enhancer
        self.image_text_extractor = image_text_extractor
        self.llm_with_functions = None

    async def notes_creation(self):
        messages = await self.prepare_content()
        await self.write_in_notion(messages)

    async def prepare_content(self):
        await self.connect_notion_to_llm()

        query = self.get_primary_notes()

        workflow = await self.draft_enhancer.create_notes_workflow()
        workflow_result = await workflow.ainvoke({"user_input": query})

        # Extract the enhanced draft from workflow result
        enhanced_draft = workflow_result.get("agent_response", str(workflow_result))

        # Prepare initial message
        title = self.image_text_extractor.repo_path.split("/")[-1]

        # Use absolute path relative to this file's location
        current_dir = Path(__file__).parent
        filename = current_dir / "base_prompt.txt"
        notion_page_id = os.getenv("NOTION_PAGE_ID")
        base_prompt = Path(filename).read_text()
        filled_prompt = base_prompt.format(
            title=title,
            notion_page_id=notion_page_id,
            draft=enhanced_draft
            )
        print(f"\n📝 Prompt sent to LLM for Notion upload:")
        print(f"Title: {title}")
        print(f"Parent Page ID: {notion_page_id}")
        print(f"Draft preview (first 200 chars): {enhanced_draft[:200]}...")
        return [HumanMessage(content=filled_prompt)]

    async def write_in_notion(self, messages):
        final_text = []
        # Prevent infinite loops
        max_iterations = 10
        iteration = 0
        consecutive_errors = 0
        # Stop if we get 5 errors in a row
        max_consecutive_errors = 5

        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Iteration {iteration}/50 - Calling LLM...")

            # Call LLM with current messages
            message = await self.llm_with_functions.ainvoke(messages)

            print(f"✉️  LLM response - has function_call: {hasattr(message, 'additional_kwargs') and 'function_call' in message.additional_kwargs}")

            if (hasattr(message, "additional_kwargs")
                    and "function_call" in message.additional_kwargs):
                # Assistant wants to call a function
                func_call = message.additional_kwargs["function_call"]
                func_name = func_call["name"]
                func_args_json = func_call.get("arguments", "{}")
                func_args_dict = json.loads(func_args_json)

                # Call the actual tool via MCP session
                print(f"🔧 Calling tool: {func_name}")
                print(f"📦 Args: {func_args_json[:200]}..." if len(func_args_json) > 200 else f"📦 Args: {func_args_json}")

                result = await (self.notion_connector.session
                                .call_tool(func_name, func_args_dict))

                final_text.append(
                    f"[Calling tool {func_name} with args {func_args_json}]")

                print(f"✅ Tool result length: {len(''.join([c.text for c in result.content]))} chars")

                # Append function_call message
                messages.append(AIMessage(content="", additional_kwargs={
                    "function_call": func_call}))

                # Append function result message
                result_text = "".join([c.text for c in result.content])
                messages.append(
                    FunctionMessage(name=func_name,
                                    content=result_text))

                # Check if this was an error response
                if "error" in result_text.lower() or "validation" in result_text.lower():
                    consecutive_errors += 1
                    print(f"⚠️  Tool call resulted in error ({consecutive_errors}/{max_consecutive_errors})")
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"❌ Stopping after {max_consecutive_errors} consecutive errors")
                        final_text.append(f"[Stopped after {max_consecutive_errors} consecutive errors]")
                        break
                else:
                    consecutive_errors = 0  # Reset counter on success

            else:
                # LLM didn't call a function - it's done
                print(f"🏁 LLM finished - no more function calls")
                if message.content:
                    print(f"📝 Final message: {message.content[:100]}...")
                    final_text.append(message.content)
                break  # Exit immediately when LLM stops calling functions

        if iteration >= max_iterations:
            print(f"⚠️  Reached maximum iterations ({max_iterations})")
            final_text.append(f"[Reached maximum iterations: {max_iterations}]")

        return "\n".join(final_text)

    async def connect_notion_to_llm(self):
        await self.notion_connector.connect_to_server()
        # Fetch available tools from MCP session
        response = await self.notion_connector.session.list_tools()
        functions = []
        for tool in response.tools:
            functions.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            })

        # Bind functions to LLM
        self.llm_with_functions = (self.llm_for_notion_mcp
                                   .bind(functions=functions))

    def get_primary_notes(self):
        query = self.image_text_extractor.extract_text()
        # file_path = './mock_txt.txt'
        # query = utils.extract_text_from_file(file_path)
        return query
