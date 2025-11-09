from typing import TypedDict
from pathlib import Path

from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

from .tooling import ImageTextExtractor, create_notion_connector
from .settings import S, M

import utils

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
                                  "Preserve any schemas. "
                                  "Use only the language of the draft."
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
                 notion_connector: create_notion_connector,
                 draft_enhancer: DraftEnhancer,
                 image_text_extractor: ImageTextExtractor):

        self.notion_connector = notion_connector
        self.draft_enhancer = draft_enhancer
        self.image_text_extractor = image_text_extractor
        self.llm_with_functions = None
        self.agent = None
        self.client = None
        self.notion_page_id = None

    async def notes_creation(self):
        await self.connect_notion_to_llm()
        self.notion_page_id = await self.agent.run("Create if it does not "
                                                   "exists a page "
                                                   "named "
                                                   "uploads. answer with the notion page id only. "
                                                   "example : "
                                                   "1f03533f-dbf1-8011-8f74-e2d006d2d706")
        messages = await self.prepare_content()
        await self.write_in_notion(messages)

    async def prepare_content(self):
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
        base_prompt = Path(filename).read_text()
        filled_prompt = base_prompt.format(
            title=title,
            notion_page_id=self.notion_page_id,
            draft=enhanced_draft
            )
        print(f"\n📝 Prompt sent to LLM for Notion upload:")
        print(f"Title: {title}")
        print(f"Parent Page ID: {self.notion_page_id}")
        print(f"Draft preview (first 200 chars): {enhanced_draft[:200]}...")
        print(f'filled prompt : {filled_prompt}')
        return filled_prompt

    async def write_in_notion(self, messages):
        try:
            await self.agent.run(messages)
        finally:
            # Ensure we clean up resources properly
            if self.client.sessions:
                await self.client.close_all_sessions()

    async def connect_notion_to_llm(self):
        self.client, self.agent = await self.notion_connector()

    def get_primary_notes(self):
        # query = self.image_text_extractor.extract_text()
        file_path = './mock_txt.txt'
        query = utils.extract_text_from_file(file_path)
        return query
